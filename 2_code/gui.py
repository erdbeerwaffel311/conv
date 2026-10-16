"""Modern macOS Desktop GUI for Universal Media, Image & Document Converter using PyQt6."""

import os
import sys
import re
import subprocess
from typing import List, Optional

# Ensure Homebrew and common macOS locations are in PATH
for p in ["/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/bin")]:
    if os.path.isdir(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{p}:{os.environ.get('PATH', '')}"

from PyQt6.QtCore import (
    Qt,
    QThread,
    pyqtSignal,
    QMimeData,
    QSize,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import ffmpeg_utils
import youtube_engine
import image_utils
import document_utils
import format_detector
from converter_models import ConversionItem, TaskStatus, TaskType


STYLESHEET = """
QMainWindow {
    background-color: #1a1a22;
    color: #e2e8f0;
}
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    color: #dedede;
}
QFrame#sidebar {
    background-color: #14141a;
    border-right: 1px solid #2d2d38;
}
QPushButton.navBtn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    font-weight: 600;
    font-size: 13px;
    text-align: left;
}
QPushButton.navBtn:hover {
    background-color: #22222e;
    color: #ffffff;
}
QPushButton.navBtn[active="true"] {
    background-color: #2563eb;
    color: #ffffff;
}
QGroupBox {
    border: 1px solid #383844;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 16px;
    font-weight: 600;
    color: #93c5fd;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    background-color: #1a1a22;
}
QLineEdit, QTextEdit, QComboBox {
    background-color: #14141a;
    border: 1px solid #383846;
    border-radius: 6px;
    padding: 6px 8px;
    color: #ffffff;
    selection-background-color: #2563eb;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
}
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:pressed {
    background-color: #1e40af;
}
QPushButton:disabled {
    background-color: #2d2d38;
    color: #64748b;
}
QPushButton#primaryBtn {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 700;
    padding: 6px 20px;
}
QPushButton#primaryBtn:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}
QPushButton#primaryBtn:disabled {
    background-color: #1e2538;
    color: #64748b;
    border: 1px solid #2b354f;
}
QPushButton#secondaryBtn {
    background-color: #272733;
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    padding: 6px 16px;
}
QPushButton#secondaryBtn:hover {
    background-color: #333344;
    color: #ffffff;
    border-color: #64748b;
}
QPushButton#secondaryBtn:disabled {
    background-color: #1e1e26;
    color: #64748b;
    border: 1px solid #2d2d38;
}
QPushButton#dangerBtn {
    background-color: #dc2626;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    border: 1px solid #ef4444;
    border-radius: 6px;
    padding: 6px 20px;
}
QPushButton#dangerBtn:hover {
    background-color: #b91c1c;
    color: #ffffff;
    border-color: #f87171;
}
QPushButton#dangerBtn:pressed {
    background-color: #991b1b;
    color: #ffffff;
}
QPushButton#dangerBtn:disabled {
    background-color: #3f1d1d;
    color: #fca5a5;
    border: 1px solid #7f1d1d;
    font-size: 13px;
    font-weight: 600;
    padding: 6px 20px;
}
QPushButton.removeBtn {
    background-color: transparent;
    color: #ef4444;
    border: 1px solid #451a1a;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
}
QPushButton.removeBtn:hover {
    background-color: #7f1d1d;
    color: #ffffff;
}
QProgressBar {
    border: 1px solid #383846;
    border-radius: 6px;
    text-align: center;
    background-color: #14141a;
    color: #ffffff;
    font-weight: 600;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #38bdf8);
    border-radius: 5px;
}
QTableWidget {
    background-color: #14141a;
    border: 1px solid #2d2d38;
    border-radius: 6px;
    gridline-color: #262634;
    color: #e2e8f0;
}
QHeaderView::section {
    background-color: #1f1f2a;
    color: #cbd5e1;
    padding: 6px;
    border: none;
    font-weight: 600;
}
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #4b5563;
    background: #14141a;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
}
"""


def get_user_downloads_dir() -> str:
    """Ermittelt dynamisch den Downloads-Ordner des aktuell angemeldeten Benutzers (macOS, Windows, Linux)."""
    try:
        downloads = os.path.expanduser("~/Downloads")
        if os.path.isdir(downloads):
            return downloads
    except Exception:
        pass

    if sys.platform == "win32":
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            dl = os.path.join(user_profile, "Downloads")
            if os.path.isdir(dl):
                return dl

    try:
        import pwd
        user_home = pwd.getpwuid(os.getuid()).pw_dir
        downloads = os.path.join(user_home, "Downloads")
        if os.path.isdir(downloads):
            return downloads
    except Exception:
        pass

    fallback = os.path.expanduser("~/Downloads")
    os.makedirs(fallback, exist_ok=True)
    return fallback


class UniversalDropArea(QFrame):
    """Drag & Drop Bereich konfigurierbar für Medien, Bilder, Dokumente oder YouTube-Links."""
    files_dropped = pyqtSignal(list)
    urls_dropped = pyqtSignal(list)

    def __init__(self, title: str, subtitle: str, file_filter: str = "", parent=None):
        super().__init__(parent)
        self.file_filter = file_filter
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")
        self.setStyleSheet("""
            QFrame#dropArea {
                border: 2px dashed #475569;
                border-radius: 12px;
                background-color: #171720;
                padding: 16px;
            }
            QFrame#dropArea:hover {
                border-color: #3b82f6;
                background-color: #1c2236;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        self.label_title = QLabel(title)
        self.label_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #ffffff; background: transparent;")
        self.label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_sub = QLabel(subtitle)
        self.label_sub.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent;")
        self.label_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.label_title)
        layout.addWidget(self.label_sub)

        if self.file_filter:
            self.browse_btn = QPushButton("Dateien durchsuchen...")
            self.browse_btn.setObjectName("secondaryBtn")
            self.browse_btn.setFixedWidth(180)
            self.browse_btn.clicked.connect(self.open_file_dialog)
            layout.addWidget(self.browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def dragEnterEvent(self, event: QDragEnterEvent):
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame#dropArea {
                    border: 2px dashed #3b82f6;
                    border-radius: 12px;
                    background-color: #1c2236;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QFrame#dropArea {
                border: 2px dashed #475569;
                border-radius: 12px;
                background-color: #171720;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        mime = event.mimeData()
        local_files = []
        web_urls = []

        if mime.hasUrls():
            for u in mime.urls():
                if u.isLocalFile():
                    path = u.toLocalFile()
                    if os.path.isfile(path):
                        local_files.append(path)
                else:
                    url_str = u.toString().strip()
                    if url_str:
                        web_urls.append(url_str)

        if mime.hasText() and not web_urls and not local_files:
            text = mime.text().strip()
            for line in text.splitlines():
                line = line.strip()
                if "http://" in line or "https://" in line:
                    web_urls.append(line)

        if web_urls:
            self.urls_dropped.emit(web_urls)
        if local_files:
            self.files_dropped.emit(local_files)

        event.acceptProposedAction()
        self.dragLeaveEvent(None)

    def open_file_dialog(self):
        start_dir = get_user_downloads_dir()
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Dateien zum Konvertieren auswählen",
            start_dir,
            self.file_filter,
        )
        if files:
            self.files_dropped.emit(files)


class WorkerThread(QThread):
    """Hintergrund-Thread zur sequentiellen Abarbeitung aller Konvertierungen."""
    progress_updated = pyqtSignal(str, float, str)
    task_finished = pyqtSignal(str, bool, str, str)
    all_finished = pyqtSignal()

    def __init__(self, tasks: List[ConversionItem]):
        super().__init__()
        self.tasks = tasks
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        for task in self.tasks:
            if self._is_cancelled:
                task.status = TaskStatus.CANCELLED
                self.task_finished.emit(task.task_id, False, "Abgebrochen", "")
                continue

            task.status = TaskStatus.RUNNING
            self.progress_updated.emit(task.task_id, 0.0, "Wird verarbeitet...")

            def progress_cb(pct: float, text: str):
                self.progress_updated.emit(task.task_id, pct, text)

            def is_cancel_cb():
                return self._is_cancelled

            # Task Routing
            if task.task_type == TaskType.YOUTUBE:
                success, msg, out_file = youtube_engine.download_youtube_media(
                    url=task.source,
                    output_dir=task.output_dir,
                    target_format=task.target_format,
                    quality=task.quality,
                    embed_thumbnail=task.embed_thumbnail,
                    progress_callback=progress_cb,
                    is_cancelled=is_cancel_cb,
                )
            elif task.task_type == TaskType.IMAGE:
                base_name = os.path.splitext(os.path.basename(task.source))[0]
                target_fmt = task.target_format.upper()
                ext = image_utils.IMAGE_FORMATS.get(target_fmt, {}).get("ext", target_fmt.lower())
                out_file = os.path.join(task.output_dir, f"{base_name}.{ext}")
                if os.path.abspath(out_file) == os.path.abspath(task.source):
                    out_file = os.path.join(task.output_dir, f"{base_name}_neu.{ext}")

                success, msg = image_utils.convert_image(
                    input_file=task.source,
                    output_file=out_file,
                    target_format=task.target_format,
                    quality_str=task.quality,
                    progress_callback=progress_cb,
                )
            elif task.task_type == TaskType.DOCUMENT:
                base_name = os.path.splitext(os.path.basename(task.source))[0]
                ext = task.target_format.lower()
                out_file = os.path.join(task.output_dir, f"{base_name}.{ext}")
                if os.path.abspath(out_file) == os.path.abspath(task.source):
                    out_file = os.path.join(task.output_dir, f"{base_name}_neu.{ext}")

                success, msg = document_utils.convert_document(
                    input_file=task.source,
                    output_file=out_file,
                    target_format=task.target_format,
                    progress_callback=progress_cb,
                )
            else:
                # LOCAL_FILE (Audio & Video)
                base_name = os.path.splitext(os.path.basename(task.source))[0]
                target_fmt = task.target_format.upper()
                if target_fmt in ffmpeg_utils.AUDIO_FORMATS:
                    ext = ffmpeg_utils.AUDIO_FORMATS[target_fmt]["ext"]
                elif target_fmt in ffmpeg_utils.VIDEO_FORMATS:
                    ext = ffmpeg_utils.VIDEO_FORMATS[target_fmt]["ext"]
                else:
                    ext = target_fmt.lower()

                out_file = os.path.join(task.output_dir, f"{base_name}.{ext}")
                if os.path.abspath(out_file) == os.path.abspath(task.source):
                    out_file = os.path.join(task.output_dir, f"{base_name}_neu.{ext}")

                custom_scale = None
                for res in ["1080p", "720p", "480p"]:
                    if res in task.quality:
                        custom_scale = res
                        break

                success, msg = ffmpeg_utils.convert_file(
                    input_file=task.source,
                    output_file=out_file,
                    target_format=task.target_format,
                    quality=task.quality,
                    custom_scale=custom_scale,
                    progress_callback=progress_cb,
                    is_cancelled=is_cancel_cb,
                )

            task.status = TaskStatus.SUCCESS if success else TaskStatus.FAILED
            task.output_file = out_file if success else None
            task.error_message = None if success else msg
            self.task_finished.emit(task.task_id, success, msg, out_file or "")

        self.all_finished.emit()


class MainWindow(QMainWindow):
    """Hauptfenster mit einklappbarer Seitenleiste und interaktiver Tabellen-Formatwahl."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal Converter (YouTube, Audio, Video, Bilder, Dokumente)")
        self.resize(1080, 760)
        self.setMinimumSize(920, 640)
        self.setStyleSheet(STYLESHEET)

        self.default_output_dir = get_user_downloads_dir()
        self.current_tasks: List[ConversionItem] = []
        self.worker_thread: Optional[WorkerThread] = None

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Linke einklappbare Seitenleiste
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("sidebar")
        self.sidebar_frame.setFixedWidth(210)
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(12, 18, 12, 18)
        sidebar_layout.setSpacing(8)

        logo_label = QLabel("Universal Converter")
        logo_label.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff; padding-left: 8px; margin-bottom: 8px;")
        sidebar_layout.addWidget(logo_label)

        self.nav_buttons: List[QPushButton] = []
        self.btn_nav_yt = self.create_nav_button("YouTube", 0)
        self.btn_nav_av = self.create_nav_button("Audio / Video", 1)
        self.btn_nav_img = self.create_nav_button("Bilder", 2)
        self.btn_nav_doc = self.create_nav_button("Dokumente / Tabellen", 3)
        self.btn_nav_info = self.create_nav_button("Info / Formate", 4)

        sidebar_layout.addWidget(self.btn_nav_yt)
        sidebar_layout.addWidget(self.btn_nav_av)
        sidebar_layout.addWidget(self.btn_nav_img)
        sidebar_layout.addWidget(self.btn_nav_doc)
        sidebar_layout.addSpacing(12)
        sidebar_layout.addWidget(self.btn_nav_info)

        sidebar_layout.addStretch()

        lbl_ver = QLabel("Lokal & Sicher")
        lbl_ver.setStyleSheet("font-size: 11px; color: #64748b; padding-left: 8px;")
        sidebar_layout.addWidget(lbl_ver)

        root_layout.addWidget(self.sidebar_frame)

        # 2. Rechter Hauptbereich
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(18, 14, 18, 14)
        content_layout.setSpacing(12)

        # Kopfleiste
        top_bar = QHBoxLayout()

        self.btn_toggle_sidebar = QPushButton("Menü ausblenden")
        self.btn_toggle_sidebar.setObjectName("secondaryBtn")
        self.btn_toggle_sidebar.setToolTip("Seitenleiste ein- oder ausblenden")
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        top_bar.addWidget(self.btn_toggle_sidebar)

        self.header_title = QLabel("YouTube Downloader")
        self.header_title.setStyleSheet("font-size: 17px; font-weight: 700; color: #ffffff; margin-left: 8px;")
        top_bar.addWidget(self.header_title)

        top_bar.addStretch()

        ffmpeg_status = "FFmpeg bereit" if ffmpeg_utils.FFMPEG_PATH else "FFmpeg nicht gefunden"
        ffmpeg_color = "#10b981" if ffmpeg_utils.FFMPEG_PATH else "#ef4444"
        self.badge_ffmpeg = QLabel(ffmpeg_status)
        self.badge_ffmpeg.setStyleSheet(f"background-color: #1e293b; color: {ffmpeg_color}; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 11px;")
        top_bar.addWidget(self.badge_ffmpeg)

        content_layout.addLayout(top_bar)

        # Zielordner-Leiste
        dest_bar = QFrame()
        dest_bar.setStyleSheet("background-color: #1e1e28; border-radius: 8px; padding: 4px;")
        dest_layout = QHBoxLayout(dest_bar)
        dest_layout.setContentsMargins(8, 4, 8, 4)

        dest_icon = QLabel("Zielordner:")
        dest_icon.setStyleSheet("font-weight: 600; color: #94a3b8;")
        dest_layout.addWidget(dest_icon)

        self.dest_path_edit = QLineEdit(self.default_output_dir)
        self.dest_path_edit.setReadOnly(True)
        dest_layout.addWidget(self.dest_path_edit, 1)

        self.btn_browse_dest = QPushButton("Ordner wählen...")
        self.btn_browse_dest.setObjectName("secondaryBtn")
        self.btn_browse_dest.clicked.connect(self.choose_output_directory)
        dest_layout.addWidget(self.btn_browse_dest)

        self.btn_open_folder = QPushButton("Im Finder öffnen")
        self.btn_open_folder.setObjectName("secondaryBtn")
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        dest_layout.addWidget(self.btn_open_folder)

        content_layout.addWidget(dest_bar)

        # Stacked Pages
        self.pages = QStackedWidget()
        self.setup_youtube_page()
        self.setup_media_page()
        self.setup_image_page()
        self.setup_document_page()
        self.setup_info_page()

        content_layout.addWidget(self.pages, 0)

        # 3. Gemeinsame Warteschlange
        queue_group = QGroupBox("Warteschlange (Format und Qualität können pro Zeile geändert werden)")
        queue_layout = QVBoxLayout(queue_group)
        queue_layout.setContentsMargins(10, 10, 10, 10)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Kategorie",
            "Datei / Link",
            "Zielformat",
            "Qualität / Option",
            "Status",
            "Fortschritt",
            "Aktion",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 170)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        queue_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Konvertierung starten")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setFixedHeight(36)
        self.btn_start.clicked.connect(self.start_processing)
        btn_layout.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_cancel.setObjectName("dangerBtn")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_processing)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_clear = QPushButton("Liste leeren")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.setFixedHeight(36)
        self.btn_clear.clicked.connect(self.clear_queue)
        btn_layout.addWidget(self.btn_clear)

        queue_layout.addLayout(btn_layout)
        content_layout.addWidget(queue_group, 1)

        root_layout.addWidget(content_container, 1)

        self.set_active_page(0)

    def create_nav_button(self, text: str, page_index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "navBtn")
        btn.setProperty("active", "false")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.set_active_page(page_index))
        self.nav_buttons.append(btn)
        return btn

    def set_active_page(self, index: int):
        self.pages.setCurrentIndex(index)
        titles = [
            "YouTube Downloader",
            "Audio / Video Konverter",
            "Bilder-Konverter",
            "Dokumente / Tabellen",
            "Info / Formate",
        ]
        if 0 <= index < len(titles):
            self.header_title.setText(titles[index])

        for i, btn in enumerate(self.nav_buttons):
            is_active = (i == index)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def toggle_sidebar(self):
        visible = self.sidebar_frame.isVisible()
        self.sidebar_frame.setVisible(not visible)
        self.btn_toggle_sidebar.setText("Menü einblenden" if visible else "Menü ausblenden")

    # ================= Pages =================

    def setup_youtube_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        # 1. Prominenter Drag & Drop Bereich für YouTube Links
        drop = UniversalDropArea(
            title="YouTube-Link(s) hierher ziehen oder ablegen",
            subtitle="Ziehe Links direkt aus dem Browser (Safari, Chrome) hierher, oder füge sie unten ein",
        )
        drop.urls_dropped.connect(self.on_youtube_urls_dropped)
        drop.files_dropped.connect(self.on_youtube_files_dropped)
        layout.addWidget(drop)

        # 2. Text-Eingabezeile für Links
        input_box = QHBoxLayout()
        self.yt_url_text = QLineEdit()
        self.yt_url_text.setPlaceholderText("YouTube-Link hier einfügen: https://www.youtube.com/watch?v=... oder https://youtu.be/...")
        input_box.addWidget(self.yt_url_text, 1)

        btn_paste = QPushButton("Aus Zwischenablage einfügen")
        btn_paste.setObjectName("secondaryBtn")
        btn_paste.clicked.connect(self.paste_from_clipboard)
        input_box.addWidget(btn_paste)

        layout.addLayout(input_box)

        # 3. Optionen
        opts_layout = QHBoxLayout()

        fmt_box = QVBoxLayout()
        fmt_box.addWidget(QLabel("Vorauswahl Zielformat:"))
        self.yt_fmt_combo = QComboBox()
        self.yt_fmt_combo.addItems(["MP3", "MP4", "WAV", "FLAC", "M4A", "MOV"])
        self.yt_fmt_combo.currentTextChanged.connect(self.on_yt_format_changed)
        fmt_box.addWidget(self.yt_fmt_combo)
        opts_layout.addLayout(fmt_box)

        qual_box = QVBoxLayout()
        qual_box.addWidget(QLabel("Vorauswahl Qualität:"))
        self.yt_quality_combo = QComboBox()
        qual_box.addWidget(self.yt_quality_combo)
        opts_layout.addLayout(qual_box)

        check_box = QVBoxLayout()
        check_box.addSpacing(16)
        self.yt_cb_metadata = QCheckBox("Album-Cover und Metadaten einbetten")
        self.yt_cb_metadata.setChecked(True)
        check_box.addWidget(self.yt_cb_metadata)
        opts_layout.addLayout(check_box)

        layout.addLayout(opts_layout)

        self.update_yt_quality_options("MP3")

        add_box = QHBoxLayout()
        add_box.addStretch()
        self.btn_add_yt = QPushButton("Zur Warteschlange hinzufügen")
        self.btn_add_yt.clicked.connect(self.add_youtube_to_queue)
        add_box.addWidget(self.btn_add_yt)
        layout.addLayout(add_box)

        self.pages.addWidget(page)

    def setup_media_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        drop = UniversalDropArea(
            title="Audio- und Videodateien hierher ziehen",
            subtitle="Unterstützt: MP4, MOV, MKV, AVI, WEBM, MP3, WAV, FLAC, AIFF, AAC, OGG uvm.",
            file_filter="Media (*.mp4 *.mov *.mkv *.avi *.webm *.mp3 *.wav *.flac *.m4a *.aiff *.aac *.ogg *.opus);;Alle (*.*)",
        )
        drop.files_dropped.connect(self.on_files_dropped_handler)
        layout.addWidget(drop)

        hint = QLabel("Hinweis: Nach dem Hinzufügen kann das Zielformat direkt in der Zeile angepasst werden.")
        hint.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(hint)

        self.pages.addWidget(page)

    def setup_image_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        drop = UniversalDropArea(
            title="Bilder hierher ziehen und ablegen",
            subtitle="Unterstützt: JPEG, JPG, HEIC, PNG, WEBP, TIFF, BMP, GIF, ICO, PSD, AVIF",
            file_filter="Bilder (*.jpg *.jpeg *.heic *.heif *.png *.webp *.tiff *.tif *.bmp *.gif *.ico *.psd *.avif);;Alle (*.*)",
        )
        drop.files_dropped.connect(self.on_files_dropped_handler)
        layout.addWidget(drop)

        hint = QLabel("Hinweis: HEIC, PNG, JPEG etc. können in jedes beliebige Bildformat umgewandelt werden.")
        hint.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(hint)

        self.pages.addWidget(page)

    def setup_document_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        drop = UniversalDropArea(
            title="Dokumente und Tabellen hierher ziehen und ablegen",
            subtitle="Unterstützt: .pdf, .docx, .xlsx, .csv, .txt, .html, .rtf, .json",
            file_filter="Dokumente und Tabellen (*.pdf *.docx *.xlsx *.xls *.csv *.tsv *.txt *.html *.rtf *.json);;Alle (*.*)",
        )
        drop.files_dropped.connect(self.on_files_dropped_handler)
        layout.addWidget(drop)

        hint = QLabel("Formaterkennung aktiv: Tabellen (XLSX, CSV) und Textdokumente (PDF, DOCX) bieten ausschließlich kompatible Zielformate.")
        hint.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(hint)

        self.pages.addWidget(page)

    def setup_info_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        info_content = QWidget()
        info_layout = QVBoxLayout(info_content)

        header = QLabel("Unterstützte Formate und Kompatibilitäts-Matrix")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #60a5fa;")
        info_layout.addWidget(header)

        rules = [
            ("YouTube Downloader", "MP3 (bis 320k), MP4 (bis 4K), WAV, FLAC, M4A, MOV. Cover und Metadaten werden eingebettet."),
            ("Audio / Video", "Video nach Video (MP4, MOV, MKV, WEBM, GIF), Video nach Audio (MP3, WAV, FLAC, AIFF, AAC), Audio nach Audio."),
            ("Bilder (High Quality)", "JPEG, PNG (mit Transparenz), HEIC (Apple Format), WebP, TIFF, BMP, ICO (Multi-Size Icon), PDF."),
            ("Tabellendokumente (XLSX, CSV)", "XLSX konvertiert nach CSV, PDF, JSON, HTML. CSV konvertiert nach XLSX, PDF, JSON, HTML. (Keine inkompatible DOCX-Konvertierung)."),
            ("Textdokumente (PDF, DOCX, TXT)", "PDF konvertiert nach DOCX, TXT, PNG, HTML. DOCX konvertiert nach PDF, TXT, HTML, RTF. TXT konvertiert nach PDF, DOCX."),
        ]
        for title, desc in rules:
            gb = QGroupBox(title)
            v = QVBoxLayout(gb)
            lbl = QLabel(desc)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #cbd5e1;")
            v.addWidget(lbl)
            info_layout.addWidget(gb)

        scroll.setWidget(info_content)
        layout.addWidget(scroll)
        self.pages.addWidget(page)

    # ================= Event Handlers =================

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.yt_url_text.setText(text)
            self.add_youtube_to_queue()

    def on_youtube_urls_dropped(self, urls: List[str]):
        """Behandelt aus dem Browser gezogene Links."""
        for u in urls:
            self.add_single_youtube_url(u)

    def on_youtube_files_dropped(self, files: List[str]):
        """Falls eine Textdatei mit YouTube Links abgelegt wird."""
        for f in files:
            if f.endswith((".txt", ".text")):
                try:
                    with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                        for line in fp:
                            line = line.strip()
                            if "youtube.com" in line or "youtu.be" in line:
                                self.add_single_youtube_url(line)
                except Exception:
                    pass
            else:
                # Normale Datei zum Konverter hinzufügen
                self.on_files_dropped_handler([f])

    def on_yt_format_changed(self, text: str):
        self.update_yt_quality_options(text)

    def update_yt_quality_options(self, fmt_text: str):
        self.yt_quality_combo.clear()
        presets = format_detector.get_quality_presets(fmt_text)
        self.yt_quality_combo.addItems(presets)

    def choose_output_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Zielordner auswählen", self.default_output_dir)
        if folder:
            self.default_output_dir = folder
            self.dest_path_edit.setText(folder)
            for t in self.current_tasks:
                if t.status == TaskStatus.PENDING:
                    t.output_dir = folder

    def open_output_folder(self):
        target = self.dest_path_edit.text()
        if os.path.exists(target):
            if sys.platform == "darwin":
                subprocess.run(["open", target])
            elif sys.platform == "win32":
                os.startfile(target)
            else:
                subprocess.run(["xdg-open", target])
        else:
            QMessageBox.information(self, "Ordner nicht gefunden", f"Der Ordner existiert noch nicht:\n{target}")

    def on_files_dropped_handler(self, file_paths: List[str]):
        """Wird aufgerufen, wenn Dateien auf ein beliebiges Drop-Feld gezogen werden."""
        for fp in file_paths:
            category, allowed, default_fmt, task_type = format_detector.detect_file_info(fp)
            presets = format_detector.get_quality_presets(default_fmt)
            default_quality = presets[0] if presets else "Standard"

            task_id = f"task_{len(self.current_tasks) + 1}_{os.path.basename(fp)}"
            item = ConversionItem(
                task_id=task_id,
                task_type=task_type,
                source=fp,
                target_format=default_fmt,
                quality=default_quality,
                output_dir=self.dest_path_edit.text(),
            )
            self.add_task_to_table(item, category, allowed)

    def add_single_youtube_url(self, raw_url: str):
        url_pattern = re.compile(r'https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?v=|shorts/|playlist\?list=)|youtu\.be/)[a-zA-Z0-9_\-]+[^\s]*')
        m = url_pattern.search(raw_url)
        url_to_add = m.group(0) if m else None
        if not url_to_add and ("youtube.com" in raw_url or "youtu.be" in raw_url):
            for part in raw_url.split():
                if "youtube.com" in part or "youtu.be" in part:
                    url_to_add = part.strip()
                    break

        if not url_to_add:
            return

        fmt_text = self.yt_fmt_combo.currentText().split()[0]
        quality = self.yt_quality_combo.currentText().split()[0]
        category, allowed, _, task_type = format_detector.detect_file_info(url_to_add)

        task_id = f"yt_{len(self.current_tasks) + 1}"
        item = ConversionItem(
            task_id=task_id,
            task_type=TaskType.YOUTUBE,
            source=url_to_add,
            target_format=fmt_text,
            quality=quality,
            output_dir=self.dest_path_edit.text(),
            embed_thumbnail=self.yt_cb_metadata.isChecked(),
        )
        self.add_task_to_table(item, category, allowed)

    def add_youtube_to_queue(self):
        text = self.yt_url_text.text().strip()
        if not text:
            QMessageBox.warning(self, "Keine URL", "Bitte gib einen YouTube-Link ein oder ziehe ihn in das Feld.")
            return

        for part in text.split():
            self.add_single_youtube_url(part)

        self.yt_url_text.clear()

    def add_task_to_table(self, task: ConversionItem, category: str, allowed_formats: List[str]):
        """Fügt eine Aufgabe zur Tabelle hinzu mit interaktiver Format- und Qualitätsauswahl."""
        self.current_tasks.append(task)
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 0. Kategorie
        item_cat = QTableWidgetItem(category)
        self.table.setItem(row, 0, item_cat)

        # 1. Dateiname / Link
        item_src = QTableWidgetItem(task.display_source())
        item_src.setToolTip(task.source)
        self.table.setItem(row, 1, item_src)

        # 2. Interaktives Zielformat Dropdown (Ausschließlich kompatible Formate)
        fmt_combo = QComboBox()
        fmt_combo.addItems(allowed_formats)
        if task.target_format in allowed_formats:
            fmt_combo.setCurrentText(task.target_format)
        self.table.setCellWidget(row, 2, fmt_combo)

        # 3. Interaktives Qualität Dropdown
        qual_combo = QComboBox()
        presets = format_detector.get_quality_presets(fmt_combo.currentText())
        qual_combo.addItems(presets)
        if task.quality in presets:
            qual_combo.setCurrentText(task.quality)
        self.table.setCellWidget(row, 3, qual_combo)

        # Event: Wenn Benutzer das Format in der Tabellenzeile ändert
        def on_format_changed(new_fmt, t=task, qc=qual_combo):
            t.target_format = new_fmt
            qc.clear()
            p = format_detector.get_quality_presets(new_fmt)
            qc.addItems(p)
            t.quality = p[0] if p else "Standard"

        fmt_combo.currentTextChanged.connect(on_format_changed)

        # Event: Wenn Benutzer die Qualität in der Zeile ändert
        def on_quality_changed(new_q, t=task):
            if new_q:
                t.quality = new_q

        qual_combo.currentTextChanged.connect(on_quality_changed)

        # 4. Status
        item_status = QTableWidgetItem(task.status.value)
        self.table.setItem(row, 4, item_status)

        # 5. Fortschrittsbalken
        pbar = QProgressBar()
        pbar.setValue(0)
        pbar.setTextVisible(True)
        pbar.setFormat("%p%")
        self.table.setCellWidget(row, 5, pbar)

        # 6. Entfernen Button
        btn_remove = QPushButton("Entfernen")
        btn_remove.setProperty("class", "removeBtn")
        btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_remove.clicked.connect(lambda _, t_id=task.task_id: self.remove_task(t_id))
        self.table.setCellWidget(row, 6, btn_remove)

    def remove_task(self, task_id: str):
        if self.worker_thread and self.worker_thread.isRunning():
            return
        for idx, task in enumerate(self.current_tasks):
            if task.task_id == task_id:
                self.current_tasks.pop(idx)
                self.table.removeRow(idx)
                break

    def on_table_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self.current_tasks):
            task = self.current_tasks[row]
            if task.status == TaskStatus.SUCCESS and task.output_file and os.path.exists(task.output_file):
                if sys.platform == "darwin":
                    subprocess.run(["open", "-R", task.output_file])
                elif sys.platform == "win32":
                    subprocess.run(["explorer", f"/select,{os.path.normpath(task.output_file)}"])
                else:
                    subprocess.run(["xdg-open", os.path.dirname(task.output_file)])
            elif task.status == TaskStatus.FAILED:
                QMessageBox.warning(self, "Fehlerdetails", f"Aufgabe fehlgeschlagen:\n\n{task.error_message or 'Unbekannter Fehler'}")

    def start_processing(self):
        pending_tasks = [t for t in self.current_tasks if t.status in [TaskStatus.PENDING, TaskStatus.FAILED]]
        if not pending_tasks:
            QMessageBox.information(self, "Keine offenen Aufgaben", "Die Warteschlange enthält keine offenen Aufgaben.")
            return

        # UI sperren
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_clear.setEnabled(False)

        # Format-Auswahl in der Tabelle während des Laufs deaktivieren
        for row in range(self.table.rowCount()):
            w2 = self.table.cellWidget(row, 2)
            w3 = self.table.cellWidget(row, 3)
            w6 = self.table.cellWidget(row, 6)
            if w2:
                w2.setEnabled(False)
            if w3:
                w3.setEnabled(False)
            if w6:
                w6.setEnabled(False)

        self.worker_thread = WorkerThread(pending_tasks)
        self.worker_thread.progress_updated.connect(self.on_worker_progress)
        self.worker_thread.task_finished.connect(self.on_worker_task_finished)
        self.worker_thread.all_finished.connect(self.on_worker_all_finished)
        self.worker_thread.start()

    def cancel_processing(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.cancel()
            self.btn_cancel.setEnabled(False)

    def on_worker_progress(self, task_id: str, pct: float, text: str):
        for idx, task in enumerate(self.current_tasks):
            if task.task_id == task_id:
                pbar: QProgressBar = self.table.cellWidget(idx, 5)
                if pbar:
                    pbar.setValue(int(pct))
                    pbar.setFormat(f"{int(pct)}% - {text}")
                status_item = self.table.item(idx, 4)
                if status_item:
                    status_item.setText("Läuft...")
                break

    def on_worker_task_finished(self, task_id: str, success: bool, message: str, out_file: str):
        for idx, task in enumerate(self.current_tasks):
            if task.task_id == task_id:
                pbar: QProgressBar = self.table.cellWidget(idx, 5)
                status_item = self.table.item(idx, 4)
                task.error_message = message if not success else None
                task.output_file = out_file if success else None
                if success:
                    if pbar:
                        pbar.setValue(100)
                        pbar.setFormat("Fertig")
                    if status_item:
                        status_item.setText("Fertig")
                        status_item.setForeground(QColor("#10b981"))
                else:
                    if pbar:
                        pbar.setFormat("Fehler")
                    if status_item:
                        status_item.setText("Fehler")
                        status_item.setForeground(QColor("#ef4444"))
                        status_item.setToolTip(message)
                break

    def on_worker_all_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_clear.setEnabled(True)

        for row in range(self.table.rowCount()):
            w2 = self.table.cellWidget(row, 2)
            w3 = self.table.cellWidget(row, 3)
            w6 = self.table.cellWidget(row, 6)
            if w2:
                w2.setEnabled(True)
            if w3:
                w3.setEnabled(True)
            if w6:
                w6.setEnabled(True)

        failed_tasks = [t for t in self.current_tasks if t.status == TaskStatus.FAILED]
        if failed_tasks:
            err_summary = "\n".join([f"- {t.display_source()}: {t.error_message or 'Fehler'}" for t in failed_tasks[:5]])
            if len(failed_tasks) > 5:
                err_summary += f"\n... und {len(failed_tasks) - 5} weitere."
            QMessageBox.warning(
                self,
                "Verarbeitung abgeschlossen (mit Fehlern)",
                f"Einige Aufgaben konnten nicht abgeschlossen werden:\n\n{err_summary}\n\nTipp: Doppelklick auf die Zeile zeigt Details."
            )
        else:
            QMessageBox.information(self, "Abgeschlossen", "Alle Aufgaben in der Warteschlange wurden erfolgreich abgearbeitet!")

    def clear_queue(self):
        if self.worker_thread and self.worker_thread.isRunning():
            return
        self.current_tasks.clear()
        self.table.setRowCount(0)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Universal Converter")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
