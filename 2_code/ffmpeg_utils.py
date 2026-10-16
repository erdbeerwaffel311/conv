"""FFmpeg utility functions for discovering binaries, probing media, and running conversions."""

import os
import re
import shutil
import subprocess
import sys
from typing import Callable, Dict, Optional, Tuple, List


# Windows subprocess flags to avoid flashing console windows
SUBPROCESS_EXTRA = {}
if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
    SUBPROCESS_EXTRA["creationflags"] = subprocess.CREATE_NO_WINDOW


def find_binary(binary_name: str) -> Optional[str]:
    """Find binary path in PyInstaller bundle, PATH, or common macOS/Windows locations."""
    candidate_names = [f"{binary_name}.exe", binary_name] if sys.platform == "win32" else [binary_name]

    # Check if running inside PyInstaller bundle
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        exe_dir = os.path.dirname(sys.executable)
        for name in candidate_names:
            for d in [base_dir, exe_dir, os.path.join(exe_dir, "..", "Resources"), os.path.join(exe_dir, "..", "Frameworks")]:
                p = os.path.join(d, name)
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    return p

    # Check standard PATH
    for name in candidate_names:
        p = shutil.which(name)
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return p

    # Check platform-specific locations
    search_paths = []
    if sys.platform == "win32":
        for name in candidate_names:
            search_paths.extend([
                os.path.join(os.getcwd(), name),
                os.path.join(os.getcwd(), "bin", name),
                f"C:\\ffmpeg\\bin\\{name}",
                f"C:\\Program Files\\ffmpeg\\bin\\{name}",
                f"C:\\ProgramData\\chocolatey\\bin\\{name}",
            ])
    else:
        for name in candidate_names:
            search_paths.extend([
                f"/opt/homebrew/bin/{name}",
                f"/usr/local/bin/{name}",
                f"/opt/local/bin/{name}",
                f"/usr/bin/{name}",
                os.path.expanduser(f"~/bin/{name}"),
                os.path.expanduser(f"~/.local/bin/{name}"),
            ])

    for sp in search_paths:
        if os.path.isfile(sp) and os.access(sp, os.X_OK):
            return sp
    return None


# If frozen in PyInstaller, ensure bundle directory and Frameworks are in PATH
if getattr(sys, "frozen", False):
    _exe_dir = os.path.dirname(sys.executable)
    _bdir = getattr(sys, "_MEIPASS", _exe_dir)
    _fw_dir = os.path.abspath(os.path.join(_exe_dir, "..", "Frameworks"))
    _res_dir = os.path.abspath(os.path.join(_exe_dir, "..", "Resources"))
    for d in [_bdir, _fw_dir, _res_dir, _exe_dir]:
        if os.path.isdir(d) and d not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{d}:{os.environ.get('PATH', '')}"

FFMPEG_PATH = find_binary("ffmpeg")
FFPROBE_PATH = find_binary("ffprobe")


def get_media_info(file_path: str) -> Dict[str, any]:
    """Get basic duration and stream info using ffprobe."""
    info = {
        "duration": 0.0,
        "has_video": False,
        "has_audio": False,
        "video_codec": None,
        "audio_codec": None,
        "width": 0,
        "height": 0,
    }
    ffprobe = FFPROBE_PATH or find_binary("ffprobe")
    if not ffprobe or not os.path.exists(file_path):
        return info

    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration:stream=codec_name,codec_type,width,height",
        "-of", "default=noprint_wrappers=1",
        file_path,
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, **SUBPROCESS_EXTRA)
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("duration="):
                try:
                    info["duration"] = float(line.split("=")[1])
                except (ValueError, IndexError):
                    pass
            elif line.startswith("codec_type=video"):
                info["has_video"] = True
            elif line.startswith("codec_type=audio"):
                info["has_audio"] = True
            elif line.startswith("codec_name="):
                codec = line.split("=")[1]
                if not info["video_codec"] and info["has_video"]:
                    info["video_codec"] = codec
                elif not info["audio_codec"] and info["has_audio"]:
                    info["audio_codec"] = codec
            elif line.startswith("width="):
                try:
                    info["width"] = int(line.split("=")[1])
                except (ValueError, IndexError):
                    pass
            elif line.startswith("height="):
                try:
                    info["height"] = int(line.split("=")[1])
                except (ValueError, IndexError):
                    pass
    except Exception:
        pass
    return info


# Supported target formats with their default extension and encoding settings
AUDIO_FORMATS = {
    "MP3": {
        "ext": "mp3",
        "codec": "libmp3lame",
        "description": "MP3 (MPEG Audio Layer III) - Höchste Kompatibilität",
        "qualities": ["320k", "256k", "192k", "128k"],
        "default_quality": "320k",
    },
    "WAV": {
        "ext": "wav",
        "codec": "pcm_s16le",
        "description": "WAV (PCM 16-Bit) - Unkomprimierte Studio-Qualität",
        "qualities": ["Lossless"],
        "default_quality": "Lossless",
    },
    "FLAC": {
        "ext": "flac",
        "codec": "flac",
        "description": "FLAC - Verlustfrei komprimiert",
        "qualities": ["Lossless"],
        "default_quality": "Lossless",
    },
    "AAC": {
        "ext": "aac",
        "codec": "aac",
        "description": "AAC (Advanced Audio Coding) - Modern & effizient",
        "qualities": ["320k", "256k", "192k", "128k"],
        "default_quality": "256k",
    },
    "M4A": {
        "ext": "m4a",
        "codec": "aac",
        "description": "M4A (Apple Audio AAC)",
        "qualities": ["320k", "256k", "192k", "128k"],
        "default_quality": "256k",
    },
    "AIFF": {
        "ext": "aiff",
        "codec": "pcm_s16be",
        "description": "AIFF (Apple Audio Interchange) - Unkomprimiert",
        "qualities": ["Lossless"],
        "default_quality": "Lossless",
    },
    "OGG": {
        "ext": "ogg",
        "codec": "libvorbis",
        "description": "OGG Vorbis - Open-Source Audio",
        "qualities": ["320k", "256k", "192k", "128k"],
        "default_quality": "192k",
    },
    "OPUS": {
        "ext": "opus",
        "codec": "libopus",
        "description": "Opus - Extrem effizient bei niedrigen Bitraten",
        "qualities": ["256k", "192k", "128k", "96k"],
        "default_quality": "160k",
    },
}

VIDEO_FORMATS = {
    "MP4": {
        "ext": "mp4",
        "vcodec": "libx264",
        "acodec": "aac",
        "description": "MP4 (H.264 / AAC) - Universell kompatibel",
        "presets": ["Original", "1080p", "720p", "480p"],
    },
    "MOV": {
        "ext": "mov",
        "vcodec": "libx264",
        "acodec": "aac",
        "description": "MOV (Apple QuickTime)",
        "presets": ["Original", "1080p", "720p", "480p"],
    },
    "MKV": {
        "ext": "mkv",
        "vcodec": "libx264",
        "acodec": "aac",
        "description": "MKV (Matroska) - Vielseitiger Multimedia-Container",
        "presets": ["Original", "1080p", "720p", "480p"],
    },
    "WEBM": {
        "ext": "webm",
        "vcodec": "libvpx-vp9",
        "acodec": "libopus",
        "description": "WebM (VP9 / Opus) - Webstandard",
        "presets": ["Original", "1080p", "720p"],
    },
    "AVI": {
        "ext": "avi",
        "vcodec": "libxvid",
        "acodec": "libmp3lame",
        "description": "AVI (Xvid / MP3) - Legacy Format",
        "presets": ["Original", "720p", "480p"],
    },
    "GIF": {
        "ext": "gif",
        "description": "Animiertes GIF",
        "presets": ["Standard (15 fps)", "High Quality (30 fps)"],
    },
}


def build_ffmpeg_command(
    input_file: str,
    output_file: str,
    target_format: str,
    quality: str = "default",
    custom_scale: Optional[str] = None,
) -> List[str]:
    """Build FFmpeg command argument list based on input and target format."""
    ffmpeg = FFMPEG_PATH or find_binary("ffmpeg") or "ffmpeg"
    cmd = [ffmpeg, "-y", "-i", input_file]

    # Audio conversions
    if target_format.upper() in AUDIO_FORMATS:
        cfg = AUDIO_FORMATS[target_format.upper()]
        cmd.extend(["-vn"])  # Strip video stream if input is a video
        cmd.extend(["-c:a", cfg["codec"]])
        effective_quality = quality if quality != "default" else cfg.get("default_quality", "Lossless")
        if effective_quality != "Lossless" and effective_quality.endswith("k"):
            cmd.extend(["-b:a", effective_quality])
        cmd.append(output_file)
        return cmd

    # Video to GIF
    if target_format.upper() == "GIF":
        fps = 30 if "30" in quality else 15
        # High quality palettegen filter
        vf = f"fps={fps},scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
        cmd.extend(["-vf", vf, output_file])
        return cmd

    # Video conversions
    if target_format.upper() in VIDEO_FORMATS:
        cfg = VIDEO_FORMATS[target_format.upper()]
        cmd.extend(["-c:v", cfg["vcodec"]])
        cmd.extend(["-c:a", cfg["acodec"]])

        # Preset scaling if requested
        if custom_scale and custom_scale != "Original":
            if custom_scale == "1080p":
                cmd.extend(["-vf", "scale=-2:1080"])
            elif custom_scale == "720p":
                cmd.extend(["-vf", "scale=-2:720"])
            elif custom_scale == "480p":
                cmd.extend(["-vf", "scale=-2:480"])

        # Compatibility flags for MP4/MOV
        if cfg["ext"] in ["mp4", "mov"]:
            cmd.extend(["-pix_fmt", "yuv420p", "-movflags", "+faststart"])

        cmd.append(output_file)
        return cmd

    # Fallback default
    cmd.extend([output_file])
    return cmd


def run_conversion(
    cmd: List[str],
    duration: float = 0.0,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, str]:
    """
    Executes an FFmpeg command with real-time progress parsing.
    Returns (success, message).
    """
    if "-progress" not in cmd:
        cmd.extend(["-progress", "pipe:1", "-nostats"])

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            **SUBPROCESS_EXTRA,
        )

        out_time_re = re.compile(r"out_time_ms=(\d+)")
        out_time_str_re = re.compile(r"out_time=(\d+):(\d+):(\d+(?:\.\d+)?)")

        while True:
            if is_cancelled and is_cancelled():
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return False, "Konvertierung abgebrochen."

            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue

            line = line.strip()
            if duration > 0 and progress_callback:
                m_ms = out_time_re.match(line)
                if m_ms:
                    curr_ms = int(m_ms.group(1))
                    curr_sec = curr_ms / 1_000_000.0
                    progress = min(99.0, max(0.0, (curr_sec / duration) * 100.0))
                    progress_callback(progress, f"{progress:.1f}% ({int(curr_sec)}s / {int(duration)}s)")
                else:
                    m_str = out_time_str_re.match(line)
                    if m_str:
                        h, m, s = float(m_str.group(1)), float(m_str.group(2)), float(m_str.group(3))
                        curr_sec = h * 3600 + m * 60 + s
                        progress = min(99.0, max(0.0, (curr_sec / duration) * 100.0))
                        progress_callback(progress, f"{progress:.1f}% ({int(curr_sec)}s / {int(duration)}s)")

        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.strip().splitlines()[-1] if stderr else "Unbekannter FFmpeg-Fehler"
            return False, f"FFmpeg Fehler (Code {proc.returncode}): {err_msg}"

        if progress_callback:
            progress_callback(100.0, "Fertig!")
        return True, "Erfolgreich konvertiert"

    except Exception as e:
        return False, f"Ausnahmefehler bei der Konvertierung: {str(e)}"


def convert_file(
    input_file: str,
    output_file: str,
    target_format: str,
    quality: str = "default",
    custom_scale: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, str]:
    """
    Executes conversion using FFmpeg with real-time progress parsing.
    Returns (success, message).
    """
    ffmpeg = FFMPEG_PATH or find_binary("ffmpeg")
    if not ffmpeg:
        return False, "FFmpeg wurde nicht gefunden."

    if not os.path.isfile(input_file):
        return False, f"Eingabedatei existiert nicht: {input_file}"

    out_dir = os.path.dirname(output_file)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    info = get_media_info(input_file)
    total_duration = info.get("duration", 0.0)

    cmd = build_ffmpeg_command(input_file, output_file, target_format, quality, custom_scale)
    return run_conversion(
        cmd=cmd,
        duration=total_duration,
        progress_callback=progress_callback,
        is_cancelled=is_cancelled
    )
