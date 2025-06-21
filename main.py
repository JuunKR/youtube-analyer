import sys
import os
import threading
import qtawesome as qta
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox,
                               QScrollArea, QGroupBox, QInputDialog, QMessageBox,
                               QFileDialog, QCheckBox)
from PySide6.QtCore import Qt, Slot

from constants import DB_FILE, DEFAULT_SETTINGS, ORDER_OPTIONS, get_platform_stylesheet
from database import DatabaseManager
from workers import Worker, SyncWorker
from widgets import DBViewerDialog, ResultCard


class YoutubeAnalyzerApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Trend Analyzer v1.0")
        self.setMinimumSize(1000, 800)
        self.setStyleSheet(get_platform_stylesheet())
        self.setWindowIcon(qta.icon('fa5b.youtube', color='#c4302b'))
        
        self._cleanup_old_token_file()
        self.db_manager = DatabaseManager(DB_FILE)
        self.load_settings()
        
        self.last_results_data = []
        self.last_used_keyword = ""
        
        self._create_central_widget()
        self.restore_ui_state()
        
        if self.sync_enabled:
            threading.Timer(0.5, lambda: self.run_sync('download')).start()

    def _cleanup_old_token_file(self):
    
        token_file_path = 'token.json'
        if os.path.exists(token_file_path):
            try:
                os.remove(token_file_path)
                print(f"Notice: Deleted existing '{token_file_path}' file and "
                      "switched to saving authentication info in DB.")
            except OSError as e:
                print(f"Warning: Failed to delete existing '{token_file_path}' file: {e}")

    def load_settings(self):
    
        self.api_keys = self.db_manager.get_api_keys()
        self.used_video_ids = self.db_manager.get_all_excluded_ids()
        self.credentials_path = self.db_manager.get_setting('credentials_path', '')
        self.sync_enabled = self.db_manager.get_setting('sync_enabled', 'false').lower() == 'true'

    def _create_central_widget(self):
    
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        top_panel_layout = QHBoxLayout()
        self._create_settings_group(top_panel_layout)
        self._create_search_conditions_group(top_panel_layout)
        main_layout.addLayout(top_panel_layout)
        
        self._create_results_section(main_layout)

    def _create_settings_group(self, parent_layout):
    
        api_group = QGroupBox("Settings & Management")
        api_layout = QVBoxLayout(api_group)
        
        self._create_api_key_section(api_layout)
        self._create_management_buttons(api_layout)
        
        parent_layout.addWidget(api_group, 1)

    def _create_api_key_section(self, parent_layout):
    
        api_key_layout = QHBoxLayout()
        
        api_key_layout.addWidget(QLabel("API Key to use:"))
        
        self.api_key_combobox = QComboBox()
        api_key_layout.addWidget(self.api_key_combobox, 1)
        
        add_key_button = QPushButton(qta.icon('fa5s.plus-circle'), " Add Key")
        add_key_button.clicked.connect(self.add_api_key)
        api_key_layout.addWidget(add_key_button)
        
        delete_key_button = QPushButton(qta.icon('fa5s.trash-alt'), " Delete Key")
        delete_key_button.clicked.connect(self.delete_api_key)
        delete_key_button.setStyleSheet("background-color: #e74c3c;")
        api_key_layout.addWidget(delete_key_button)
        
        parent_layout.addLayout(api_key_layout)

    def _create_management_buttons(self, parent_layout):
    
        self.sync_checkbox = QCheckBox("Cloud Sync (Google Drive)")
        self.sync_checkbox.toggled.connect(self.toggle_sync)
        parent_layout.addWidget(self.sync_checkbox)
        
        sync_buttons_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton(qta.icon('fa5s.sync-alt', color='white'), " Refresh from Cloud")
        self.refresh_button.setToolTip("Download latest data from cloud and refresh the app.")
        self.refresh_button.clicked.connect(self.refresh_from_cloud)
        sync_buttons_layout.addWidget(self.refresh_button)
        
        self.upload_button = QPushButton(qta.icon('fa5s.cloud-upload-alt', color='white'), " Upload to Cloud")
        self.upload_button.setToolTip("Upload current local data to cloud.")
        self.upload_button.clicked.connect(self.upload_to_cloud)
        sync_buttons_layout.addWidget(self.upload_button)
        
        self.reset_creds_button = QPushButton(qta.icon('fa5s.redo-alt', color='white'), " Reset Auth File")
        self.reset_creds_button.setStyleSheet("background-color: #e74c3c;")
        self.reset_creds_button.clicked.connect(self.reset_credentials)
        sync_buttons_layout.addWidget(self.reset_creds_button)
        
        parent_layout.addLayout(sync_buttons_layout)
        
        db_viewer_button = QPushButton(qta.icon('fa5s.database', color='white'), " DB Manager")
        db_viewer_button.clicked.connect(self.open_db_viewer)
        parent_layout.addWidget(db_viewer_button)

    def _create_search_conditions_group(self, parent_layout):
    
        settings_group = QGroupBox("Search Conditions")
        settings_layout = QGridLayout(settings_group)
        
        self._init_search_inputs()
        self._layout_search_widgets(settings_layout)
        
        parent_layout.addWidget(settings_group, 2)

    def _init_search_inputs(self):
    
        self.keyword_entry = QLineEdit()
        
        self.order_combobox = QComboBox()
        self.order_combobox.addItems(list(ORDER_OPTIONS.keys()))
        
        self.max_subs_entry = QLineEdit()
        self.min_views_entry = QLineEdit()
        self.min_duration_entry = QLineEdit()
        self.target_count_entry = QLineEdit()
        
        self.shorts_only_checkbox = QCheckBox("Shorts only (under 1 minute)")
        self.shorts_only_checkbox.toggled.connect(self.on_shorts_only_toggled)
        
        self.search_button = QPushButton(qta.icon('fa5s.search'), " Start Analysis")
        self.search_button.clicked.connect(self.start_search)

    def _layout_search_widgets(self, layout):
    
        layout.addWidget(QLabel("Search Keyword:"), 0, 0)
        layout.addWidget(self.keyword_entry, 0, 1, 1, 3)
        
        layout.addWidget(QLabel("Sort by:"), 1, 0)
        layout.addWidget(self.order_combobox, 1, 1)
        layout.addWidget(QLabel("Max Subscribers:"), 1, 2)
        layout.addWidget(self.max_subs_entry, 1, 3)
        
        layout.addWidget(QLabel("Min Views:"), 2, 0)
        layout.addWidget(self.min_views_entry, 2, 1)
        layout.addWidget(QLabel("Min Duration (sec):"), 2, 2)
        layout.addWidget(self.min_duration_entry, 2, 3)
        
        layout.addWidget(QLabel("Video Count:"), 3, 0)
        layout.addWidget(self.target_count_entry, 3, 1)
        layout.addWidget(self.shorts_only_checkbox, 3, 2, 1, 2)
        
        layout.addWidget(self.search_button, 4, 0, 1, 4)

    def _create_results_section(self, parent_layout):
    
        results_group = QGroupBox("Analysis Results")
        results_group_layout = QVBoxLayout(results_group)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.scroll_content_widget = QWidget()
        self.results_layout = QVBoxLayout(self.scroll_content_widget)
        self.results_layout.setAlignment(Qt.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content_widget)
        results_group_layout.addWidget(self.scroll_area)
        
        self.save_results_button = QPushButton(qta.icon('fa5s.save'), " Save Results as Text")
        self.save_results_button.clicked.connect(self.save_results_as_text)
        self.save_results_button.setEnabled(False)
        results_group_layout.addWidget(self.save_results_button)
        
        parent_layout.addWidget(results_group, 1)

    def on_shorts_only_toggled(self, checked):
    
        self.min_duration_entry.setEnabled(not checked)
        
        if checked:
            self.min_duration_entry.setText("0")
        else:
            self.min_duration_entry.setText(
                self.db_manager.get_setting('last_min_duration', '60')
            )

    def open_db_viewer(self):
    
        dialog = DBViewerDialog(self)
        dialog.exec()
        
        self.load_settings()
        self.restore_ui_state()
        self.update_status_bar()

    def reset_credentials(self):
    
        reply = QMessageBox.question(
            self, "Reset Authentication", 
            "Do you want to reset Google Drive authentication and start over?\n"
            "Existing authentication info stored in DB will be deleted.", 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.credentials_path = ''
            self.db_manager.set_setting('credentials_path', '')
            self.db_manager.set_setting('google_auth_token', '')
            
            self.update_status_bar("Authentication info deleted from DB.", 3000)
            self.update_sync_buttons_state()
            
            self.sync_checkbox.setChecked(False)
            self.sync_checkbox.setChecked(True)

    def restore_ui_state(self):
    
        self.api_key_combobox.clear()
        self.api_key_combobox.addItems(self.api_keys.keys())
        self.api_key_combobox.setCurrentText(
            self.db_manager.get_setting('last_api_alias', '')
        )
        
        self.keyword_entry.setText('')
        
        saved_order = self.db_manager.get_setting('last_order', DEFAULT_SETTINGS['order'])
        korean_order = self._get_korean_order_name(saved_order)
        self.order_combobox.setCurrentText(korean_order)
        
        self.max_subs_entry.setText(
            self.db_manager.get_setting('last_max_subs', DEFAULT_SETTINGS['max_subs'])
        )
        self.min_views_entry.setText(
            self.db_manager.get_setting('last_min_views', DEFAULT_SETTINGS['min_views'])
        )
        self.min_duration_entry.setText(
            self.db_manager.get_setting('last_min_duration', DEFAULT_SETTINGS['min_duration'])
        )
        self.target_count_entry.setText(
            self.db_manager.get_setting('last_target_count', DEFAULT_SETTINGS['target_count'])
        )
        
        self.sync_checkbox.blockSignals(True)
        self.sync_checkbox.setChecked(self.sync_enabled)
        self.sync_checkbox.blockSignals(False)
        
        self.update_sync_buttons_state()

    def _get_korean_order_name(self, api_value):
        for korean_name, api_val in ORDER_OPTIONS.items():
            if api_val == api_value:
                return korean_name
        return 'Most Views'

    def _get_api_order_value(self, korean_name):
        return ORDER_OPTIONS.get(korean_name, 'viewCount')

    def toggle_sync(self, checked):
        self.sync_enabled = checked
        self.update_sync_buttons_state()
        if checked and not self.credentials_path:
            self.prompt_for_credentials()

    def update_sync_buttons_state(self):
        self.refresh_button.setEnabled(self.sync_enabled)
        self.upload_button.setEnabled(self.sync_enabled)
        
        has_credentials = bool(
            self.credentials_path or 
            self.db_manager.get_setting('google_auth_token') or
            self.db_manager.get_setting('credentials_path')
        )
        self.reset_creds_button.setEnabled(has_credentials)

    def prompt_for_credentials(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Google Drive Authentication Setup Guide")
        msg_box.setIcon(QMessageBox.Information)
        
        msg_box.setText(
            "Google Cloud authentication info (credentials.json) is needed for cloud sync.<br>"
            "Please follow the instructions to complete the setup, then click 'Select File' button."
        )
        
        detailed_steps = self._get_credentials_setup_guide()
        msg_box.setInformativeText(detailed_steps)
        msg_box.setTextFormat(Qt.RichText)
        
        select_file_button = msg_box.addButton("Select File", QMessageBox.AcceptRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        msg_box.setDefaultButton(select_file_button)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == select_file_button:
            self._handle_credentials_file_selection()
        else:
            self.sync_checkbox.setChecked(False)

    def _get_credentials_setup_guide(self):
        return """<hr><b>Authentication Setup Steps:</b><ol>
    <li>Go to Google Cloud Console <a href="https://console.cloud.google.com/apis/credentials">link</a> and log in.</li>
    <li>Select the project menu at the top or create a new one.</li>
    <li><b>[Important]</b> Search for '<b>Google Drive API</b>' in 'API & Services' > 'Library' and '<b>Enable</b>' it.</li>
    <li>Go to 'API & Services' > '<b>Credentials</b>' from the left menu.</li>
    <li>Select '<b>+ Create Credentials</b>' > '<b>OAuth Client ID</b>'.</li>
    <li>Select '<b>Desktop App</b>' and click 'Create'.</li>
    <li>Download credentials.json file from the created client ID.</li>
    <li style="color: #ffcc00;"><b>[Required] Add Test User:</b>
        <ul style="margin-top: 5px;">
            <li>Go to 'OAuth consent screen' from the left menu.</li>
            <li>Ensure the status is 'Test' and click '<b>+ ADD USERS</b>'.</li>
            <li>Add your Google account email and save.<br>(Skipping this step will result in 'access denied' error.)</li></ul></li>
    <li>After completing all steps, click 'Select File' button.</li></ol>"""

    def _handle_credentials_file_selection(self):
        creds_path, _ = QFileDialog.getOpenFileName(
            self, "Select downloaded credentials.json file", "", "JSON Files (*.json)"
        )
        
        if creds_path:
            self.credentials_path = creds_path
            self.db_manager.set_setting('credentials_path', creds_path)
            
            QMessageBox.information(
                self, "Credentials Setup Completed", 
                "Credentials file has been set.\nNow sync will proceed."
            )
            self.run_sync('download')
        else:
            QMessageBox.warning(
                self, "Setup Cancelled", 
                "No file selected, so sync setup has been cancelled."
            )
            self.sync_checkbox.setChecked(False)

    def run_sync(self, direction):
        if not self.credentials_path:
            self.prompt_for_credentials()
            if not self.sync_enabled:
                return
        
        self.search_button.setEnabled(False)
        self.sync_worker = SyncWorker(direction, self.credentials_path)
        self.sync_worker.finished.connect(self.on_sync_finished)
        self.sync_worker.start()
        self.update_status_bar(f"Syncing with cloud... ({direction})")

    @Slot(str, str)
    def on_sync_finished(self, status, message):
        if status == "error":
            QMessageBox.critical(self, "Sync Error", message)
            self.sync_checkbox.setChecked(False)
            self.sync_enabled = False
        else:
            if status == "success" and "downloaded" in message.lower():
                self.refresh_app_data()
            else:
                self.db_manager = DatabaseManager(DB_FILE)
                self.load_settings()
                self.restore_ui_state()
                if status != "skip":
                    self.update_status_bar(message, 5000)
        
        self.search_button.setEnabled(True)
        if status != "error":
            self.update_status_bar()

    def save_settings_on_exit(self):
        self.db_manager.set_setting('sync_enabled', str(self.sync_enabled))
        
        api_order_value = self._get_api_order_value(self.order_combobox.currentText())
        
        settings_to_save = {
            'last_api_alias': self.api_key_combobox.currentText(),
            'last_order': api_order_value,
            'last_max_subs': self.max_subs_entry.text(),
            'last_min_views': self.min_views_entry.text(),
            'last_min_duration': self.min_duration_entry.text(),
            'last_target_count': self.target_count_entry.text()
        }
        
        for key, value in settings_to_save.items():
            self.db_manager.set_setting(key, value)

    def closeEvent(self, event):
        self.save_settings_on_exit()
        
        if self.sync_enabled:
            reply = QMessageBox.question(
                self, "Exit and Upload", 
                "Do you want to upload changes to cloud and exit?", 
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, 
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                self.update_status_bar("Uploading...")
                QApplication.processEvents()
                sync_worker = SyncWorker('upload', self.credentials_path)
                sync_worker.run()
                event.accept()
            elif reply == QMessageBox.Cancel:
                event.ignore()
            else:
                event.accept()
        else:
            event.accept()

    def add_api_key(self):
        if not self._show_api_key_guide():
            return
        
        new_key = self._get_api_key_input()
        if not new_key:
            return
        
        alias = self._get_api_key_alias()
        if not alias:
            return
        
        if self.db_manager.add_api_key(alias, new_key):
            self.api_keys[alias] = new_key
            self.api_key_combobox.addItem(alias)
            self.api_key_combobox.setCurrentText(alias)
            
            QMessageBox.information(self, "Success", f"'{alias}' has been successfully added.")
            self.update_status_bar()
        else:
            QMessageBox.warning(self, "Duplicate Error", "Already registered API key or alias.")

    def _show_api_key_guide(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("YouTube API Key Addition Guide")
        msg_box.setIcon(QMessageBox.Information)
        
        msg_box.setText(
            "YouTube Data API v3 key is needed for analysis.<br>"
            "Please follow the instructions to get the key, then input it in the next step."
        )
        
        detailed_steps = """<hr><b>API Key Issuance Steps:</b><ol>
    <li>Go to Google Cloud Console <a href="https://console.cloud.google.com/apis/credentials">link</a> and log in.</li>
    <li>Select the project or create a new one.</li>
    <li>Search for '<b>YouTube Data API v3</b>' in 'API & Services' > 'Library' and '<b>Enable</b>' it.</li>
    <li>Go to 'API & Services' > '<b>Credentials</b>'.</li>
    <li>Select '<b>+ Create Credentials</b>' > '<b>API Key</b>'.</li>
    <li>Copy the generated key and paste it into this window, then click 'OK'.</li></ol>"""
        
        msg_box.setInformativeText(detailed_steps)
        msg_box.setTextFormat(Qt.RichText)
        
        ok_button = msg_box.addButton("Key Input", QMessageBox.AcceptRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        msg_box.setDefaultButton(ok_button)
        
        msg_box.exec()
        return msg_box.clickedButton() == ok_button

    def _get_api_key_input(self):
        new_key, ok = QInputDialog.getText(
            self, "API Key Input", 
            "Paste the issued YouTube Data API v3 key here:"
        )
        
        if ok and new_key:
            return new_key.strip()
        elif ok:
            QMessageBox.warning(self, "Input Error", "Please input API key.")
        
        return None

    def _get_api_key_alias(self):
        alias, ok_alias = QInputDialog.getText(
            self, "Key Alias Setting", 
            "Enter an alias to identify this key:", 
            text=f"API Key {len(self.api_keys) + 1}"
        )
        
        if ok_alias and alias:
            return alias.strip()
        else:
            QMessageBox.warning(self, "Input Error", "Alias must be entered.")
        
        return None

    def start_search(self):
        selected_alias = self.api_key_combobox.currentText()
        if not selected_alias:
            QMessageBox.critical(self, "Error", "Please select or add an API key to use.")
            return
        
        self.last_used_keyword = self.keyword_entry.text().strip()
        if not self.last_used_keyword:
            QMessageBox.warning(self, "Input Error", "Please input search keyword.")
            return
        
        params = self._prepare_search_params(selected_alias)
        if not params:
            return
        
        self._execute_search(params)

    def _prepare_search_params(self, selected_alias):
        try:
            is_shorts_search = self.shorts_only_checkbox.isChecked()
            max_duration = 60 if is_shorts_search else -1
            
            api_order_value = self._get_api_order_value(self.order_combobox.currentText())
            
            return {
                "api_key": self.api_keys[selected_alias],
                "keyword": self.last_used_keyword,
                "order": api_order_value,
                "max_subs": int(self.max_subs_entry.text()),
                "min_views": int(self.min_views_entry.text()),
                "min_duration": int(self.min_duration_entry.text()),
                "target_count": int(self.target_count_entry.text()),
                "max_duration": max_duration
            }
        except ValueError:
            QMessageBox.critical(self, "Input Error", "Please input correct numbers in numeric fields.")
            return None

    def _execute_search(self, params):
        self.search_button.setEnabled(False)
        self.save_results_button.setEnabled(False)
        self.clear_results()
        
        self.worker = Worker(params, self.used_video_ids)
        self.worker.progress.connect(self.update_status_bar)
        self.worker.result.connect(self.display_results)
        self.worker.error.connect(self.show_error)
        self.worker.finished.connect(lambda: self.search_button.setEnabled(True))
        self.worker.start()

    @Slot(list)
    def display_results(self, videos):
        self.clear_results()
        
        sorted_videos = sorted(videos, key=lambda x: x['view_velocity'], reverse=True)
        self.last_results_data = sorted_videos
        
        if not sorted_videos:
            self.results_layout.addWidget(
                QLabel("No videos found for the specified conditions.")
            )
            return
        
        self.db_manager.add_analyzed_videos(sorted_videos, self.last_used_keyword)
        self.update_status_bar(f"{len(sorted_videos)} videos saved to DB!", 5000)
        
        for video_data in sorted_videos:
            card = ResultCard(video_data)
            card.exclude_requested.connect(self.exclude_video)
            card.status_update.connect(self.update_status_bar)
            self.results_layout.addWidget(card)
        
        self.save_results_button.setEnabled(True)

    @Slot(str)
    def exclude_video(self, video_id):
        if video_id not in self.used_video_ids:
            self.db_manager.add_excluded_video(video_id)
            self.used_video_ids.add(video_id)
            
            QMessageBox.information(
                self, "Success", 
                f"Video({video_id}) has been added to exclude list."
            )
            self.update_status_bar()
            
            for i in reversed(range(self.results_layout.count())):
                widget = self.results_layout.itemAt(i).widget()
                if (isinstance(widget, ResultCard) and 
                    widget.video_data['id'] == video_id):
                    widget.setParent(None)
                    widget.deleteLater()
                    break

    def save_results_as_text(self):
        if not self.last_results_data:
            QMessageBox.warning(self, "No Data to Save", "Please analyze data first.")
            return
        
        default_filename = (f"AnalysisResult_{self.keyword_entry.text()}_"
                           f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Results", default_filename, 
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            self._write_results_to_file(file_path)

    def _write_results_to_file(self, file_path):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"--- YouTube Analysis Results ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ---\n")
                f.write(f"Search Keyword: {self.keyword_entry.text()}\n\n")
                
                for i, video in enumerate(self.last_results_data):
                    duration_min, duration_sec = divmod(video['duration'], 60)
                    
                    f.write(f"🏆 #{i+1}. {video['title']}\n")
                    f.write(f"   - Channel: {video['channel']} ({video['subscribers']:,} subscribers)\n")
                    f.write(f"   - Upload Date: {video['upload_date']} / Views: {video['views']:,}\n")
                    f.write(f"   - Video Duration: {duration_min}m {duration_sec}s\n")
                    f.write(f"   - 🔥 View Velocity: {video['view_velocity']:.1f}\n")
                    f.write(f"   - URL: {video['url']}\n\n")
            
            QMessageBox.information(
                self, "Save Completed", 
                f"Results have been successfully saved.\nPath: {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", 
                f"An error occurred while saving file: {e}"
            )

    def clear_results(self):
        self.last_results_data = []
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    @Slot(str, int)
    def update_status_bar(self, message="", timeout=0):
        if not message:
            try:
                analyzed_count = self.db_manager.conn.execute(
                    'SELECT COUNT(*) FROM analyzed_videos'
                ).fetchone()[0]
                
                message = (f"Waiting... (API Keys: {len(self.api_keys)} / "
                          f"Analyzed Videos: {analyzed_count} / "
                          f"Excluded Videos: {len(self.used_video_ids)})")
            except:
                message = "Waiting..."
        
        if timeout > 0:
            self.statusBar().showMessage(message, timeout)
        else:
            self.statusBar().showMessage(message)

    @Slot(str)
    def show_error(self, error_message):
        QMessageBox.critical(self, "Error Occurred", error_message)
        self.update_status_bar("Error occurred. Please try again.", 5000)

    def delete_api_key(self):
        selected_alias = self.api_key_combobox.currentText()
        if not selected_alias:
            QMessageBox.warning(self, "No Key Selected", "Please select an API key to delete.")
            return
        
        if len(self.api_keys) <= 1:
            QMessageBox.warning(
                self, "Cannot Delete", 
                "Cannot delete the last API key. At least one API key must remain."
            )
            return
        
        reply = QMessageBox.question(
            self, "Delete API Key", 
            f"Are you sure you want to delete the API key '{selected_alias}'?\n\n"
            f"This action cannot be undone.", 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db_manager.delete_api_key(selected_alias):
                del self.api_keys[selected_alias]
                current_index = self.api_key_combobox.findText(selected_alias)
                self.api_key_combobox.removeItem(current_index)
                
                if self.api_key_combobox.count() > 0:
                    self.api_key_combobox.setCurrentIndex(0)
                
                QMessageBox.information(self, "Success", f"API key '{selected_alias}' has been deleted.")
                self.update_status_bar()
            else:
                QMessageBox.warning(self, "Delete Error", "Failed to delete API key from database.")

    def refresh_from_cloud(self):
        if not self.sync_enabled:
            QMessageBox.warning(
                self, "Sync Disabled", 
                "Please enable Cloud Sync first before refreshing from cloud."
            )
            return
            
        if not self.credentials_path:
            QMessageBox.warning(
                self, "No Credentials", 
                "Please set up Google Drive authentication first."
            )
            return
        
        reply = QMessageBox.question(
            self, "Refresh from Cloud", 
            "This will download the latest database from cloud and refresh the app.\n"
            "Any unsaved local changes will be lost.\n\n"
            "Continue?", 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.run_sync('download')

    def refresh_app_data(self):
        try:
            old_db = self.db_manager
            self.db_manager = DatabaseManager(DB_FILE)
            
            self.load_settings()
            self.restore_ui_state()
            self.clear_results()
            self.update_status_bar()
            
            old_db.conn.close()
            
            QMessageBox.information(
                self, "Refresh Complete", 
                "App has been refreshed with the latest data from cloud."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Refresh Error", 
                f"Failed to refresh app data: {e}"
            )

    def upload_to_cloud(self):
        if not self.sync_enabled:
            QMessageBox.warning(
                self, "Sync Disabled", 
                "Please enable Cloud Sync first before uploading to cloud."
            )
            return
            
        if not self.credentials_path:
            QMessageBox.warning(
                self, "No Credentials", 
                "Please set up Google Drive authentication first."
            )
            return
        
        if not os.path.exists(DB_FILE):
            QMessageBox.warning(
                self, "No Local Database", 
                "No local database file found to upload."
            )
            return
        
        reply = QMessageBox.question(
            self, "Upload to Cloud", 
            "This will upload your current local database to cloud.\n"
            "This will overwrite the existing cloud database.\n\n"
            "Continue?", 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.run_sync('upload')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YoutubeAnalyzerApp()
    window.show()
    window.update_status_bar()
    sys.exit(app.exec()) 