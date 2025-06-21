import sqlite3
from datetime import datetime, timezone


class DatabaseManager:
    
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.create_tables()
        self.update_schema()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings 
                         (key TEXT PRIMARY KEY, value TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS api_keys 
                         (alias TEXT PRIMARY KEY, key TEXT UNIQUE)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS analyzed_videos 
                         (id TEXT PRIMARY KEY, title TEXT, channel TEXT, 
                          upload_date TEXT, views INTEGER, subscribers INTEGER, 
                          duration INTEGER, view_velocity REAL, retrieved_at TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS excluded_videos 
                         (id TEXT PRIMARY KEY)''')
        
        self.conn.commit()

    def update_schema(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(analyzed_videos)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'search_keyword' not in columns:
                cursor.execute("ALTER TABLE analyzed_videos ADD COLUMN search_keyword TEXT")
                self.conn.commit()
        except sqlite3.Error as e:
            print(f"Schema update error: {e}")

    def get_setting(self, key, default=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        result = cursor.fetchone()
        return result[0] if result else default

    def set_setting(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                      (key, str(value)))
        self.conn.commit()

    def get_api_keys(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT alias, key FROM api_keys')
        return {row[0]: row[1] for row in cursor.fetchall()}

    def add_api_key(self, alias, key):
        try:
            cursor = self.conn.cursor()
            cursor.execute('INSERT INTO api_keys (alias, key) VALUES (?, ?)', (alias, key))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def delete_api_key(self, alias):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM api_keys WHERE alias = ?', (alias,))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def add_analyzed_videos(self, videos, keyword):
        cursor = self.conn.cursor()
        current_time = datetime.now(timezone.utc).isoformat()
        
        video_data = [
            (v['id'], v['title'], v['channel'], v['upload_date'], v['views'], 
             v['subscribers'], v['duration'], v['view_velocity'], current_time, keyword)
            for v in videos
        ]
        
        cursor.executemany(
            '''INSERT OR REPLACE INTO analyzed_videos VALUES (?,?,?,?,?,?,?,?,?,?)''',
            video_data
        )
        self.conn.commit()
    
    def add_excluded_video(self, video_id):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO excluded_videos (id) VALUES (?)', (video_id,))
        self.conn.commit()

    def get_all_excluded_ids(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM excluded_videos')
        return {row[0] for row in cursor.fetchall()}

    def delete_excluded_videos(self, video_ids):
        if not video_ids:
            return
        
        cursor = self.conn.cursor()
        placeholders = ','.join('?' for _ in video_ids)
        cursor.execute(f"DELETE FROM excluded_videos WHERE id IN ({placeholders})", video_ids)
        self.conn.commit()

    def delete_analyzed_videos(self, video_ids):
        if not video_ids:
            return
        
        cursor = self.conn.cursor()
        placeholders = ','.join('?' for _ in video_ids)
        cursor.execute(f"DELETE FROM analyzed_videos WHERE id IN ({placeholders})", video_ids)
        self.conn.commit() 