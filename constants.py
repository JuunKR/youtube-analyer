import sys
import os

def get_db_path():
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 실행파일인 경우 - 모든 플랫폼에서 Documents 폴더 사용
        documents_dir = os.path.expanduser('~/Documents')
        return os.path.join(documents_dir, '.youtube_analysis.db')
    else:
        # 개발 환경에서는 현재 디렉토리에 저장
        return 'youtube_analysis.db'

DB_FILE = get_db_path()
SCOPES = ['https://www.googleapis.com/auth/drive.file']

DEFAULT_SETTINGS = {
    'min_views': '100000',
    'min_duration': '60',
    'max_subs': '-1',
    'target_count': '10',
    'order': 'viewCount'
}

ORDER_OPTIONS = {
    'Most Views': 'viewCount',
    'Relevance': 'relevance', 
    'Latest Upload': 'date'
}

COLORS = {
    'background': '#2c313c',
    'widget_bg': '#353b48',
    'input_bg': '#4a5160',
    'border': '#5a6170',
    'accent': '#5dade2',
    'accent_hover': '#85c1e9',
    'text': '#e0e0e0',
    'text_dim': '#a0a0a0',
    'disabled': '#909090',
    'combo_bg': '#3a4150',
    'combo_hover': '#4a5160',
    'combo_selected': '#5dade2'
}

def get_platform_stylesheet():
    font_families = {
        "darwin": "'Apple SD Gothic Neo', sans-serif",
        "win32": "'Malgun Gothic', '맑은 고딕', sans-serif"
    }
    font_family = font_families.get(sys.platform, "sans-serif")
    
    return f"""
    QWidget {{ 
        font-family: {font_family}; 
        color: {COLORS['text']}; 
        font-size: 10pt; 
    }}
    QMainWindow {{ 
        background-color: {COLORS['background']}; 
    }}
    QGroupBox {{ 
        background-color: {COLORS['widget_bg']}; 
        border: 1px solid {COLORS['border']}; 
        border-radius: 8px; 
        margin-top: 10px; 
        font-weight: bold; 
    }}
    QGroupBox::title {{ 
        subcontrol-origin: margin; 
        subcontrol-position: top left; 
        padding: 0 5px; 
        margin-left: 10px; 
        color: {COLORS['accent']}; 
    }}
    QLabel {{ 
        background-color: transparent; 
    }}
    QLabel a {{ 
        color: {COLORS['text']}; 
        text-decoration: none; 
    }}
    QLabel a:hover {{ 
        text-decoration: underline; 
    }}
    QLineEdit, QTableWidget {{ 
        background-color: {COLORS['input_bg']}; 
        border: 1px solid {COLORS['border']}; 
        border-radius: 4px; 
        padding: 5px; 
        gridline-color: {COLORS['border']}; 
    }}
    QLineEdit:hover {{
        border: 1px solid {COLORS['accent']};
        background-color: {COLORS['combo_hover']};
    }}
    QLineEdit:focus {{ 
        border: 1px solid {COLORS['accent']}; 
    }}
    QComboBox {{
        background-color: {COLORS['combo_bg']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        padding: 6px 8px;
        font-size: 10pt;
        color: {COLORS['text']};
        min-height: 16px;
        selection-background-color: {COLORS['combo_selected']};
    }}
    QComboBox:hover {{
        border: 1px solid {COLORS['accent']};
        background-color: {COLORS['combo_hover']};
    }}
    QComboBox:focus {{
        border: 1px solid {COLORS['accent']};
        background-color: {COLORS['combo_hover']};
        outline: none;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left-width: 1px;
        border-left-color: {COLORS['border']};
        border-left-style: solid;
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
        background-color: {COLORS['accent']};
    }}
    QComboBox::drop-down:hover {{
        background-color: {COLORS['accent_hover']};
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 3px solid transparent;
        border-right: 3px solid transparent;
        border-top: 5px solid white;
        margin-left: 1px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLORS['widget_bg']};
        border: 1px solid {COLORS['accent']};
        border-radius: 4px;
        color: {COLORS['text']};
        font-size: 10pt;
        padding: 2px;
        outline: none;
        selection-background-color: {COLORS['combo_selected']};
        selection-color: white;
    }}
    QComboBox QAbstractItemView::item {{
        padding: 8px 12px;
        border-radius: 2px;
        margin: 1px;
        min-height: 16px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background-color: {COLORS['combo_hover']};
        color: white;
    }}
    QComboBox QAbstractItemView::item:selected {{
        background-color: {COLORS['combo_selected']};
        color: white;
        font-weight: 500;
    }}
    QHeaderView::section {{ 
        background-color: {COLORS['accent']}; 
        color: white; 
        padding: 4px; 
        border: 1px solid {COLORS['widget_bg']}; 
        font-weight: bold; 
    }}
    QPushButton {{ 
        background-color: {COLORS['accent']}; 
        color: #ffffff; 
        border: none; 
        padding: 10px 16px; 
        border-radius: 4px; 
        font-weight: bold; 
    }}
    QPushButton:hover {{ 
        background-color: {COLORS['accent_hover']}; 
    }}
    QPushButton:disabled {{ 
        background-color: {COLORS['border']}; 
        color: {COLORS['disabled']}; 
    }}
    QScrollArea {{ 
        border: none; 
        background-color: {COLORS['background']}; 
    }}
    QScrollBar:vertical {{ 
        border: none; 
        background: {COLORS['widget_bg']}; 
        width: 10px; 
        margin: 0px; 
    }}
    QScrollBar::handle:vertical {{ 
        background: {COLORS['border']}; 
        min-height: 20px; 
        border-radius:5px; 
    }}
    QMessageBox, QDialog {{ 
        background-color: {COLORS['widget_bg']}; 
    }}
    QMessageBox QLabel, QDialog QLabel {{ 
        color: {COLORS['text']}; 
    }}
    QMessageBox QPushButton, QDialog QPushButton {{ 
        min-width: 80px; 
    }}
    QInputDialog QLineEdit {{ 
        background-color: #ffffff; 
        color: #212121; 
        border: 1px solid {COLORS['disabled']}; 
    }}
    QInputDialog QLineEdit:focus {{ 
        border: 1px solid {COLORS['accent']}; 
    }}
    QTabWidget::pane {{ 
        border: 1px solid {COLORS['border']}; 
        top: -1px; 
    }}
    QTabBar::tab {{ 
        background: {COLORS['widget_bg']}; 
        color: {COLORS['text']}; 
        padding: 8px 20px; 
        border: 1px solid {COLORS['border']}; 
        border-bottom: none; 
    }}
    QTabBar::tab:selected {{ 
        background: {COLORS['input_bg']}; 
        font-weight: bold; 
    }}
    QTableWidget::item:selected {{ 
        background-color: {COLORS['accent']}; 
        color: #ffffff; 
    }}
    """ 