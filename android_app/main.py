"""
Universal Media Converter - Mobile Android App (Kivy).
Designed for Samsung Galaxy A55 5G (Android 14/15/16, ARM64).
"""

import os
import sys
import threading
from typing import List, Optional

# Kivy configuration before imports
os.environ["KIVY_NO_CONSOLELOG"] = "0"

from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.graphics import Color, RoundedRectangle, Rectangle

# Determine storage path for Android vs Desktop
def get_android_download_dir() -> str:
    """Returns the Downloads directory for Android (Samsung OneUI) or Desktop fallback."""
    try:
        from android.storage import primary_external_storage_path
        base = primary_external_storage_path()
        dl_dir = os.path.join(base, "Download", "UniversalConverter")
        os.makedirs(dl_dir, exist_ok=True)
        return dl_dir
    except Exception:
        pass

    # Standard Android path
    for test_path in ["/storage/emulated/0/Download/UniversalConverter", "/sdcard/Download/UniversalConverter"]:
        try:
            os.makedirs(test_path, exist_ok=True)
            return test_path
        except Exception:
            pass

    fallback = os.path.join(os.path.expanduser("~"), "Downloads", "UniversalConverter")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def request_android_permissions():
    """Request runtime permissions on modern Android (Android 13, 14, 15+)."""
    try:
        from android.permissions import request_permissions, Permission
        perms = [
            Permission.INTERNET,
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
        ]
        # Android 13+ Granular Media Permissions
        if hasattr(Permission, "READ_MEDIA_AUDIO"):
            perms.append(Permission.READ_MEDIA_AUDIO)
        if hasattr(Permission, "READ_MEDIA_VIDEO"):
            perms.append(Permission.READ_MEDIA_VIDEO)
        if hasattr(Permission, "READ_MEDIA_IMAGES"):
            perms.append(Permission.READ_MEDIA_IMAGES)
        request_permissions(perms)
    except Exception:
        pass


class StyledCard(BoxLayout):
    """Modern dark card widget with rounded corners."""
    def __init__(self, bg_color=(0.12, 0.12, 0.16, 1.0), radius=[16], **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.radius = radius
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class YouTubeScreen(Screen):
    """Screen for downloading YouTube videos and audio."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.download_thread = None
        self.is_cancelled = False

        layout = BoxLayout(orientation="vertical", spacing=14, padding=[18, 16, 18, 16])

        # Header Info Card
        info_card = StyledCard(orientation="vertical", size_hint_y=None, height=90, padding=[14, 10])
        lbl_title = Label(
            text="YouTube Downloader",
            font_size="19sp",
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=0.55,
            halign="left"
        )
        lbl_title.bind(size=lbl_title.setter("text_size"))
        lbl_sub = Label(
            text="Lade Musik als MP3/M4A oder Videos in HD herunter.",
            font_size="13sp",
            color=(0.6, 0.65, 0.75, 1),
            size_hint_y=0.45,
            halign="left"
        )
        lbl_sub.bind(size=lbl_sub.setter("text_size"))
        info_card.add_widget(lbl_title)
        info_card.add_widget(lbl_sub)
        layout.add_widget(info_card)

        # Input Card
        input_card = StyledCard(orientation="vertical", spacing=10, size_hint_y=None, height=130, padding=[14, 12])
        self.url_input = TextInput(
            hint_text="YouTube-Link hier einfügen (https://...)",
            multiline=False,
            size_hint_y=None,
            height=46,
            background_color=(0.08, 0.08, 0.11, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.2, 0.5, 1, 1),
            font_size="14sp",
            padding=[10, 12]
        )
        input_card.add_widget(self.url_input)

        paste_btn = Button(
            text="Aus Zwischenablage einfügen",
            size_hint_y=None,
            height=42,
            background_normal="",
            background_color=(0.18, 0.22, 0.32, 1),
            color=(1, 1, 1, 1),
            font_size="13sp",
            bold=True
        )
        paste_btn.bind(on_release=self.paste_clipboard)
        input_card.add_widget(paste_btn)
        layout.add_widget(input_card)

        # Options Card
        opts_card = StyledCard(orientation="horizontal", spacing=10, size_hint_y=None, height=75, padding=[14, 12])
        
        # Format selector
        fmt_box = BoxLayout(orientation="vertical", spacing=4)
        fmt_lbl = Label(text="Format:", font_size="12sp", color=(0.7, 0.75, 0.85, 1), size_hint_y=0.4)
        self.fmt_spinner = Spinner(
            text="MP3",
            values=["MP3", "MP4", "M4A", "WAV"],
            size_hint_y=0.6,
            background_normal="",
            background_color=(0.15, 0.18, 0.26, 1),
            color=(1, 1, 1, 1),
            font_size="13sp",
            bold=True
        )
        self.fmt_spinner.bind(text=self.on_format_change)
        fmt_box.add_widget(fmt_lbl)
        fmt_box.add_widget(self.fmt_spinner)
        opts_card.add_widget(fmt_box)

        # Quality selector
        qual_box = BoxLayout(orientation="vertical", spacing=4)
        qual_lbl = Label(text="Qualität:", font_size="12sp", color=(0.7, 0.75, 0.85, 1), size_hint_y=0.4)
        self.qual_spinner = Spinner(
            text="320k (Hohe Qualität)",
            values=["320k (Hohe Qualität)", "256k", "192k", "128k"],
            size_hint_y=0.6,
            background_normal="",
            background_color=(0.15, 0.18, 0.26, 1),
            color=(1, 1, 1, 1),
            font_size="13sp",
            bold=True
        )
        qual_box.add_widget(qual_lbl)
        qual_box.add_widget(self.qual_spinner)
        opts_card.add_widget(qual_box)

        layout.add_widget(opts_card)

        # Progress & Status Card
        status_card = StyledCard(orientation="vertical", spacing=6, size_hint_y=None, height=85, padding=[14, 10])
        self.lbl_status = Label(
            text="Bereit zum Herunterladen",
            font_size="13sp",
            color=(0.6, 0.8, 1, 1),
            size_hint_y=0.5,
            halign="left"
        )
        self.lbl_status.bind(size=self.lbl_status.setter("text_size"))
        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=0.5)
        status_card.add_widget(self.lbl_status)
        status_card.add_widget(self.progress_bar)
        layout.add_widget(status_card)

        # Action Buttons
        btn_box = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=50)
        self.btn_download = Button(
            text="Download starten",
            background_normal="",
            background_color=(0.15, 0.4, 0.95, 1),
            color=(1, 1, 1, 1),
            font_size="15sp",
            bold=True
        )
        self.btn_download.bind(on_release=self.start_download)
        btn_box.add_widget(self.btn_download)

        self.btn_cancel = Button(
            text="Abbrechen",
            size_hint_x=0.4,
            background_normal="",
            background_color=(0.3, 0.15, 0.15, 1),
            color=(0.9, 0.6, 0.6, 1),
            font_size="14sp",
            disabled=True
        )
        self.btn_cancel.bind(on_release=self.cancel_download)
        btn_box.add_widget(self.btn_cancel)

        layout.add_widget(btn_box)

        # Storage directory hint
        dl_path = get_android_download_dir()
        self.lbl_path = Label(
            text=f"Speicherort: {dl_path}",
            font_size="11sp",
            color=(0.45, 0.5, 0.6, 1),
            size_hint_y=None,
            height=28
        )
        layout.add_widget(self.lbl_path)

        layout.add_widget(BoxLayout())  # spacer
        self.add_widget(layout)

    def on_format_change(self, spinner, text):
        if text in ["MP3", "M4A", "WAV"]:
            self.qual_spinner.values = ["320k (Hohe Qualität)", "256k", "192k", "128k"]
            self.qual_spinner.text = "320k (Hohe Qualität)"
        else:
            self.qual_spinner.values = ["1080p Full HD", "720p HD", "480p", "Original"]
            self.qual_spinner.text = "1080p Full HD"

    def paste_clipboard(self, instance):
        text = Clipboard.paste()
        if text:
            self.url_input.text = text.strip()

    def update_progress(self, pct, text):
        def _update(dt):
            self.progress_bar.value = pct
            self.lbl_status.text = f"{int(pct)}% - {text}"
        Clock.schedule_once(_update)

    def finish_download(self, success, message, out_file):
        def _finish(dt):
            self.btn_download.disabled = False
            self.btn_cancel.disabled = True
            if success:
                self.progress_bar.value = 100
                self.lbl_status.text = "Fertig! Gespeichert in Downloads."
            else:
                self.lbl_status.text = f"Fehler: {message[:40]}"
        Clock.schedule_once(_finish)

    def start_download(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.lbl_status.text = "Bitte gib zuerst einen YouTube-Link ein!"
            return

        self.btn_download.disabled = True
        self.btn_cancel.disabled = False
        self.is_cancelled = False
        self.progress_bar.value = 0
        self.lbl_status.text = "Starte Download..."

        out_dir = get_android_download_dir()
        fmt = self.fmt_spinner.text
        qual = self.qual_spinner.text.split()[0]

        def _worker():
            try:
                import youtube_engine
                success, msg, out_file = youtube_engine.download_youtube_media(
                    url=url,
                    output_dir=out_dir,
                    target_format=fmt,
                    quality=qual,
                    embed_thumbnail=True,
                    progress_callback=self.update_progress,
                    is_cancelled=lambda: self.is_cancelled
                )
                self.finish_download(success, msg, out_file)
            except Exception as e:
                self.finish_download(False, str(e), None)

        self.download_thread = threading.Thread(target=_worker, daemon=True)
        self.download_thread.start()

    def cancel_download(self, instance):
        self.is_cancelled = True
        self.lbl_status.text = "Wird abgebrochen..."
        self.btn_cancel.disabled = True


class InfoScreen(Screen):
    """Screen with info about Universal Converter and supported formats."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=14, padding=[18, 16, 18, 16])

        card = StyledCard(orientation="vertical", spacing=10, padding=[16, 14])
        t = Label(text="Universal Media Converter", font_size="19sp", bold=True, size_hint_y=0.2)
        v = Label(text="Version 2.0.0 (Samsung Galaxy A55 Edition)", font_size="13sp", color=(0.4, 0.7, 1, 1), size_hint_y=0.15)
        d = Label(
            text=(
                "Unterstützte Formate:\n\n"
                "- YouTube: MP3, MP4, M4A, WAV\n"
                "- Audio/Video: MP4, MOV, MKV, MP3, WAV, FLAC, AAC\n"
                "- Bilder: JPEG, PNG, WEBP, BMP, GIF, PDF\n"
                "- Dokumente: TXT, DOCX, PDF, CSV, XLSX\n\n"
                "Alle konvertierten Dateien werden direkt im Ordner\n"
                "'Download/UniversalConverter' gespeichert und sind\n"
                "in Samsung 'Eigene Dateien' sowie der Galerie sichtbar."
            ),
            font_size="13sp",
            color=(0.85, 0.85, 0.9, 1),
            halign="left",
            size_hint_y=0.65
        )
        d.bind(size=d.setter("text_size"))
        card.add_widget(t)
        card.add_widget(v)
        card.add_widget(d)

        layout.add_widget(card)
        self.add_widget(layout)


class UniversalConverterMobileApp(App):
    """Main Kivy Application."""
    def build(self):
        Window.clearcolor = (0.07, 0.07, 0.09, 1)
        request_android_permissions()

        root = BoxLayout(orientation="vertical")

        # Top Navigation Bar
        top_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=52, padding=[12, 6], spacing=8)
        with top_bar.canvas.before:
            Color(0.09, 0.09, 0.12, 1)
            self.bar_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=lambda *_: setattr(self.bar_rect, "pos", top_bar.pos),
                     size=lambda *_: setattr(self.bar_rect, "size", top_bar.size))

        self.sm = ScreenManager(transition=FadeTransition(duration=0.15))
        self.sm.add_widget(YouTubeScreen(name="youtube"))
        self.sm.add_widget(InfoScreen(name="info"))

        btn_nav_yt = Button(
            text="YouTube",
            background_normal="",
            background_color=(0.15, 0.35, 0.85, 1),
            color=(1, 1, 1, 1),
            font_size="14sp",
            bold=True
        )
        btn_nav_yt.bind(on_release=lambda _: setattr(self.sm, "current", "youtube"))

        btn_nav_info = Button(
            text="Info & Formate",
            background_normal="",
            background_color=(0.16, 0.16, 0.22, 1),
            color=(0.8, 0.85, 0.95, 1),
            font_size="13sp"
        )
        btn_nav_info.bind(on_release=lambda _: setattr(self.sm, "current", "info"))

        top_bar.add_widget(btn_nav_yt)
        top_bar.add_widget(btn_nav_info)

        root.add_widget(top_bar)
        root.add_widget(self.sm)

        return root


if __name__ == "__main__":
    UniversalConverterMobileApp().run()
