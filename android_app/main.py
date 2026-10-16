"""
Universal Media Converter - Mobile Android App (Kivy).
Vollstaendige mobile Version mit allen Funktionen der Desktop-Version:
- YouTube Downloader (Musik & Videos)
- Lokale Audio- & Video-Konvertierung
- Bild-Konvertierung (JPEG, PNG, WEBP, BMP, GIF, ICO, PDF)
- Dokument- & Tabellen-Konvertierung (PDF, DOCX, TXT, CSV, XLSX, JSON, HTML)
- Info & Formatuebersicht

Speziell optimiert fuer das Samsung Galaxy A55 5G (Hochkant-Display, 1080x2340, ARM64).
"""

import os
import sys
import threading
from typing import List, Optional, Callable

# Kivy Konfiguration
os.environ["KIVY_NO_CONSOLELOG"] = "0"

from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, RoundedRectangle, Rectangle

import format_detector
import ffmpeg_utils
import image_utils
import document_utils
import youtube_engine
import android_native_picker


def get_android_download_dir() -> str:
    """Ermittelt den Download-Ordner fuer Android (Samsung One UI) oder Fallback."""
    try:
        from android.storage import primary_external_storage_path
        base = primary_external_storage_path()
        dl_dir = os.path.join(base, "Download", "UniversalConverter")
        os.makedirs(dl_dir, exist_ok=True)
        return dl_dir
    except Exception:
        pass

    for test_path in ["/storage/emulated/0/Download/UniversalConverter", "/sdcard/Download/UniversalConverter"]:
        try:
            os.makedirs(test_path, exist_ok=True)
            return test_path
        except Exception:
            pass

    fallback = os.path.join(os.path.expanduser("~"), "Downloads", "UniversalConverter")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def get_standard_user_folders() -> dict:
    """Gibt typische Samsung-Speicherpfade fuer Schnellzugriff zurueck."""
    base = "/storage/emulated/0"
    if not os.path.isdir(base):
        base = os.path.expanduser("~")

    return {
        "Downloads": os.path.join(base, "Download"),
        "Kamera": os.path.join(base, "DCIM"),
        "Bilder": os.path.join(base, "Pictures"),
        "Musik": os.path.join(base, "Music"),
        "Dokumente": os.path.join(base, "Documents"),
    }


def request_android_permissions():
    """Fordert notwendige Android-Berechtigungen fuer Speicher und Netzwerk an."""
    try:
        from android.permissions import request_permissions, Permission
        perms = [
            Permission.INTERNET,
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
        ]
        if hasattr(Permission, "READ_MEDIA_AUDIO"):
            perms.append(Permission.READ_MEDIA_AUDIO)
        if hasattr(Permission, "READ_MEDIA_VIDEO"):
            perms.append(Permission.READ_MEDIA_VIDEO)
        if hasattr(Permission, "READ_MEDIA_IMAGES"):
            perms.append(Permission.READ_MEDIA_IMAGES)
        request_permissions(perms)
    except Exception:
        pass


class WrappingLabel(Label):
    """
    Label, das Text automatisch umbricht und seine Höhe dynamisch
    an den Inhalt anpasst, sodass kein Text abgeschnitten wird.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.valign = "middle"
        self.bind(width=self._update_text_size)
        self.bind(texture_size=self._update_height)

    def _update_text_size(self, instance, width):
        self.text_size = (width, None)

    def _update_height(self, instance, texture_size):
        if texture_size and texture_size[1] > 0:
            self.height = texture_size[1] + dp(4)


class StyledCard(BoxLayout):
    """Moderne dunkle Karte im One-UI-Stil mit abgerundeten Ecken und flexiblem Inhalt."""
    def __init__(
        self,
        bg_color=(0.11, 0.12, 0.16, 1.0),
        border_color=(0.18, 0.20, 0.26, 1.0),
        radius_dp=16,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        self.radius_dp = radius_dp

        with self.canvas.before:
            Color(*self.border_color)
            self.border_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self.radius_dp)])
            Color(*self.bg_color)
            self.bg_rect = RoundedRectangle(
                pos=(self.pos[0] + dp(1), self.pos[1] + dp(1)),
                size=(max(0, self.size[0] - dp(2)), max(0, self.size[1] - dp(2))),
                radius=[dp(self.radius_dp - 1)]
            )
        self.bind(pos=self._update_rects, size=self._update_rects)

    def _update_rects(self, *args):
        self.border_rect.pos = self.pos
        self.border_rect.size = self.size
        self.bg_rect.pos = (self.pos[0] + dp(1), self.pos[1] + dp(1))
        self.bg_rect.size = (max(0, self.size[0] - dp(2)), max(0, self.size[1] - dp(2)))


class MobileSpinnerOption(SpinnerOption):
    """Dropdown-Eintrag mit bequemer Touch-Höhe für Smartphones."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(46)
        self.font_size = "14sp"
        self.background_normal = ""
        self.background_color = (0.16, 0.19, 0.26, 1.0)
        self.color = (0.95, 0.95, 1.0, 1.0)


class FilePickerModal(Popup):
    """Eleganter Datei-Auswahldialog mit Schnellzugriff auf Samsung-Ordner."""
    def __init__(self, on_selected: Callable[[str], None], file_filters=None, **kwargs):
        super().__init__(**kwargs)
        self.title = "Datei auf dem Gerät auswählen"
        self.title_size = "16sp"
        self.size_hint = (0.95, 0.92)
        self.auto_dismiss = False
        self.on_selected_cb = on_selected

        root_layout = BoxLayout(orientation="vertical", spacing=dp(10), padding=[dp(10), dp(10)])

        # Schnellzugriffs-Leiste
        folders = get_standard_user_folders()
        quick_bar = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint_y=None, height=dp(38))
        
        default_start_path = folders.get("Downloads", "/storage/emulated/0")
        if not os.path.isdir(default_start_path):
            default_start_path = "/storage/emulated/0" if os.path.isdir("/storage/emulated/0") else os.path.expanduser("~")

        for label, path in folders.items():
            if os.path.isdir(path):
                btn = Button(
                    text=label,
                    font_size="11sp",
                    background_normal="",
                    background_color=(0.20, 0.24, 0.32, 1),
                    color=(0.9, 0.95, 1, 1)
                )
                btn.bind(on_release=lambda _, p=path: self.set_folder(p))
                quick_bar.add_widget(btn)

        root_layout.add_widget(quick_bar)

        # FileChooser
        self.file_chooser = FileChooserListView(
            path=default_start_path,
            filters=file_filters or [],
            dirselect=False
        )
        root_layout.add_widget(self.file_chooser)

        # Ausgewählter Pfad
        self.lbl_chosen = Label(
            text=f"Ordner: {default_start_path}",
            size_hint_y=None,
            height=dp(28),
            font_size="11sp",
            color=(0.7, 0.75, 0.85, 1)
        )
        self.file_chooser.bind(selection=self.on_selection_change)
        root_layout.add_widget(self.lbl_chosen)

        # Aktions-Buttons
        btn_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(48))
        btn_cancel = Button(
            text="Abbrechen",
            background_normal="",
            background_color=(0.28, 0.14, 0.16, 1),
            color=(0.95, 0.7, 0.7, 1),
            font_size="14sp"
        )
        btn_cancel.bind(on_release=self.dismiss)

        btn_select = Button(
            text="Auswählen",
            background_normal="",
            background_color=(0.17, 0.42, 0.95, 1),
            color=(1, 1, 1, 1),
            font_size="15sp",
            bold=True
        )
        btn_select.bind(on_release=self.confirm_selection)

        btn_row.add_widget(btn_cancel)
        btn_row.add_widget(btn_select)
        root_layout.add_widget(btn_row)

        self.content = root_layout

    def set_folder(self, path):
        if os.path.isdir(path):
            self.file_chooser.path = path
            self.lbl_chosen.text = f"Ordner: {path}"

    def on_selection_change(self, chooser, selection):
        if selection:
            self.lbl_chosen.text = f"Ausgewählt: {os.path.basename(selection[0])}"

    def confirm_selection(self, instance):
        if self.file_chooser.selection:
            selected_path = self.file_chooser.selection[0]
            self.dismiss()
            if self.on_selected_cb:
                self.on_selected_cb(selected_path)


class YouTubeScreen(Screen):
    """Hauptbildschirm für YouTube Video- und Audio-Downloads."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.download_thread = None
        self.is_cancelled = False
        self.last_downloaded_file = None

        scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(4),
            bar_color=(0.3, 0.4, 0.6, 0.7),
            bar_inactive_color=(0.2, 0.25, 0.35, 0.3)
        )

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=[dp(16), dp(16), dp(16), dp(28)],
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter("height"))

        # 1. Header Karte
        header_card = StyledCard(
            orientation="vertical",
            spacing=dp(6),
            padding=[dp(16), dp(16), dp(16), dp(16)],
            size_hint_y=None
        )
        header_card.bind(minimum_height=header_card.setter("height"))

        lbl_app_title = WrappingLabel(
            text="YouTube Downloader",
            font_size="20sp",
            bold=True,
            color=(1, 1, 1, 1),
            halign="left"
        )
        lbl_app_sub = WrappingLabel(
            text="Musik und Videos direkt auf Ihr Samsung Galaxy A55 5G herunterladen.",
            font_size="13sp",
            color=(0.4, 0.7, 1, 1),
            halign="left"
        )
        header_card.add_widget(lbl_app_title)
        header_card.add_widget(lbl_app_sub)
        content.add_widget(header_card)

        # 2. Link Eingabe Karte
        input_card = StyledCard(
            orientation="vertical",
            spacing=dp(12),
            padding=[dp(16), dp(16), dp(16), dp(16)],
            size_hint_y=None
        )
        input_card.bind(minimum_height=input_card.setter("height"))

        lbl_input_title = WrappingLabel(
            text="YouTube Link eingeben:",
            font_size="14sp",
            bold=True,
            color=(0.85, 0.9, 0.95, 1),
            halign="left"
        )
        input_card.add_widget(lbl_input_title)

        self.url_input = TextInput(
            hint_text="https://www.youtube.com/watch?v=...",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            background_normal="",
            background_color=(0.07, 0.08, 0.11, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.3, 0.6, 1, 1),
            font_size="14sp",
            padding=[dp(12), dp(14), dp(12), dp(14)]
        )
        input_card.add_widget(self.url_input)

        paste_btn = Button(
            text="Aus Zwischenablage einfügen",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.18, 0.22, 0.32, 1),
            color=(0.9, 0.95, 1, 1),
            font_size="14sp",
            bold=True
        )
        paste_btn.bind(on_release=self.paste_clipboard)
        input_card.add_widget(paste_btn)
        content.add_widget(input_card)

        # 3. Format & Qualität Karte
        opts_card = StyledCard(
            orientation="vertical",
            spacing=dp(12),
            padding=[dp(16), dp(16), dp(16), dp(16)],
            size_hint_y=None
        )
        opts_card.bind(minimum_height=opts_card.setter("height"))

        lbl_opts_title = WrappingLabel(
            text="Download-Optionen:",
            font_size="14sp",
            bold=True,
            color=(0.85, 0.9, 0.95, 1),
            halign="left"
        )
        opts_card.add_widget(lbl_opts_title)

        grid_opts = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        grid_opts.bind(minimum_height=grid_opts.setter("height"))

        # Spalte 1: Format
        col_fmt = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        col_fmt.bind(minimum_height=col_fmt.setter("height"))
        lbl_fmt = WrappingLabel(text="Ziel-Format:", font_size="12sp", color=(0.65, 0.7, 0.8, 1))
        self.fmt_spinner = Spinner(
            text="MP3",
            values=["MP3", "M4A", "MP4", "WAV"],
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.15, 0.18, 0.26, 1),
            color=(1, 1, 1, 1),
            font_size="14sp",
            bold=True,
            option_cls=MobileSpinnerOption
        )
        self.fmt_spinner.bind(text=self.on_format_change)
        col_fmt.add_widget(lbl_fmt)
        col_fmt.add_widget(self.fmt_spinner)
        grid_opts.add_widget(col_fmt)

        # Spalte 2: Qualität
        col_qual = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        col_qual.bind(minimum_height=col_qual.setter("height"))
        lbl_qual = WrappingLabel(text="Qualität:", font_size="12sp", color=(0.65, 0.7, 0.8, 1))
        self.qual_spinner = Spinner(
            text="320k (Beste)",
            values=["320k (Beste)", "256k", "192k", "128k"],
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.15, 0.18, 0.26, 1),
            color=(1, 1, 1, 1),
            font_size="14sp",
            bold=True,
            option_cls=MobileSpinnerOption
        )
        col_qual.add_widget(lbl_qual)
        col_qual.add_widget(self.qual_spinner)
        grid_opts.add_widget(col_qual)

        opts_card.add_widget(grid_opts)
        content.add_widget(opts_card)

        # 4. Status & Fortschritt Karte
        status_card = StyledCard(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(16), dp(16), dp(16), dp(16)],
            size_hint_y=None
        )
        status_card.bind(minimum_height=status_card.setter("height"))

        self.lbl_status = WrappingLabel(
            text="Bereit zum Herunterladen",
            font_size="14sp",
            bold=True,
            color=(0.4, 0.75, 1, 1),
            halign="left"
        )
        status_card.add_widget(self.lbl_status)

        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(12)
        )
        status_card.add_widget(self.progress_bar)

        self.lbl_details = WrappingLabel(
            text="Tippen Sie auf 'Download starten', um den Vorgang zu beginnen.",
            font_size="12sp",
            color=(0.6, 0.65, 0.75, 1),
            halign="left"
        )
        status_card.add_widget(self.lbl_details)
        content.add_widget(status_card)

        # 5. Aktions-Buttons
        btn_box = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None
        )
        btn_box.bind(minimum_height=btn_box.setter("height"))

        self.btn_download = Button(
            text="Download starten",
            size_hint_y=None,
            height=dp(56),
            background_normal="",
            background_color=(0.17, 0.42, 0.95, 1),
            color=(1, 1, 1, 1),
            font_size="16sp",
            bold=True
        )
        self.btn_download.bind(on_release=self.start_download)
        btn_box.add_widget(self.btn_download)

        self.btn_cancel = Button(
            text="Download abbrechen",
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_color=(0.28, 0.14, 0.16, 1),
            color=(0.95, 0.65, 0.65, 1),
            font_size="14sp",
            disabled=True
        )
        self.btn_cancel.bind(on_release=self.cancel_download)
        btn_box.add_widget(self.btn_cancel)

        self.btn_save_as = Button(
            text="In individuellem Ordner speichern...",
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_color=(0.14, 0.28, 0.22, 1),
            color=(0.65, 0.95, 0.75, 1),
            font_size="14sp",
            bold=True,
            disabled=True
        )
        self.btn_save_as.bind(on_release=self.prompt_save_as)
        btn_box.add_widget(self.btn_save_as)
        content.add_widget(btn_box)

        # 6. Speicherort Info Karte
        dl_path = get_android_download_dir()
        path_card = StyledCard(
            orientation="vertical",
            spacing=dp(4),
            padding=[dp(16), dp(14), dp(16), dp(14)],
            bg_color=(0.08, 0.09, 0.12, 1.0),
            border_color=(0.14, 0.16, 0.22, 1.0),
            size_hint_y=None
        )
        path_card.bind(minimum_height=path_card.setter("height"))

        lbl_path_title = WrappingLabel(
            text="Speicherort auf dem Gerät:",
            font_size="12sp",
            bold=True,
            color=(0.55, 0.6, 0.7, 1)
        )
        self.lbl_path = WrappingLabel(
            text=f"{dl_path}\n(In Samsung 'Eigene Dateien' -> Downloads -> UniversalConverter)",
            font_size="11sp",
            color=(0.4, 0.7, 0.9, 1)
        )
        path_card.add_widget(lbl_path_title)
        path_card.add_widget(self.lbl_path)
        content.add_widget(path_card)

        scroll.add_widget(content)
        self.add_widget(scroll)

    def on_format_change(self, spinner, text):
        if text in ["MP3", "M4A", "WAV"]:
            self.qual_spinner.values = ["320k (Beste)", "256k", "192k", "128k"]
            self.qual_spinner.text = "320k (Beste)"
        else:
            self.qual_spinner.values = ["1080p Full HD", "720p HD", "480p"]
            self.qual_spinner.text = "720p HD"

    def paste_clipboard(self, instance):
        text = Clipboard.paste()
        if text:
            self.url_input.text = text.strip()

    def update_progress(self, pct, text):
        def _update(dt):
            self.progress_bar.value = pct
            self.lbl_status.text = f"{int(pct)}% - Lädt herunter..."
            self.lbl_details.text = text
        Clock.schedule_once(_update)

    def finish_download(self, success, message, out_file):
        def _finish(dt):
            self.btn_download.disabled = False
            self.btn_cancel.disabled = True
            if success:
                self.progress_bar.value = 100
                self.last_downloaded_file = out_file
                self.btn_save_as.disabled = False
                self.lbl_status.text = "Download erfolgreich abgeschlossen!"
                self.lbl_details.text = (
                    f"Datei gespeichert in:\n{out_file or get_android_download_dir()}\n"
                    "Sichtbar in der Samsung Galerie und 'Eigene Dateien'."
                )
                if out_file and os.path.isfile(out_file):
                    android_native_picker.save_file_native(
                        source_file_path=out_file,
                        callback=self.on_save_as_completed
                    )
            else:
                self.lbl_status.text = "Download fehlgeschlagen"
                self.lbl_details.text = f"Fehlermeldung: {message}"
        Clock.schedule_once(_finish)

    def prompt_save_as(self, instance):
        if self.last_downloaded_file and os.path.isfile(self.last_downloaded_file):
            android_native_picker.save_file_native(
                source_file_path=self.last_downloaded_file,
                callback=self.on_save_as_completed
            )

    def on_save_as_completed(self, success, msg):
        if success:
            self.lbl_status.text = "Datei erfolgreich exportiert!"
            self.lbl_details.text = msg
        else:
            if "abgebrochen" not in msg.lower():
                self.lbl_details.text = msg

    def start_download(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.lbl_status.text = "Kein Link eingegeben"
            self.lbl_details.text = "Bitte fügen Sie zuerst einen YouTube-Link in das Textfeld ein."
            return

        self.btn_download.disabled = True
        self.btn_cancel.disabled = False
        self.is_cancelled = False
        self.progress_bar.value = 0
        self.lbl_status.text = "Verbindung wird aufgebaut..."
        self.lbl_details.text = "Analysiere Video-Informationen..."

        out_dir = get_android_download_dir()
        fmt = self.fmt_spinner.text
        qual = self.qual_spinner.text.split()[0]

        def _worker():
            try:
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
        self.lbl_details.text = "Download-Vorgang wird angehalten..."
        self.btn_cancel.disabled = True


class AudioVideoScreen(Screen):
    """Bildschirm für lokale Audio- und Video-Konvertierung."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_file = None
        self.conv_thread = None
        self.is_cancelled = False
        self.last_converted_file = None

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=dp(4))
        content = BoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=[dp(16), dp(16), dp(16), dp(28)],
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter("height"))

        # Header
        card_header = StyledCard(orientation="vertical", spacing=dp(6), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_header.bind(minimum_height=card_header.setter("height"))
        card_header.add_widget(WrappingLabel(text="Audio & Video Konverter", font_size="20sp", bold=True, color=(1, 1, 1, 1)))
        card_header.add_widget(WrappingLabel(text="Lokale Musik- und Videodateien umwandeln (z.B. Video zu MP3, WAV zu FLAC, MP4 zu MOV).", font_size="13sp", color=(0.4, 0.7, 1, 1)))
        content.add_widget(card_header)

        # Dateiauswahl
        card_file = StyledCard(orientation="vertical", spacing=dp(12), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_file.bind(minimum_height=card_file.setter("height"))
        card_file.add_widget(WrappingLabel(text="Mediendatei auswählen:", font_size="14sp", bold=True, color=(0.85, 0.9, 0.95, 1)))

        self.lbl_file_info = WrappingLabel(text="Noch keine Datei gewählt", font_size="13sp", color=(0.6, 0.65, 0.75, 1))
        card_file.add_widget(self.lbl_file_info)

        btn_browse = Button(
            text="Datei auf Smartphone wählen...",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.18, 0.22, 0.32, 1),
            color=(0.9, 0.95, 1, 1),
            font_size="14sp",
            bold=True
        )
        btn_browse.bind(on_release=self.open_file_picker)
        card_file.add_widget(btn_browse)
        content.add_widget(card_file)

        # Ziel-Optionen
        card_opts = StyledCard(orientation="vertical", spacing=dp(12), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_opts.bind(minimum_height=card_opts.setter("height"))
        card_opts.add_widget(WrappingLabel(text="Ziel-Einstellungen:", font_size="14sp", bold=True, color=(0.85, 0.9, 0.95, 1)))

        grid = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        col1 = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        col1.bind(minimum_height=col1.setter("height"))
        col1.add_widget(WrappingLabel(text="Format:", font_size="12sp", color=(0.65, 0.7, 0.8, 1)))
        self.fmt_spinner = Spinner(
            text="MP3",
            values=["MP3", "WAV", "FLAC", "AAC", "M4A", "OGG", "OPUS", "MP4", "MOV", "MKV", "GIF"],
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.15, 0.18, 0.26, 1),
            color=(1, 1, 1, 1),
            font_size="14sp",
            bold=True,
            option_cls=MobileSpinnerOption
        )
        self.fmt_spinner.bind(text=self.on_format_change)
        col1.add_widget(self.fmt_spinner)
        grid.add_widget(col1)

        col2 = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        col2.bind(minimum_height=col2.setter("height"))
        col2.add_widget(WrappingLabel(text="Qualität / Auflösung:", font_size="12sp", color=(0.65, 0.7, 0.8, 1)))
        self.qual_spinner = Spinner(
            text="320k (Hohe Qualität)",
            values=["320k (Hohe Qualität)", "256k", "192k", "128k"],
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.15, 0.18, 0.26, 1),
            color=(1, 1, 1, 1),
            font_size="14sp",
            bold=True,
            option_cls=MobileSpinnerOption
        )
        col2.add_widget(self.qual_spinner)
        grid.add_widget(col2)

        card_opts.add_widget(grid)
        content.add_widget(card_opts)

        # Status & Fortschritt
        card_status = StyledCard(orientation="vertical", spacing=dp(10), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_status.bind(minimum_height=card_status.setter("height"))
        self.lbl_status = WrappingLabel(text="Bereit", font_size="14sp", bold=True, color=(0.4, 0.75, 1, 1))
        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(12))
        self.lbl_details = WrappingLabel(text="Wählen Sie eine Audio- oder Videodatei aus.", font_size="12sp", color=(0.6, 0.65, 0.75, 1))
        card_status.add_widget(self.lbl_status)
        card_status.add_widget(self.progress_bar)
        card_status.add_widget(self.lbl_details)
        content.add_widget(card_status)

        # Buttons
        btn_box = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        btn_box.bind(minimum_height=btn_box.setter("height"))

        self.btn_start = Button(
            text="Konvertierung starten",
            size_hint_y=None,
            height=dp(56),
            background_normal="",
            background_color=(0.17, 0.42, 0.95, 1),
            color=(1, 1, 1, 1),
            font_size="16sp",
            bold=True
        )
        self.btn_start.bind(on_release=self.start_conversion)
        btn_box.add_widget(self.btn_start)

        self.btn_cancel = Button(
            text="Abbrechen",
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_color=(0.28, 0.14, 0.16, 1),
            color=(0.95, 0.65, 0.65, 1),
            font_size="14sp",
            disabled=True
        )
        self.btn_cancel.bind(on_release=self.cancel_conversion)
        btn_box.add_widget(self.btn_cancel)

        self.btn_save_as = Button(
            text="In individuellem Ordner speichern...",
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_color=(0.14, 0.28, 0.22, 1),
            color=(0.65, 0.95, 0.75, 1),
            font_size="14sp",
            bold=True,
            disabled=True
        )
        self.btn_save_as.bind(on_release=self.prompt_save_as)
        btn_box.add_widget(self.btn_save_as)
        content.add_widget(btn_box)

        scroll.add_widget(content)
        self.add_widget(scroll)

    def open_file_picker(self, _):
        launched = android_native_picker.open_file_native(
            callback=self.on_file_selected,
            mime_type="*/*"
        )
        if not launched:
            picker = FilePickerModal(
                on_selected=self.on_file_selected,
                file_filters=[
                    "*.mp4", "*.mov", "*.mkv", "*.webm", "*.avi", "*.flv", "*.m4v",
                    "*.mp3", "*.wav", "*.flac", "*.aac", "*.m4a", "*.ogg", "*.opus", "*.aiff"
                ]
            )
            picker.open()

    def on_file_selected(self, path):
        self.selected_file = path
        size_mb = os.path.getsize(path) / (1024 * 1024) if os.path.exists(path) else 0
        name = os.path.basename(path)
        self.lbl_file_info.text = f"{name} ({size_mb:.1f} MB)"

        _, allowed, default_fmt, _ = format_detector.detect_file_info(path)
        if allowed:
            self.fmt_spinner.values = allowed
            self.fmt_spinner.text = default_fmt
        self.lbl_details.text = "Datei geladen. Wählen Sie Zielformat und Qualität."

    def on_format_change(self, spinner, text):
        presets = format_detector.get_quality_presets(text)
        if presets:
            self.qual_spinner.values = presets
            self.qual_spinner.text = presets[0]

    def update_progress(self, pct, text):
        def _update(dt):
            self.progress_bar.value = pct
            self.lbl_status.text = f"{int(pct)}% - Wird konvertiert..."
            self.lbl_details.text = text
        Clock.schedule_once(_update)

    def finish_conversion(self, success, message, out_file):
        def _finish(dt):
            self.btn_start.disabled = False
            self.btn_cancel.disabled = True
            if success:
                self.progress_bar.value = 100
                self.last_converted_file = out_file
                self.btn_save_as.disabled = False
                self.lbl_status.text = "Konvertierung erfolgreich!"
                self.lbl_details.text = f"Gespeichert in:\n{out_file}"
                if out_file and os.path.isfile(out_file):
                    android_native_picker.save_file_native(
                        source_file_path=out_file,
                        callback=self.on_save_as_completed
                    )
            else:
                self.lbl_status.text = "Fehler bei der Konvertierung"
                self.lbl_details.text = message
        Clock.schedule_once(_finish)

    def prompt_save_as(self, instance):
        if self.last_converted_file and os.path.isfile(self.last_converted_file):
            android_native_picker.save_file_native(
                source_file_path=self.last_converted_file,
                callback=self.on_save_as_completed
            )

    def on_save_as_completed(self, success, msg):
        if success:
            self.lbl_status.text = "Datei erfolgreich exportiert!"
            self.lbl_details.text = msg
        else:
            if "abgebrochen" not in msg.lower():
                self.lbl_details.text = msg

    def start_conversion(self, _):
        if not self.selected_file or not os.path.isfile(self.selected_file):
            self.lbl_status.text = "Keine Datei gewählt"
            self.lbl_details.text = "Bitte wählen Sie zuerst eine Video- oder Audiodatei aus."
            return

        self.btn_start.disabled = True
        self.btn_cancel.disabled = False
        self.is_cancelled = False
        self.progress_bar.value = 0
        self.lbl_status.text = "Konvertierung startet..."

        out_dir = get_android_download_dir()
        base_name = os.path.splitext(os.path.basename(self.selected_file))[0]
        target_fmt = self.fmt_spinner.text
        ext = target_fmt.lower()
        out_file = os.path.join(out_dir, f"{base_name}_konvertiert.{ext}")
        quality = self.qual_spinner.text.split()[0]

        def _worker():
            try:
                success, msg = ffmpeg_utils.convert_file(
                    input_file=self.selected_file,
                    output_file=out_file,
                    target_format=target_fmt,
                    quality=quality,
                    progress_callback=self.update_progress,
                    is_cancelled=lambda: self.is_cancelled
                )
                self.finish_conversion(success, msg, out_file)
            except Exception as e:
                self.finish_conversion(False, str(e), None)

        self.conv_thread = threading.Thread(target=_worker, daemon=True)
        self.conv_thread.start()

    def cancel_conversion(self, _):
        self.is_cancelled = True
        self.lbl_status.text = "Abgebrochen"
        self.btn_cancel.disabled = True


class ImageScreen(Screen):
    """Bildschirm für Bildkonvertierung."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_file = None
        self.conv_thread = None
        self.last_converted_file = None

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=dp(4))
        content = BoxLayout(orientation="vertical", spacing=dp(16), padding=[dp(16), dp(16), dp(16), dp(28)], size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        # Header
        card_header = StyledCard(orientation="vertical", spacing=dp(6), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_header.bind(minimum_height=card_header.setter("height"))
        card_header.add_widget(WrappingLabel(text="Bild-Konverter", font_size="20sp", bold=True, color=(1, 1, 1, 1)))
        card_header.add_widget(WrappingLabel(text="Bilder umwandeln zwischen JPEG, PNG, WEBP, BMP, GIF, ICO und PDF.", font_size="13sp", color=(0.4, 0.7, 1, 1)))
        content.add_widget(card_header)

        # Auswahl
        card_file = StyledCard(orientation="vertical", spacing=dp(12), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_file.bind(minimum_height=card_file.setter("height"))
        card_file.add_widget(WrappingLabel(text="Bilddatei auswählen:", font_size="14sp", bold=True, color=(0.85, 0.9, 0.95, 1)))

        self.lbl_file_info = WrappingLabel(text="Kein Bild ausgewählt", font_size="13sp", color=(0.6, 0.65, 0.75, 1))
        card_file.add_widget(self.lbl_file_info)

        btn_browse = Button(
            text="Bild aus Galerie / Speicher wählen...",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.18, 0.22, 0.32, 1),
            color=(0.9, 0.95, 1, 1),
            font_size="14sp",
            bold=True
        )
        btn_browse.bind(on_release=self.open_file_picker)
        card_file.add_widget(btn_browse)
        content.add_widget(card_file)

        # Optionen
        card_opts = StyledCard(orientation="vertical", spacing=dp(12), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_opts.bind(minimum_height=card_opts.setter("height"))
        card_opts.add_widget(WrappingLabel(text="Bild-Optionen:", font_size="14sp", bold=True, color=(0.85, 0.9, 0.95, 1)))

        grid = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        col1 = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        col1.bind(minimum_height=col1.setter("height"))
        col1.add_widget(WrappingLabel(text="Ziel-Format:", font_size="12sp", color=(0.65, 0.7, 0.8, 1)))
        self.fmt_spinner = Spinner(
            text="PNG",
            values=["PNG", "JPEG", "WEBP", "BMP", "GIF", "ICO", "PDF", "TIFF"],
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.15, 0.18, 0.26, 1),
            color=(1, 1, 1, 1),
            font_size="14sp",
            bold=True,
            option_cls=MobileSpinnerOption
        )
        col1.add_widget(self.fmt_spinner)
        grid.add_widget(col1)

        col2 = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        col2.bind(minimum_height=col2.setter("height"))
        col2.add_widget(WrappingLabel(text="Qualität:", font_size="12sp", color=(0.65, 0.7, 0.8, 1)))
        self.qual_spinner = Spinner(
            text="Sehr hoch (95%)",
            values=["Maximum (100%)", "Sehr hoch (95%)", "Hoch (85%)", "Mittel (75%)", "Lossless (Verlustfrei)"],
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.15, 0.18, 0.26, 1),
            color=(1, 1, 1, 1),
            font_size="14sp",
            bold=True,
            option_cls=MobileSpinnerOption
        )
        col2.add_widget(self.qual_spinner)
        grid.add_widget(col2)

        card_opts.add_widget(grid)
        content.add_widget(card_opts)

        # Status
        card_status = StyledCard(orientation="vertical", spacing=dp(10), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_status.bind(minimum_height=card_status.setter("height"))
        self.lbl_status = WrappingLabel(text="Bereit", font_size="14sp", bold=True, color=(0.4, 0.75, 1, 1))
        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(12))
        self.lbl_details = WrappingLabel(text="Wählen Sie ein Bild aus.", font_size="12sp", color=(0.6, 0.65, 0.75, 1))
        card_status.add_widget(self.lbl_status)
        card_status.add_widget(self.progress_bar)
        card_status.add_widget(self.lbl_details)
        content.add_widget(card_status)

        # Start Button
        self.btn_convert = Button(
            text="Bild konvertieren",
            size_hint_y=None,
            height=dp(56),
            background_normal="",
            background_color=(0.17, 0.42, 0.95, 1),
            color=(1, 1, 1, 1),
            font_size="16sp",
            bold=True
        )
        self.btn_convert.bind(on_release=self.start_conversion)
        content.add_widget(self.btn_convert)

        self.btn_save_as = Button(
            text="In individuellem Ordner speichern...",
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_color=(0.14, 0.28, 0.22, 1),
            color=(0.65, 0.95, 0.75, 1),
            font_size="14sp",
            bold=True,
            disabled=True
        )
        self.btn_save_as.bind(on_release=self.prompt_save_as)
        content.add_widget(self.btn_save_as)

        scroll.add_widget(content)
        self.add_widget(scroll)

    def open_file_picker(self, _):
        launched = android_native_picker.open_file_native(
            callback=self.on_file_selected,
            mime_type="image/*"
        )
        if not launched:
            picker = FilePickerModal(
                on_selected=self.on_file_selected,
                file_filters=["*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp", "*.gif", "*.tiff", "*.ico", "*.heic"]
            )
            picker.open()

    def on_file_selected(self, path):
        self.selected_file = path
        size_kb = os.path.getsize(path) / 1024 if os.path.exists(path) else 0
        name = os.path.basename(path)
        self.lbl_file_info.text = f"{name} ({size_kb:.0f} KB)"

        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext in ["jpg", "jpeg"]:
            self.fmt_spinner.text = "PNG"
        elif ext == "png":
            self.fmt_spinner.text = "JPEG"
        self.lbl_details.text = "Bild geladen. Zielformat wählen und starten."

    def update_progress(self, pct, text):
        def _update(dt):
            self.progress_bar.value = pct
            self.lbl_status.text = f"{int(pct)}% - Verarbeite Bild..."
            self.lbl_details.text = text
        Clock.schedule_once(_update)

    def finish_conversion(self, success, message, out_file):
        def _finish(dt):
            self.btn_convert.disabled = False
            if success:
                self.progress_bar.value = 100
                self.last_converted_file = out_file
                self.btn_save_as.disabled = False
                self.lbl_status.text = "Bild erfolgreich konvertiert!"
                self.lbl_details.text = f"Gespeichert in:\n{out_file}\nIn Galerie und 'Eigene Dateien' sichtbar."
                if out_file and os.path.isfile(out_file):
                    android_native_picker.save_file_native(
                        source_file_path=out_file,
                        callback=self.on_save_as_completed
                    )
            else:
                self.lbl_status.text = "Fehler bei Bildkonvertierung"
                self.lbl_details.text = message
        Clock.schedule_once(_finish)

    def prompt_save_as(self, instance):
        if self.last_converted_file and os.path.isfile(self.last_converted_file):
            android_native_picker.save_file_native(
                source_file_path=self.last_converted_file,
                callback=self.on_save_as_completed
            )

    def on_save_as_completed(self, success, msg):
        if success:
            self.lbl_status.text = "Bild erfolgreich exportiert!"
            self.lbl_details.text = msg
        else:
            if "abgebrochen" not in msg.lower():
                self.lbl_details.text = msg

    def start_conversion(self, _):
        if not self.selected_file or not os.path.isfile(self.selected_file):
            self.lbl_status.text = "Kein Bild gewählt"
            self.lbl_details.text = "Bitte wählen Sie zuerst eine Bilddatei aus."
            return

        self.btn_convert.disabled = True
        self.progress_bar.value = 10
        self.lbl_status.text = "Konvertiere Bild..."

        out_dir = get_android_download_dir()
        base_name = os.path.splitext(os.path.basename(self.selected_file))[0]
        target_fmt = self.fmt_spinner.text
        ext = target_fmt.lower()
        if ext == "jpeg":
            ext = "jpg"
        out_file = os.path.join(out_dir, f"{base_name}_konvertiert.{ext}")
        quality = self.qual_spinner.text

        def _worker():
            try:
                success, msg = image_utils.convert_image(
                    input_file=self.selected_file,
                    output_file=out_file,
                    target_format=target_fmt,
                    quality_str=quality,
                    progress_callback=self.update_progress
                )
                self.finish_conversion(success, msg, out_file)
            except Exception as e:
                self.finish_conversion(False, str(e), None)

        self.conv_thread = threading.Thread(target=_worker, daemon=True)
        self.conv_thread.start()


class DocumentScreen(Screen):
    """Bildschirm für Dokument- und Tabellen-Konvertierung."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_file = None
        self.conv_thread = None
        self.last_converted_file = None

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=dp(4))
        content = BoxLayout(orientation="vertical", spacing=dp(16), padding=[dp(16), dp(16), dp(16), dp(28)], size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        # Header
        card_header = StyledCard(orientation="vertical", spacing=dp(6), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_header.bind(minimum_height=card_header.setter("height"))
        card_header.add_widget(WrappingLabel(text="Dokumente & Tabellen", font_size="20sp", bold=True, color=(1, 1, 1, 1)))
        card_header.add_widget(WrappingLabel(text="Konvertierung von Tabellen (CSV, XLSX, JSON, HTML) und Textdokumenten (PDF, DOCX, TXT).", font_size="13sp", color=(0.4, 0.7, 1, 1)))
        content.add_widget(card_header)

        # Datei
        card_file = StyledCard(orientation="vertical", spacing=dp(12), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_file.bind(minimum_height=card_file.setter("height"))
        card_file.add_widget(WrappingLabel(text="Dokument oder Tabelle wählen:", font_size="14sp", bold=True, color=(0.85, 0.9, 0.95, 1)))

        self.lbl_file_info = WrappingLabel(text="Keine Datei ausgewählt", font_size="13sp", color=(0.6, 0.65, 0.75, 1))
        card_file.add_widget(self.lbl_file_info)

        btn_browse = Button(
            text="Dokument / Tabelle suchen...",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.18, 0.22, 0.32, 1),
            color=(0.9, 0.95, 1, 1),
            font_size="14sp",
            bold=True
        )
        btn_browse.bind(on_release=self.open_file_picker)
        card_file.add_widget(btn_browse)
        content.add_widget(card_file)

        # Optionen
        card_opts = StyledCard(orientation="vertical", spacing=dp(12), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_opts.bind(minimum_height=card_opts.setter("height"))
        card_opts.add_widget(WrappingLabel(text="Ziel-Format:", font_size="14sp", bold=True, color=(0.85, 0.9, 0.95, 1)))

        self.fmt_spinner = Spinner(
            text="CSV",
            values=["CSV", "XLSX", "JSON", "HTML", "PDF", "TXT", "DOCX"],
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.15, 0.18, 0.26, 1),
            color=(1, 1, 1, 1),
            font_size="14sp",
            bold=True,
            option_cls=MobileSpinnerOption
        )
        card_opts.add_widget(self.fmt_spinner)
        content.add_widget(card_opts)

        # Status
        card_status = StyledCard(orientation="vertical", spacing=dp(10), padding=[dp(16), dp(16), dp(16), dp(16)], size_hint_y=None)
        card_status.bind(minimum_height=card_status.setter("height"))
        self.lbl_status = WrappingLabel(text="Bereit", font_size="14sp", bold=True, color=(0.4, 0.75, 1, 1))
        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(12))
        self.lbl_details = WrappingLabel(text="Wählen Sie eine Datei aus.", font_size="12sp", color=(0.6, 0.65, 0.75, 1))
        card_status.add_widget(self.lbl_status)
        card_status.add_widget(self.progress_bar)
        card_status.add_widget(self.lbl_details)
        content.add_widget(card_status)

        # Start Button
        self.btn_convert = Button(
            text="Dokument konvertieren",
            size_hint_y=None,
            height=dp(56),
            background_normal="",
            background_color=(0.17, 0.42, 0.95, 1),
            color=(1, 1, 1, 1),
            font_size="16sp",
            bold=True
        )
        self.btn_convert.bind(on_release=self.start_conversion)
        content.add_widget(self.btn_convert)

        self.btn_save_as = Button(
            text="In individuellem Ordner speichern...",
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_color=(0.14, 0.28, 0.22, 1),
            color=(0.65, 0.95, 0.75, 1),
            font_size="14sp",
            bold=True,
            disabled=True
        )
        self.btn_save_as.bind(on_release=self.prompt_save_as)
        content.add_widget(self.btn_save_as)

        scroll.add_widget(content)
        self.add_widget(scroll)

    def open_file_picker(self, _):
        launched = android_native_picker.open_file_native(
            callback=self.on_file_selected,
            mime_type="*/*"
        )
        if not launched:
            picker = FilePickerModal(
                on_selected=self.on_file_selected,
                file_filters=["*.csv", "*.xlsx", "*.xls", "*.json", "*.html", "*.pdf", "*.docx", "*.txt", "*.tsv"]
            )
            picker.open()

    def on_file_selected(self, path):
        self.selected_file = path
        size_kb = os.path.getsize(path) / 1024 if os.path.exists(path) else 0
        name = os.path.basename(path)
        self.lbl_file_info.text = f"{name} ({size_kb:.0f} KB)"

        targets = document_utils.get_available_targets(path)
        if targets:
            self.fmt_spinner.values = targets
            self.fmt_spinner.text = targets[0]
        self.lbl_details.text = "Datei geladen. Zielformat wählen und starten."

    def update_progress(self, pct, text):
        def _update(dt):
            self.progress_bar.value = pct
            self.lbl_status.text = f"{int(pct)}% - Verarbeite Dokument..."
            self.lbl_details.text = text
        Clock.schedule_once(_update)

    def finish_conversion(self, success, message, out_file):
        def _finish(dt):
            self.btn_convert.disabled = False
            if success:
                self.progress_bar.value = 100
                self.last_converted_file = out_file
                self.btn_save_as.disabled = False
                self.lbl_status.text = "Konvertierung erfolgreich abgeschlossen!"
                self.lbl_details.text = f"Gespeichert in:\n{out_file}"
                if out_file and os.path.isfile(out_file):
                    android_native_picker.save_file_native(
                        source_file_path=out_file,
                        callback=self.on_save_as_completed
                    )
            else:
                self.lbl_status.text = "Konvertierung fehlgeschlagen"
                self.lbl_details.text = message
        Clock.schedule_once(_finish)

    def prompt_save_as(self, instance):
        if self.last_converted_file and os.path.isfile(self.last_converted_file):
            android_native_picker.save_file_native(
                source_file_path=self.last_converted_file,
                callback=self.on_save_as_completed
            )

    def on_save_as_completed(self, success, msg):
        if success:
            self.lbl_status.text = "Dokument erfolgreich exportiert!"
            self.lbl_details.text = msg
        else:
            if "abgebrochen" not in msg.lower():
                self.lbl_details.text = msg

    def start_conversion(self, _):
        if not self.selected_file or not os.path.isfile(self.selected_file):
            self.lbl_status.text = "Keine Datei gewählt"
            self.lbl_details.text = "Bitte wählen Sie zuerst eine Dokument- oder Tabellendatei aus."
            return

        self.btn_convert.disabled = True
        self.progress_bar.value = 10
        self.lbl_status.text = "Konvertiere Dokument..."

        out_dir = get_android_download_dir()
        base_name = os.path.splitext(os.path.basename(self.selected_file))[0]
        target_fmt = self.fmt_spinner.text
        ext = target_fmt.lower()
        out_file = os.path.join(out_dir, f"{base_name}_konvertiert.{ext}")

        def _worker():
            try:
                success, msg = document_utils.convert_document(
                    input_file=self.selected_file,
                    output_file=out_file,
                    target_format=target_fmt,
                    progress_callback=self.update_progress
                )
                self.finish_conversion(success, msg, out_file)
            except Exception as e:
                self.finish_conversion(False, str(e), None)

        self.conv_thread = threading.Thread(target=_worker, daemon=True)
        self.conv_thread.start()


class InfoScreen(Screen):
    """Informations- und Formatübersichtsbildschirm."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=dp(4))
        content = BoxLayout(orientation="vertical", spacing=dp(16), padding=[dp(16), dp(16), dp(16), dp(28)], size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        # App Info Card
        card_info = StyledCard(orientation="vertical", spacing=dp(10), padding=[dp(18), dp(18), dp(18), dp(18)], size_hint_y=None)
        card_info.bind(minimum_height=card_info.setter("height"))

        t = WrappingLabel(text="Universal Media Converter", font_size="20sp", bold=True)
        v = WrappingLabel(
            text="Version 2.1.2 (Samsung Galaxy A55 5G Vollversion)",
            font_size="13sp",
            color=(0.4, 0.7, 1, 1)
        )
        d = WrappingLabel(
            text=(
                "Diese App bringt alle Konvertierungsfunktionen der Desktop-Version "
                "direkt auf Ihr Samsung Galaxy A55 5G:\n\n"
                "1. YouTube Downloader:\n"
                "   - Musik als MP3, M4A oder WAV mit bis zu 320 kbps\n"
                "   - Videos in Full HD (1080p), HD (720p) oder 480p\n\n"
                "2. Audio & Video Konverter:\n"
                "   - Konvertierung zwischen MP4, MOV, MKV, MP3, WAV, FLAC, AAC, M4A, OGG, OPUS und GIF\n"
                "   - Integrierter FFmpeg-Beschleuniger für 64-Bit ARM\n\n"
                "3. Bild-Konverter:\n"
                "   - Umwandlung von JPEG, PNG, WEBP, BMP, GIF, ICO, TIFF und PDF\n"
                "   - Einstellbare Qualitätsstufen (100% bis 75% oder verlustfrei)\n\n"
                "4. Dokumente & Tabellen:\n"
                "   - Tabellen: CSV, XLSX, JSON, HTML\n"
                "   - Dokumente: PDF-Textextraktion, DOCX, TXT\n\n"
                "5. Dateiverwaltung auf Samsung:\n"
                "   Alle Ausgaben landen im Standardordner 'Download/UniversalConverter' "
                "und können direkt in Samsung 'Eigene Dateien', der Galerie oder Samsung Music geöffnet werden."
            ),
            font_size="13sp",
            color=(0.85, 0.88, 0.95, 1)
        )
        card_info.add_widget(t)
        card_info.add_widget(v)
        card_info.add_widget(d)
        content.add_widget(card_info)

        scroll.add_widget(content)
        self.add_widget(scroll)


class UniversalConverterMobileApp(App):
    """Haupt-App mit responsiver Navigationsleiste für alle 5 Kategorien."""
    def build(self):
        Window.clearcolor = (0.06, 0.07, 0.09, 1)
        request_android_permissions()

        root = BoxLayout(orientation="vertical")

        # Obere horizontal scrollbare Navigationsleiste für 5 Kategorien
        nav_scroll = ScrollView(
            size_hint_y=None,
            height=dp(58),
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=0
        )
        nav_box = BoxLayout(
            orientation="horizontal",
            size_hint_x=None,
            padding=[dp(8), dp(6), dp(8), dp(6)],
            spacing=dp(8)
        )
        nav_box.bind(minimum_width=nav_box.setter("width"))

        with nav_scroll.canvas.before:
            Color(0.09, 0.10, 0.13, 1)
            self.bar_rect = Rectangle(pos=nav_scroll.pos, size=nav_scroll.size)
        nav_scroll.bind(
            pos=lambda *_: setattr(self.bar_rect, "pos", nav_scroll.pos),
            size=lambda *_: setattr(self.bar_rect, "size", nav_scroll.size)
        )

        self.sm = ScreenManager(transition=FadeTransition(duration=0.15))
        self.sm.add_widget(YouTubeScreen(name="youtube"))
        self.sm.add_widget(AudioVideoScreen(name="audiovideo"))
        self.sm.add_widget(ImageScreen(name="image"))
        self.sm.add_widget(DocumentScreen(name="document"))
        self.sm.add_widget(InfoScreen(name="info"))

        self.nav_buttons = {}
        tabs = [
            ("youtube", "YouTube"),
            ("audiovideo", "Audio / Video"),
            ("image", "Bilder"),
            ("document", "Dokumente"),
            ("info", "Info"),
        ]

        for screen_name, label_text in tabs:
            btn = Button(
                text=label_text,
                size_hint_x=None,
                width=dp(105),
                background_normal="",
                background_color=(0.17, 0.42, 0.95, 1) if screen_name == "youtube" else (0.13, 0.15, 0.20, 1),
                color=(1, 1, 1, 1) if screen_name == "youtube" else (0.75, 0.8, 0.9, 1),
                font_size="13sp",
                bold=True
            )
            btn.bind(on_release=lambda _, name=screen_name: self.switch_screen(name))
            self.nav_buttons[screen_name] = btn
            nav_box.add_widget(btn)

        nav_scroll.add_widget(nav_box)
        root.add_widget(nav_scroll)
        root.add_widget(self.sm)

        return root

    def switch_screen(self, screen_name):
        self.sm.current = screen_name
        for name, btn in self.nav_buttons.items():
            if name == screen_name:
                btn.background_color = (0.17, 0.42, 0.95, 1)
                btn.color = (1, 1, 1, 1)
            else:
                btn.background_color = (0.13, 0.15, 0.20, 1)
                btn.color = (0.75, 0.8, 0.9, 1)


if __name__ == "__main__":
    UniversalConverterMobileApp().run()
