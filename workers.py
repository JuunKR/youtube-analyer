import os
import json
from datetime import datetime, timezone
from PySide6.QtCore import QThread, Signal
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from isodate import parse_duration

from constants import DB_FILE, SCOPES
from database import DatabaseManager


class Worker(QThread):    
    progress = Signal(str)
    result = Signal(list)
    error = Signal(str)
    finished = Signal()
    
    def __init__(self, params, used_video_ids):
        super().__init__()
        self.params = params
        self.used_video_ids = used_video_ids

    def run(self):
        try:
            youtube = build("youtube", "v3", developerKey=self.params['api_key'])
            self.progress.emit(f"Starting analysis with '{self.params['keyword']}' keyword... (Order: {self.params['order']})")
            
            found_videos = []
            next_page_token = None
            searched_page_count = 0
            
            while len(found_videos) < self.params['target_count'] and searched_page_count < 20:
                searched_page_count += 1
                self.progress.emit(f"[Page {searched_page_count}] Searching...")
                
                search_response = youtube.search().list(
                    q=self.params['keyword'], 
                    part="snippet", 
                    type="video", 
                    order=self.params['order'], 
                    maxResults=50, 
                    pageToken=next_page_token
                ).execute()
                
                video_ids_to_check = [
                    item['id']['videoId'] 
                    for item in search_response.get('items', []) 
                    if 'videoId' in item.get('id', {}) 
                    and item['id']['videoId'] not in self.used_video_ids
                ]
                
                if not video_ids_to_check:
                    next_page_token = search_response.get('nextPageToken')
                    if not next_page_token:
                        break
                    continue
                
                video_response = youtube.videos().list(
                    part="snippet,statistics,contentDetails", 
                    id=",".join(video_ids_to_check)
                ).execute()
                
                valid_channel_ids = [
                    item.get('snippet', {}).get('channelId') 
                    for item in video_response.get('items', []) 
                    if item.get('snippet', {}).get('channelId')
                ]
                
                if not valid_channel_ids:
                    continue
                
                channel_response = youtube.channels().list(
                    part="statistics", 
                    id=",".join(valid_channel_ids)
                ).execute()
                
                subscriber_counts = {
                    item['id']: int(item['statistics'].get('subscriberCount', 0)) 
                    for item in channel_response.get('items', [])
                }
                
                for item in video_response.get('items', []):
                    video_info = self._process_video_item(item, subscriber_counts)
                    if video_info and self._passes_filters(video_info):
                        found_videos.append(video_info)
                        self.progress.emit(f"-> Filter passed! '{video_info['title'][:30]}...'")
                        
                        if len(found_videos) >= self.params['target_count']:
                            break
                
                if len(found_videos) >= self.params['target_count']:
                    break
                
                next_page_token = search_response.get('nextPageToken')
                if not next_page_token:
                    break
                
            self.result.emit(found_videos)
            
        except HttpError as e:
            self.error.emit(f"API Error: {e}")
        except Exception as e:
            self.error.emit(f"Unknown Error: {e}")
        finally:
            self.finished.emit()

    def _process_video_item(self, item, subscriber_counts):
        snippet = item.get('snippet', {})
        stats = item.get('statistics', {})
        details = item.get('contentDetails', {})
        channel_id = snippet.get('channelId')
        
        if not all([channel_id, snippet.get('publishedAt'), details.get('duration')]):
            return None
        
        subscriber_count = subscriber_counts.get(channel_id, 0)
        view_count = int(stats.get('viewCount', 0))
        duration_seconds = parse_duration(details.get('duration', 'PT0S')).total_seconds()
        upload_date = datetime.fromisoformat(snippet.get('publishedAt').replace('Z', '+00:00'))
        
        days_since_upload = (datetime.now(timezone.utc) - upload_date).days + 1
        view_velocity = view_count / days_since_upload
        
        return {
            "id": item.get('id'),
            "title": snippet.get('title', 'No Title'),
            "channel": snippet.get('channelTitle', 'No Channel'),
            "upload_date": upload_date.strftime("%Y-%m-%d"),
            "views": view_count,
            "subscribers": subscriber_count,
            "duration": int(duration_seconds),
            "url": f"https://www.youtube.com/watch?v={item.get('id')}",
            "view_velocity": view_velocity,
            "thumbnail_url": snippet.get('thumbnails', {}).get('high', {}).get('url')
        }

    def _passes_filters(self, video_info):    
        if video_info['views'] < self.params['min_views']:
            return False
        
        if video_info['duration'] < self.params['min_duration']:
            return False
        
        if self.params['max_duration'] > 0 and video_info['duration'] > self.params['max_duration']:
            return False
        
        if self.params['max_subs'] >= 0 and video_info['subscribers'] > self.params['max_subs']:
            return False
        
        return True


class SyncWorker(QThread):
    
    finished = Signal(str, str)
    
    def __init__(self, direction, credentials_path):
        super().__init__()
        self.direction = direction
        self.credentials_path = credentials_path
        self.db_manager = None
    
    def get_credentials(self):
    
        creds = None
        token_info_json = self.db_manager.get_setting('google_auth_token')
        
        if token_info_json:
            try:
                token_info = json.loads(token_info_json)
                creds = Credentials.from_authorized_user_info(token_info, SCOPES)
            except (json.JSONDecodeError, TypeError):
                creds = None
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Authentication file path not found: {self.credentials_path}\n"
                        "Please select the correct credentials.json file again in settings."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            self.db_manager.set_setting('google_auth_token', creds.to_json())
        
        return creds
    
    def run(self):
        try:
            self.db_manager = DatabaseManager(DB_FILE)
            creds = self.get_credentials()
            service = build('drive', 'v3', credentials=creds)
            
            # Google Drive에서는 파일 이름만 사용 (경로 제외)
            db_filename = os.path.basename(DB_FILE)
            response = service.files().list(
                q=f"name='{db_filename}' and trashed=false", 
                spaces='drive', 
                fields='files(id, name, modifiedTime)'
            ).execute()
            
            files = response.get('files', [])
            
            if self.direction == 'download':
                self._handle_download(service, files)
            elif self.direction == 'upload':
                self._handle_upload(service, files)
                
        except FileNotFoundError as e:
            self.finished.emit("error", str(e))
        except Exception as e:
            self.finished.emit("error", f"Sync error occurred: {e}")

    def _handle_download(self, service, files):
        if not files:
            self.finished.emit("skip", "No DB file found in cloud. Starting with local DB.")
            return
        
        cloud_file = files[0]
        local_token = self.db_manager.get_setting('google_auth_token')
        
        request = service.files().get_media(fileId=cloud_file['id'])
        with open(DB_FILE, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        
        downloaded_db_manager = DatabaseManager(DB_FILE)
        if local_token and not downloaded_db_manager.get_setting('google_auth_token'):
            downloaded_db_manager.set_setting('google_auth_token', local_token)
        
        self.finished.emit("success", "DB file successfully downloaded from cloud.")

    def _handle_upload(self, service, files):
        if not os.path.exists(DB_FILE):
            self.finished.emit("skip", "No local DB file to upload.")
            return
        
        # Google Drive에 업로드할 때는 파일 이름만 사용 (경로 제외)
        db_filename = os.path.basename(DB_FILE)
        file_metadata = {'name': db_filename}
        media = MediaFileUpload(DB_FILE, mimetype='application/x-sqlite3')
        
        if files:
            service.files().update(
                fileId=files[0]['id'], 
                body=file_metadata, 
                media_body=media, 
                fields='id'
            ).execute()
        else:
            service.files().create(
                body=file_metadata, 
                media_body=media, 
                fields='id'
            ).execute()
        
        self.finished.emit("success", "DB file successfully uploaded to cloud.") 