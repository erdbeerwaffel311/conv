"""
Native Android Storage Access Framework (SAF) integration for Samsung One UI.
Enables native file open dialog (ACTION_OPEN_DOCUMENT) and native save dialog (ACTION_CREATE_DOCUMENT).
"""

import os
import re
import threading
from typing import Callable, Optional

# Check if running on Android
IS_ANDROID = False
try:
    from jnius import autoclass
    from android import activity
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Intent = autoclass("android.content.Intent")
    Activity = autoclass("android.app.Activity")
    OpenableColumns = autoclass("android.provider.OpenableColumns")
    IS_ANDROID = True
except Exception:
    IS_ANDROID = False

_open_callbacks = {}
_save_callbacks = {}
_pending_save_paths = {}

REQ_OPEN_BASE = 1000
REQ_SAVE_BASE = 2000
_req_counter = 0


def _get_next_req_id(base):
    global _req_counter
    _req_counter = (_req_counter + 1) % 900
    return base + _req_counter


def sanitize_android_filename(name: str) -> str:
    """
    Sanitizes a filename so Samsung One UI and Android SAF accept it without '(invalid)'.
    Replaces / \ : * ? " < > | with hyphens, removes control characters, trims spaces and dots.
    """
    if not name:
        return "datei"
    s = re.sub(r'[\/\\:\*?"<>|]', '-', str(name))
    s = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s)
    s = re.sub(r'-\s*-+', '-', s)
    s = re.sub(r'\s+', ' ', s)
    s = s.strip(' .-_')
    if not s:
        return "datei"
    if len(s.encode("utf-8")) > 200:
        s = s[:80]
    return s


def _guess_mime_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    mime_map = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "flac": "audio/flac",
        "aac": "audio/aac",
        "m4a": "audio/mp4",
        "ogg": "audio/ogg",
        "opus": "audio/opus",
        "mp4": "video/mp4",
        "mov": "video/quicktime",
        "mkv": "video/x-matroska",
        "webm": "video/webm",
        "avi": "video/x-msvideo",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "json": "application/json",
        "txt": "text/plain",
        "html": "text/html",
    }
    return mime_map.get(ext, "*/*")


def _on_activity_result(request_code, result_code, intent):
    """Handles Activity Results from Samsung native file picker."""
    try:
        from kivy.clock import Clock

        # 1. Open File Result
        if request_code in _open_callbacks:
            callback = _open_callbacks.pop(request_code)
            if result_code == -1 and intent is not None:  # Activity.RESULT_OK == -1
                uri = intent.getData()
                if uri:
                    def _copy_worker():
                        try:
                            local_path = _copy_content_uri_to_cache(uri)
                            if local_path and callback:
                                Clock.schedule_once(lambda _: callback(local_path), 0)
                        finally:
                            try:
                                import jnius
                                jnius.detach()
                            except Exception:
                                pass
                    threading.Thread(target=_copy_worker, daemon=True).start()

        # 2. Save File Result
        elif request_code in _save_callbacks:
            callback = _save_callbacks.pop(request_code)
            source_file = _pending_save_paths.pop(request_code, None)
            if result_code == -1 and intent is not None and source_file:
                target_uri = intent.getData()
                if target_uri:
                    def _write_worker():
                        try:
                            success, msg = _write_file_to_content_uri(source_file, target_uri)
                            if callback:
                                Clock.schedule_once(lambda _: callback(success, msg), 0)
                        finally:
                            try:
                                import jnius
                                jnius.detach()
                            except Exception:
                                pass
                    threading.Thread(target=_write_worker, daemon=True).start()
            elif callback:
                Clock.schedule_once(lambda _: callback(False, "Speichern abgebrochen."), 0)
    except Exception as e:
        print(f"Error in on_activity_result: {e}")


if IS_ANDROID:
    try:
        activity.bind(on_activity_result=_on_activity_result)
    except Exception as e:
        print(f"Failed to bind activity result: {e}")


def _copy_content_uri_to_cache(uri) -> Optional[str]:
    """Copies content from a content:// Uri to a real file path in the app cache directory."""
    try:
        activity_obj = PythonActivity.mActivity
        content_resolver = activity_obj.getContentResolver()

        display_name = "ausgewaehlte_datei"
        cursor = None
        try:
            cursor = content_resolver.query(uri, None, None, None, None)
            if cursor is not None and cursor.moveToFirst():
                name_idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if name_idx >= 0:
                    val = cursor.getString(name_idx)
                    if val:
                        display_name = val
        finally:
            if cursor is not None:
                cursor.close()

        base, ext = os.path.splitext(display_name)
        clean_base = sanitize_android_filename(base)
        clean_name = f"{clean_base}{ext}" if ext else clean_base

        cache_dir = activity_obj.getCacheDir().getAbsolutePath()
        os.makedirs(cache_dir, exist_ok=True)
        dest_path = os.path.join(cache_dir, clean_name)

        input_stream = content_resolver.openInputStream(uri)
        if input_stream is None:
            return None

        FileOutputStream = autoclass("java.io.FileOutputStream")
        File = autoclass("java.io.File")
        Channels = autoclass("java.nio.channels.Channels")

        dest_file = File(dest_path)
        out_stream = FileOutputStream(dest_file)
        in_channel = Channels.newChannel(input_stream)
        out_channel = out_stream.getChannel()

        try:
            CHUNK = 16 * 1024 * 1024
            pos = 0
            while True:
                transferred = out_channel.transferFrom(in_channel, pos, CHUNK)
                if transferred <= 0:
                    break
                pos += transferred
        finally:
            try:
                in_channel.close()
            except Exception:
                pass
            try:
                input_stream.close()
            except Exception:
                pass
            try:
                out_channel.close()
            except Exception:
                pass
            try:
                out_stream.flush()
                out_stream.close()
            except Exception:
                pass

        if os.path.isfile(dest_path) and os.path.getsize(dest_path) > 0:
            return dest_path
        return None
    except Exception as e:
        print(f"Error copying URI to cache: {e}")
        return None


def _write_file_to_content_uri(source_file: str, target_uri) -> tuple:
    """Writes a local file to a destination content:// Uri chosen by the user."""
    try:
        if not os.path.isfile(source_file):
            return False, f"Quelldatei nicht gefunden: {source_file}"

        file_size = os.path.getsize(source_file)
        if file_size == 0:
            return False, "Quelldatei ist leer (0 Bytes)."

        activity_obj = PythonActivity.mActivity
        content_resolver = activity_obj.getContentResolver()

        # Open target OutputStream with 'wt' (write + truncate)
        out_stream = content_resolver.openOutputStream(target_uri, "wt")
        if out_stream is None:
            out_stream = content_resolver.openOutputStream(target_uri)
        if out_stream is None:
            return False, "Konnte Zielort nicht zum Schreiben öffnen."

        FileInputStream = autoclass("java.io.FileInputStream")
        File = autoclass("java.io.File")
        Channels = autoclass("java.nio.channels.Channels")

        in_file = File(source_file)
        in_stream = FileInputStream(in_file)
        in_channel = in_stream.getChannel()
        out_channel = Channels.newChannel(out_stream)

        try:
            transferred = 0
            size = in_channel.size()
            while transferred < size:
                sent = in_channel.transferTo(transferred, size - transferred, out_channel)
                if sent <= 0:
                    break
                transferred += sent
        finally:
            try:
                out_channel.close()
            except Exception:
                pass
            try:
                out_stream.flush()
                out_stream.close()
            except Exception:
                pass
            try:
                in_channel.close()
            except Exception:
                pass
            try:
                in_stream.close()
            except Exception:
                pass

        filename = os.path.basename(source_file)
        size_mb = file_size / (1024 * 1024)
        return True, f"'{filename}' ({size_mb:.1f} MB) erfolgreich gespeichert!"
    except Exception as e:
        return False, f"Fehler beim Speichern: {str(e)}"


def open_file_native(callback: Callable[[str], None], mime_type: str = "*/*") -> bool:
    """
    Öffnet die native Android-Dateiauswahl (Samsung Eigene Dateien / Galerie / Downloads).
    Ruft callback(local_file_path) auf, sobald die Datei gewählt wurde.
    Gibt True zurück, wenn der Dialog erfolgreich gestartet wurde.
    """
    if not IS_ANDROID:
        return False

    try:
        req_id = _get_next_req_id(REQ_OPEN_BASE)
        _open_callbacks[req_id] = callback

        activity_obj = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.setType(mime_type)

        activity_obj.startActivityForResult(intent, req_id)
        return True
    except Exception as e:
        print(f"Failed to launch native file picker: {e}")
        return False


def save_file_native(
    source_file_path: str,
    default_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    callback: Optional[Callable[[bool, str], None]] = None
) -> bool:
    """
    Öffnet den nativen Android 'Speichern unter'-Dialog (ACTION_CREATE_DOCUMENT).
    Der Nutzer wählt den Zielordner und Dateinamen auf seinem Samsung-Gerät aus.
    Stellt sicher, dass Dateinamen sauber bereinigt und mit korrekter Dateiendung
    übergeben werden, sodass Samsung One UI niemals '(invalid)' anzeigt.
    """
    if not IS_ANDROID or not os.path.isfile(source_file_path):
        return False

    try:
        raw_name = default_name or os.path.basename(source_file_path)
        base, ext = os.path.splitext(raw_name)
        clean_base = sanitize_android_filename(base)
        clean_ext = ext if ext else ""
        clean_filename = f"{clean_base}{clean_ext}"

        resolved_mime = mime_type if mime_type else _guess_mime_type(clean_filename)

        req_id = _get_next_req_id(REQ_SAVE_BASE)
        _save_callbacks[req_id] = callback
        _pending_save_paths[req_id] = source_file_path

        activity_obj = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.setType(resolved_mime)
        # Übergebe sauberen Dateinamen inklusive Endung an EXTRA_TITLE
        intent.putExtra(Intent.EXTRA_TITLE, clean_filename)

        activity_obj.startActivityForResult(intent, req_id)
        return True
    except Exception as e:
        print(f"Failed to launch native save dialog: {e}")
        return False
