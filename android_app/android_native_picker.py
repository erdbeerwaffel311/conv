"""
Native Android Storage Access Framework (SAF) integration for Samsung One UI.
Enables native file open dialog (ACTION_OPEN_DOCUMENT) and native save dialog (ACTION_CREATE_DOCUMENT).
"""

import os
import shutil
import threading
from typing import Callable, Optional

# Check if running on Android
IS_ANDROID = False
try:
    from jnius import autoclass
    import android.activity
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
                        local_path = _copy_content_uri_to_cache(uri)
                        if local_path and callback:
                            Clock.schedule_once(lambda _: callback(local_path), 0)
                    threading.Thread(target=_copy_worker, daemon=True).start()

        # 2. Save File Result
        elif request_code in _save_callbacks:
            callback = _save_callbacks.pop(request_code)
            source_file = _pending_save_paths.pop(request_code, None)
            if result_code == -1 and intent is not None and source_file:
                target_uri = intent.getData()
                if target_uri:
                    def _write_worker():
                        success, msg = _write_file_to_content_uri(source_file, target_uri)
                        if callback:
                            Clock.schedule_once(lambda _: callback(success, msg), 0)
                    threading.Thread(target=_write_worker, daemon=True).start()
            elif callback:
                Clock.schedule_once(lambda _: callback(False, "Speichern abgebrochen."), 0)
    except Exception as e:
        print(f"Error in on_activity_result: {e}")


if IS_ANDROID:
    try:
        android.activity.bind(on_activity_result=_on_activity_result)
    except Exception as e:
        print(f"Failed to bind activity result: {e}")


def _copy_content_uri_to_cache(uri) -> Optional[str]:
    """Copies content from a content:// Uri to a real file path in the app cache directory."""
    try:
        activity = PythonActivity.mActivity
        content_resolver = activity.getContentResolver()

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

        cache_dir = activity.getCacheDir().getAbsolutePath()
        os.makedirs(cache_dir, exist_ok=True)
        dest_path = os.path.join(cache_dir, display_name)

        pfd = content_resolver.openFileDescriptor(uri, "r")
        if pfd is not None:
            fd = pfd.detachFd()
            with os.fdopen(fd, "rb") as in_f, open(dest_path, "wb") as out_f:
                shutil.copyfileobj(in_f, out_f, length=64 * 1024)
            return dest_path

        return None
    except Exception as e:
        print(f"Error copying URI to cache: {e}")
        return None


def _write_file_to_content_uri(source_file: str, target_uri) -> tuple:
    """Writes a local file to a destination content:// Uri chosen by the user."""
    try:
        activity = PythonActivity.mActivity
        content_resolver = activity.getContentResolver()

        pfd = content_resolver.openFileDescriptor(target_uri, "w")
        if pfd is not None:
            fd = pfd.detachFd()
            with open(source_file, "rb") as in_f, os.fdopen(fd, "wb") as out_f:
                shutil.copyfileobj(in_f, out_f, length=64 * 1024)
            return True, "Datei erfolgreich im ausgewählten Ordner gespeichert!"
        return False, "Konnte Zielort nicht öffnen."
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

        activity = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.setType(mime_type)

        activity.startActivityForResult(intent, req_id)
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
    """
    if not IS_ANDROID or not os.path.isfile(source_file_path):
        return False

    try:
        filename = default_name or os.path.basename(source_file_path)
        resolved_mime = mime_type if mime_type else _guess_mime_type(filename)

        req_id = _get_next_req_id(REQ_SAVE_BASE)
        _save_callbacks[req_id] = callback
        _pending_save_paths[req_id] = source_file_path

        activity = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.setType(resolved_mime)
        intent.putExtra(Intent.EXTRA_TITLE, filename)

        activity.startActivityForResult(intent, req_id)
        return True
    except Exception as e:
        print(f"Failed to launch native save dialog: {e}")
        return False
