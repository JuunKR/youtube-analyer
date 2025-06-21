import os
import math
import webbrowser
import threading
import qtawesome as qta
import requests
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, 
                               QAbstractItemView, QMessageBox, QFrame, QFileDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

from constants import DB_FILE
from database import DatabaseManager


class DBViewerDialog(QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DB Manager")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(parent.styleSheet())
        
        self.db_manager = DatabaseManager(DB_FILE)
        self._init_state_variables()
        self._setup_ui()
        self._connect_signals()
        self.update_view()

    def _init_state_variables(self):
        self.current_page = 1
        self.rows_per_page = 100
        self.current_sort_column = 6
        self.current_sort_order = Qt.DescendingOrder
        self.column_map = {
            0: 'id', 1: 'search_keyword', 2: 'title', 
            3: 'channel', 4: 'views', 5: 'upload_date', 6: 'retrieved_at'
        }

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        self._create_search_section(main_layout)
        self._create_tab_widget(main_layout)
        self._create_bottom_buttons(main_layout)

    def _create_search_section(self, parent_layout):
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search (Keyword):"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter keyword to search and press Enter...")
        search_layout.addWidget(self.search_input)
        
        parent_layout.addLayout(search_layout)

    def _create_tab_widget(self, parent_layout):
        self.tab_widget = QTabWidget()
        parent_layout.addWidget(self.tab_widget)
        
        self.analyzed_table = self._create_table_widget(list(self.column_map.values()))
        self.tab_widget.addTab(self.analyzed_table, "Analyzed Videos")
        
        self.excluded_table = self._create_table_widget(['Excluded Video ID'])
        self.tab_widget.addTab(self.excluded_table, "Excluded Videos")

    def _create_bottom_buttons(self, parent_layout):
        bottom_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("<< Previous")
        self.page_label = QLabel("Page 1 / 1")
        self.next_button = QPushButton("Next >>")
        
        bottom_layout.addWidget(self.prev_button)
        bottom_layout.addWidget(self.page_label)
        bottom_layout.addWidget(self.next_button)
        bottom_layout.addStretch()
        
        delete_button = QPushButton("Delete Selected")
        close_button = QPushButton("Close")
        bottom_layout.addWidget(delete_button)
        bottom_layout.addWidget(close_button)
        
        parent_layout.addLayout(bottom_layout)
        
        self.delete_button = delete_button
        self.close_button = close_button

    def _create_table_widget(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _connect_signals(self):
        self.tab_widget.currentChanged.connect(self.trigger_update)
        self.search_input.returnPressed.connect(self.trigger_update)
        self.analyzed_table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        self.prev_button.clicked.connect(self.go_to_previous_page)
        self.next_button.clicked.connect(self.go_to_next_page)
        self.delete_button.clicked.connect(self.delete_selected_rows)
        self.close_button.clicked.connect(self.accept)
        self.analyzed_table.cellDoubleClicked.connect(self.open_video_url)

    def trigger_update(self):
        self.current_page = 1
        self.update_view()

    def on_header_clicked(self, logical_index):
        if self.current_sort_column == logical_index:
            self.current_sort_order = (Qt.DescendingOrder 
                                     if self.current_sort_order == Qt.AscendingOrder 
                                     else Qt.AscendingOrder)
        else:
            self.current_sort_column = logical_index
            self.current_sort_order = Qt.AscendingOrder
        self.update_view()
    
    def go_to_previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_view()
    
    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_view()
    
    def update_view(self):
        current_table = self.tab_widget.currentWidget()
        
        if current_table is self.excluded_table:
            self.update_excluded_table()
            return
        
        self._update_analyzed_table()

    def _update_analyzed_table(self):
        search_term = self.search_input.text().strip()
        where_clause = ""
        params = []
        
        if search_term:
            where_clause = "WHERE search_keyword LIKE ?"
            params.append(f"%{search_term}%")

        order_by_column = self.column_map.get(self.current_sort_column, 'retrieved_at')
        order_direction = "DESC" if self.current_sort_order == Qt.DescendingOrder else "ASC"
        
        cursor = self.db_manager.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM analyzed_videos {where_clause}", params)
        total_rows = cursor.fetchone()[0]
        self.total_pages = math.ceil(total_rows / self.rows_per_page) or 1
        
        offset = (self.current_page - 1) * self.rows_per_page
        query = f"""SELECT {', '.join(self.column_map.values())} FROM analyzed_videos
                    {where_clause} ORDER BY {order_by_column} {order_direction}
                    LIMIT ? OFFSET ?"""
        params.extend([self.rows_per_page, offset])
        cursor.execute(query, params)

        self.analyzed_table.setRowCount(0)
        for row_idx, row_data in enumerate(cursor.fetchall()):
            self.analyzed_table.insertRow(row_idx)
            for col_idx, cell_data in enumerate(row_data):
                item = QTableWidgetItem(str(cell_data))
                item.setToolTip("Double-click to watch video")
                
                if self.column_map[col_idx] == 'views':
                    try: 
                        num_item = QTableWidgetItem()
                        num_item.setData(Qt.DisplayRole, int(cell_data))
                        item = num_item
                    except (ValueError, TypeError):
                        pass
                
                self.analyzed_table.setItem(row_idx, col_idx, item)
        
        self.analyzed_table.horizontalHeader().setSortIndicator(
            self.current_sort_column, self.current_sort_order)
        self.analyzed_table.resizeColumnsToContents()
        self.update_pagination_controls(total_rows)

    def update_excluded_table(self):
        self.excluded_table.setRowCount(0)
        cursor = self.db_manager.conn.cursor()
        cursor.execute("SELECT id FROM excluded_videos ORDER BY rowid DESC")
        
        for row_idx, row_data in enumerate(cursor.fetchall()):
            self.excluded_table.insertRow(row_idx)
            self.excluded_table.setItem(row_idx, 0, QTableWidgetItem(row_data[0]))
        
        self.update_pagination_controls(self.excluded_table.rowCount(), is_excluded=True)

    def update_pagination_controls(self, total_rows, is_excluded=False):
        if is_excluded:
            self.page_label.setText(f"Total {total_rows} items")
            self.prev_button.hide()
            self.next_button.hide()
        else:
            self.page_label.setText(f"Page {self.current_page} / {self.total_pages} ({total_rows} items)")
            self.prev_button.show()
            self.next_button.show()
            self.prev_button.setEnabled(self.current_page > 1)
            self.next_button.setEnabled(self.current_page < self.total_pages)
    
    def delete_selected_rows(self):
        current_table = self.tab_widget.currentWidget()
        selected_items = current_table.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "Notice", "Please select items to delete.")
            return
        
        selected_rows = sorted(list(set(item.row() for item in selected_items)), reverse=True)
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to permanently delete {len(selected_rows)} items from the database?", 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            ids_to_delete = [current_table.item(row, 0).text() for row in selected_rows]
            
            if current_table is self.excluded_table:
                self.db_manager.delete_excluded_videos(ids_to_delete)
            else:
                self.db_manager.delete_analyzed_videos(ids_to_delete)
            
            self.update_view()
            QMessageBox.information(self, "Complete", "Selected items have been deleted.")
    
    def open_video_url(self, row, column):
        if self.tab_widget.currentWidget() is not self.analyzed_table:
            return
        
        id_item = self.analyzed_table.item(row, 0)
        if id_item:
            webbrowser.open_new_tab(f"https://www.youtube.com/watch?v={id_item.text()}")


class ResultCard(QFrame):
    
    exclude_requested = Signal(str)
    status_update = Signal(str, int)
    
    def __init__(self, video_data):
        super().__init__()
        self.video_data = video_data
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("QFrame { background-color: #353b48; border-radius: 8px; }")
        self._setup_ui()
        self._load_thumbnail_async()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        self._create_thumbnail_section(main_layout)
        self._create_info_section(main_layout)
        self._create_button_section(main_layout)

    def _create_thumbnail_section(self, main_layout):
        self.thumbnail_label = QLabel("Loading...")
        self.thumbnail_label.setFixedSize(160, 90)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet(
            "background-color: #4a5160; border-radius: 4px; color: #a0a0a0;"
        )
        self.thumbnail_label.mousePressEvent = self.download_thumbnail
        main_layout.addWidget(self.thumbnail_label)

    def _create_info_section(self, main_layout):
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        title_text = (f"<a href='{self.video_data['url']}' "
                     f"style='color: #e0e0e0; text-decoration: none;'>"
                     f"<b>{self.video_data['title']}</b></a>")
        title_label = QLabel(title_text)
        title_label.setWordWrap(True)
        title_label.setOpenExternalLinks(True)
        
        channel_label = QLabel(
            f"<font color='#a0a0a0'>{self.video_data['channel']} "
            f"({self.video_data['subscribers']:,} subscribers)</font>"
        )
        channel_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        duration_min, duration_sec = divmod(self.video_data['duration'], 60)
        meta_text = (f"<font color='#a0a0a0'>Views: {self.video_data['views']:,} / "
                    f"Duration: {duration_min}m {duration_sec}s</font>")
        meta_label = QLabel(meta_text)
        meta_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        velocity_label = QLabel(
            f"🔥 View velocity: {self.video_data['view_velocity']:.1f} "
            f"({self.video_data['upload_date']})"
        )
        velocity_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        velocity_label.setStyleSheet("color: #5dade2;")
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(channel_label)
        info_layout.addWidget(meta_label)
        info_layout.addWidget(velocity_label)
        
        main_layout.addLayout(info_layout)

    def _create_button_section(self, main_layout):
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        button_width = 110
        
        url_button = QPushButton(qta.icon('fa5s.link', color='white'), " Watch Video")
        url_button.setFixedWidth(button_width)
        url_button.clicked.connect(
            lambda: webbrowser.open_new_tab(self.video_data['url'])
        )
        
        exclude_button = QPushButton(qta.icon('fa5s.trash-alt', color='white'), " Exclude")
        exclude_button.setFixedWidth(button_width)
        exclude_button.setStyleSheet("background-color: #e74c3c;")
        exclude_button.clicked.connect(
            lambda: self.exclude_requested.emit(self.video_data['id'])
        )
        
        button_layout.addWidget(url_button)
        button_layout.addWidget(exclude_button)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)

    def _load_thumbnail_async(self):
        threading.Thread(target=self._load_thumbnail, daemon=True).start()

    def _load_thumbnail(self):
        try:
            response = requests.get(self.video_data['thumbnail_url'], stream=True)
            if response.status_code == 200:
                self.pixmap = QPixmap()
                self.pixmap.loadFromData(response.content)
                self.thumbnail_label.setPixmap(
                    self.pixmap.scaled(160, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.thumbnail_label.setToolTip("Click to download thumbnail")
                self.thumbnail_label.setCursor(Qt.PointingHandCursor)
        except Exception:
            self.thumbnail_label.setText("No\nImage")

    def download_thumbnail(self, event):
        if not hasattr(self, 'pixmap'):
            self.status_update.emit("Thumbnail image not yet loaded.", 3000)
            return
        
        safe_title = "".join(
            c for c in self.video_data['title'] 
            if c.isalnum() or c in " _-"
        ).rstrip()
        
        default_filename = f"{self.video_data['id']}_{safe_title[:20]}.jpg"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Thumbnail", default_filename, "JPEG Image (*.jpg)"
        )
        
        if file_path:
            try:
                self.pixmap.save(file_path, "JPG", 95)
                self.status_update.emit(
                    f"Success: {os.path.basename(file_path)} saved!", 5000
                )
            except Exception as e:
                self.status_update.emit(f"Error: Failed to save thumbnail - {e}", 5000) 