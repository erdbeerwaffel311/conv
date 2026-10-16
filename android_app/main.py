"""
Universal Media Converter - Mobile Android App (Kivy).
Speziell optimiert fuer das Samsung Galaxy A55 5G (Hochkant-Display, 1080x2340, ARM64).
"""

import os
import sys
import threading
from typing import List, Optional

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
from kivy.graphics import Color, RoundedRectangle, Rectangle


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
    Label, das Text automatisch umbricht und seine Hoehe dynamisch
    an den Inhalt anpasst, sodass auf keinem Bildschirm Text abgeschnitten wird.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
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
    """Dropdown-Eintrag mit bequemer Touch-Hoehe fuer Smartphones."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(46)
        self.font_size = "14sp"
        self.background_normal = ""
        self.background_color = (0.16, 0.19, 0.26, 1.0)
        self.color = (0.95, 0.95, 1.0, 1.0)


class YouTubeScreen(Screen):
    """Hauptbildschirm fuer YouTube Video- und Audio-Downloads."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.download_thread = None
        self.is_cancelled = False

        # ScrollView stellt sicher, dass der gesamte Hochkant-Bildschirm
        # perfekt scrollbar ist und bei geoeffneter Tastatur nichts verdeckt wird.
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
            text="Universal Media Converter",
            font_size="20sp",
            bold=True,
            color=(1, 1, 1, 1),
            halign="left"
        )
        lbl_app_sub = WrappingLabel(
            text="YouTube Downloader - optimiert fuer Samsung Galaxy A55 5G",
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
            text="Aus Zwischenablage einfuegen",
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

        # 3. Format & Qualitaet Karte
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

        # Spalte 2: Qualitaet
        col_qual = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        col_qual.bind(minimum_height=col_qual.setter("height"))
        lbl_qual = WrappingLabel(text="Qualitaet:", font_size="12sp", color=(0.65, 0.7, 0.8, 1))
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
            text="Tippe auf 'Download starten', um den Vorgang zu beginnen.",
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
            text="Speicherort auf dem Geraet:",
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
            self.lbl_status.text = f"{int(pct)}% - Laedt herunter..."
            self.lbl_details.text = text
        Clock.schedule_once(_update)

    def finish_download(self, success, message, out_file):
        def _finish(dt):
            self.btn_download.disabled = False
            self.btn_cancel.disabled = True
            if success:
                self.progress_bar.value = 100
                self.lbl_status.text = "Download erfolgreich abgeschlossen!"
                self.lbl_details.text = (
                    f"Datei gespeichert in:\n{out_file or get_android_download_dir()}\n"
                    "Sichtbar in der Samsung Galerie und 'Eigene Dateien'."
                )
            else:
                self.lbl_status.text = "Download fehlgeschlagen"
                self.lbl_details.text = f"Fehlermeldung: {message}"
        Clock.schedule_once(_finish)

    def start_download(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.lbl_status.text = "Kein Link eingegeben"
            self.lbl_details.text = "Bitte fuege zuerst einen YouTube-Link in das Textfeld ein."
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
        self.lbl_details.text = "Download-Vorgang wird angehalten..."
        self.btn_cancel.disabled = True


class InfoScreen(Screen):
    """Informations- und Formatuebersichtsbildschirm."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(4)
        )

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=[dp(16), dp(16), dp(16), dp(28)],
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter("height"))

        # App Info Card
        card_info = StyledCard(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(18), dp(18), dp(18), dp(18)],
            size_hint_y=None
        )
        card_info.bind(minimum_height=card_info.setter("height"))

        t = WrappingLabel(text="Universal Media Converter", font_size="20sp", bold=True)
        v = WrappingLabel(
            text="Version 2.0.1 (Samsung Galaxy A55 5G Edition)",
            font_size="13sp",
            color=(0.4, 0.7, 1, 1)
        )
        d = WrappingLabel(
            text=(
                "Dieser Konverter wurde fuer die 64-Bit ARM-Architektur des Samsung "
                "Galaxy A55 5G (Exynos 1480, Android 14+) optimiert.\n\n"
                "Unterstuetzte Funktionen:\n"
                "- YouTube Musik & Audio (MP3, M4A, WAV)\n"
                "- YouTube Videos (MP4 1080p, 720p, 480p)\n"
                "- Direkte Speicherung im Ordner 'Download/UniversalConverter'\n"
                "- Sofortige Verfuegbarkeit in Samsung Music, Galerie und 'Eigene Dateien'\n\n"
                "Hinweis zur Dateiverwaltung:\n"
                "Auf Samsung-Geraeten koennen heruntergeladene Dateien direkt ueber die "
                "vorinstallierte App 'Eigene Dateien' -> 'Downloads' geoeffnet oder geteilt werden."
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
    """Haupt-App mit responsiver Navigationsleiste."""
    def build(self):
        Window.clearcolor = (0.06, 0.07, 0.09, 1)
        request_android_permissions()

        root = BoxLayout(orientation="vertical")

        # Obere Navigationsleiste mit komfortabler Touch-Hoehe
        top_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(62),
            padding=[dp(12), dp(8), dp(12), dp(8)],
            spacing=dp(10)
        )
        with top_bar.canvas.before:
            Color(0.09, 0.10, 0.13, 1)
            self.bar_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(
            pos=lambda *_: setattr(self.bar_rect, "pos", top_bar.pos),
            size=lambda *_: setattr(self.bar_rect, "size", top_bar.size)
        )

        self.sm = ScreenManager(transition=FadeTransition(duration=0.15))
        self.sm.add_widget(YouTubeScreen(name="youtube"))
        self.sm.add_widget(InfoScreen(name="info"))

        self.btn_nav_yt = Button(
            text="YouTube",
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_color=(0.17, 0.42, 0.95, 1),
            color=(1, 1, 1, 1),
            font_size="15sp",
            bold=True
        )

        self.btn_nav_info = Button(
            text="Info & Formate",
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_color=(0.14, 0.16, 0.22, 1),
            color=(0.75, 0.8, 0.9, 1),
            font_size="14sp"
        )

        def switch_to_yt(_):
            self.sm.current = "youtube"
            self.btn_nav_yt.background_color = (0.17, 0.42, 0.95, 1)
            self.btn_nav_yt.color = (1, 1, 1, 1)
            self.btn_nav_info.background_color = (0.14, 0.16, 0.22, 1)
            self.btn_nav_info.color = (0.75, 0.8, 0.9, 1)

        def switch_to_info(_):
            self.sm.current = "info"
            self.btn_nav_info.background_color = (0.17, 0.42, 0.95, 1)
            self.btn_nav_info.color = (1, 1, 1, 1)
            self.btn_nav_yt.background_color = (0.14, 0.16, 0.22, 1)
            self.btn_nav_yt.color = (0.75, 0.8, 0.9, 1)

        self.btn_nav_yt.bind(on_release=switch_to_yt)
        self.btn_nav_info.bind(on_release=switch_to_info)

        top_bar.add_widget(self.btn_nav_yt)
        top_bar.add_widget(self.btn_nav_info)

        root.add_widget(top_bar)
        root.add_widget(self.sm)

        return root


if __name__ == "__main__":
    UniversalConverterMobileApp().run()
