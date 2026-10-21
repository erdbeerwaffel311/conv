"""YouTube downloader engine powered by yt-dlp."""

import os
import re
import sys
from typing import Callable, Dict, Optional, Tuple, Any
import yt_dlp

# Ensure common macOS binary locations are in PATH
for p in ["/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/bin")]:
    if os.path.isdir(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{p}:{os.environ.get('PATH', '')}"

from ffmpeg_utils import FFMPEG_PATH, find_binary


def clean_filename(s: str) -> str:
    """Sanitize filename for macOS/Unix."""
    return re.sub(r'[\\/*?:"<>|]', "", s).strip()


def get_ydl_base_opts() -> Dict[str, Any]:
    """Return common robust yt-dlp options bypassing SABR & bot blocks."""
    ffmpeg = FFMPEG_PATH or find_binary("ffmpeg")
    opts = {
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
        "restrictfilenames": False,
        # Bypass YouTube SABR / bot challenge by using iOS/Android/mweb player clients
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "mweb"]
            }
        },
    }
    if ffmpeg:
        opts["ffmpeg_location"] = os.path.dirname(ffmpeg)
    return opts


def fetch_video_metadata(url: str) -> Dict[str, Any]:
    """Fetch video title and basic info quickly without downloading."""
    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        "skip_download": True,
        "extract_flat": "in_playlist",
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if "entries" in info:  # Playlist
                title = f"Playlist: {info.get('title', 'YouTube Playlist')} ({len(info['entries'])} Videos)"
            else:
                title = info.get("title", url)
            return {"title": title, "duration": info.get("duration", 0), "uploader": info.get("uploader", "")}
    except Exception as e:
        return {"title": url, "error": str(e)}


def download_youtube_media(
    url: str,
    output_dir: str,
    target_format: str = "MP3",
    quality: str = "320k",
    embed_thumbnail: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Downloads media from YouTube and converts it according to target_format & quality.
    Supports audio extraction (MP3, WAV, FLAC, M4A, AAC) and video (MP4, MKV, MOV, WEBM).
    Returns (success, message, output_filepath).
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    target_format = target_format.upper()
    is_audio = target_format in ["MP3", "WAV", "FLAC", "M4A", "AAC", "OGG", "OPUS"]

    output_file_holder = {"path": None}

    def ydl_progress_hook(d: Dict[str, Any]):
        if is_cancelled and is_cancelled():
            raise Exception("Download abgebrochen.")

        status = d.get("status")
        if status == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed")
            eta = d.get("eta")

            speed_str = f"{speed / (1024 * 1024):.1f} MB/s" if speed else ""
            eta_str = f"ETA: {int(eta)}s" if eta else ""

            if total_bytes > 0:
                pct = min(99.0, (downloaded / total_bytes) * 100.0)
                status_msg = f"{pct:.1f}% ({speed_str} {eta_str})".strip()
                if progress_callback:
                    progress_callback(pct, status_msg)
            else:
                if progress_callback:
                    progress_callback(50.0, f"Lade herunter... {speed_str}".strip())

        elif status == "finished":
            filename = d.get("filename")
            if filename:
                output_file_holder["path"] = filename
            if progress_callback:
                progress_callback(95.0, "Konvertiere / verarbeite Metadaten...")

    outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        "outtmpl": outtmpl,
        "progress_hooks": [ydl_progress_hook],
    })

    has_ffmpeg = bool(FFMPEG_PATH or find_binary("ffmpeg"))
    postprocessors = []

    if is_audio:
        # Standalone reliable audio download without ffprobe dependency
        ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    else:
        # Video Download
        video_ext = target_format.lower()
        if has_ffmpeg:
            if quality in ["2160p", "4K"]:
                format_spec = "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best"
            elif quality == "1440p":
                format_spec = "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best"
            elif quality == "1080p":
                format_spec = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
            elif quality == "720p":
                format_spec = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
            elif quality == "480p":
                format_spec = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
            else:
                format_spec = "bestvideo+bestaudio/best"

            ydl_opts["format"] = format_spec
            ydl_opts["merge_output_format"] = video_ext if video_ext in ["mp4", "mkv", "mov", "webm"] else "mp4"

            if embed_thumbnail:
                ydl_opts["writethumbnail"] = True
                postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
                if video_ext in ["mp4", "mkv", "mov"]:
                    postprocessors.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
        else:
            # Standalone Android mode without FFmpeg: download YouTube's pre-muxed MP4 directly
            ydl_opts["format"] = "best[ext=mp4]/best"

    if postprocessors and has_ffmpeg:
        ydl_opts["postprocessors"] = postprocessors

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_file = None
            if "requested_downloads" in info and len(info["requested_downloads"]) > 0:
                final_file = info["requested_downloads"][0].get("filepath")
            elif output_file_holder["path"]:
                final_file = output_file_holder["path"]

            # If post-processing converted the extension (e.g. .mp4 -> .mp3)
            if final_file and not os.path.exists(final_file):
                base_no_ext = os.path.splitext(final_file)[0]
                expected_ext = target_format.lower()
                candidate = f"{base_no_ext}.{expected_ext}"
                if os.path.exists(candidate):
                    final_file = candidate

            # Perform audio conversion if target format differs from downloaded native stream
            if is_audio and final_file and os.path.exists(final_file):
                curr_ext = os.path.splitext(final_file)[1].lower().lstrip(".")
                target_ext = target_format.lower()
                if curr_ext != target_ext:
                    ffmpeg_bin = FFMPEG_PATH or find_binary("ffmpeg")
                    if ffmpeg_bin:
                        out_target = os.path.splitext(final_file)[0] + f".{target_ext}"
                        if progress_callback:
                            progress_callback(95.0, f"Konvertiere in {target_format}...")
                        import ffmpeg_utils
                        success, conv_msg = ffmpeg_utils.convert_file(
                            input_file=final_file,
                            output_file=out_target,
                            target_format=target_format,
                            quality=quality,
                            progress_callback=progress_callback,
                            is_cancelled=is_cancelled
                        )
                        if success and os.path.exists(out_target):
                            try:
                                os.remove(final_file)
                            except Exception:
                                pass
                            final_file = out_target

            if progress_callback:
                progress_callback(100.0, "Fertig!")

            # Ensure the output file has the clean YouTube title without illegal characters
            if final_file and os.path.exists(final_file):
                try:
                    from android_native_picker import sanitize_android_filename
                    raw_title = info.get("title") or os.path.splitext(os.path.basename(final_file))[0]
                    clean_title = sanitize_android_filename(raw_title)
                    curr_ext = os.path.splitext(final_file)[1].lstrip(".")
                    target_ext = target_format.lower()
                    effective_ext = target_ext if target_ext in ["mp3", "m4a", "wav", "flac", "aac", "ogg", "opus", "mp4", "mkv", "mov", "webm"] else curr_ext
                    if effective_ext == "jpeg":
                        effective_ext = "jpg"
                    desired_path = os.path.join(output_dir, f"{clean_title}.{effective_ext}")
                    if os.path.abspath(final_file) != os.path.abspath(desired_path):
                        if os.path.exists(desired_path):
                            os.remove(desired_path)
                        os.rename(final_file, desired_path)
                        final_file = desired_path
                except Exception as e:
                    print(f"Failed to rename YouTube media to clean title: {e}")

            return True, "Download und Konvertierung erfolgreich abgeschlossen.", final_file
    except Exception as e:
        err = str(e)
        if "Download abgebrochen" in err:
            return False, "Download durch Benutzer abgebrochen.", None
        return False, f"Fehler beim Download: {err}", None
