"""Format detection and compatibility validation matrix."""

import os
from typing import Dict, List, Optional, Tuple
from converter_models import TaskType

# Strict mapping: extension -> (Category, List of allowed target formats, Default target format, TaskType)
FORMAT_RULES: Dict[str, Tuple[str, List[str], str, TaskType]] = {
    # Video
    "mp4":  ("Video", ["MP4", "MOV", "MKV", "WEBM", "AVI", "GIF", "MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP3", TaskType.LOCAL_FILE),
    "mov":  ("Video", ["MP4", "MOV", "MKV", "WEBM", "AVI", "GIF", "MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP4", TaskType.LOCAL_FILE),
    "mkv":  ("Video", ["MP4", "MOV", "MKV", "WEBM", "AVI", "GIF", "MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP4", TaskType.LOCAL_FILE),
    "webm": ("Video", ["MP4", "MOV", "MKV", "WEBM", "AVI", "GIF", "MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP4", TaskType.LOCAL_FILE),
    "avi":  ("Video", ["MP4", "MOV", "MKV", "WEBM", "AVI", "GIF", "MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP4", TaskType.LOCAL_FILE),
    "flv":  ("Video", ["MP4", "MOV", "MKV", "WEBM", "AVI", "GIF", "MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP4", TaskType.LOCAL_FILE),
    "m4v":  ("Video", ["MP4", "MOV", "MKV", "WEBM", "AVI", "GIF", "MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP4", TaskType.LOCAL_FILE),

    # Audio
    "mp3":  ("Audio", ["MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "WAV", TaskType.LOCAL_FILE),
    "wav":  ("Audio", ["MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP3", TaskType.LOCAL_FILE),
    "flac": ("Audio", ["MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP3", TaskType.LOCAL_FILE),
    "aac":  ("Audio", ["MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP3", TaskType.LOCAL_FILE),
    "m4a":  ("Audio", ["MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP3", TaskType.LOCAL_FILE),
    "aiff": ("Audio", ["MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP3", TaskType.LOCAL_FILE),
    "aif":  ("Audio", ["MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP3", TaskType.LOCAL_FILE),
    "ogg":  ("Audio", ["MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP3", TaskType.LOCAL_FILE),
    "opus": ("Audio", ["MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP3", TaskType.LOCAL_FILE),
    "wma":  ("Audio", ["MP3", "WAV", "FLAC", "AAC", "M4A", "AIFF", "OGG", "OPUS"], "MP3", TaskType.LOCAL_FILE),

    # Images
    "jpg":  ("Bild", ["JPEG", "PNG", "HEIC", "WEBP", "TIFF", "BMP", "GIF", "ICO", "PDF"], "PNG", TaskType.IMAGE),
    "jpeg": ("Bild", ["JPEG", "PNG", "HEIC", "WEBP", "TIFF", "BMP", "GIF", "ICO", "PDF"], "PNG", TaskType.IMAGE),
    "png":  ("Bild", ["JPEG", "PNG", "HEIC", "WEBP", "TIFF", "BMP", "GIF", "ICO", "PDF"], "JPEG", TaskType.IMAGE),
    "heic": ("Bild", ["JPEG", "PNG", "WEBP", "TIFF", "BMP", "GIF", "ICO", "PDF"], "JPEG", TaskType.IMAGE),
    "heif": ("Bild", ["JPEG", "PNG", "WEBP", "TIFF", "BMP", "GIF", "ICO", "PDF"], "JPEG", TaskType.IMAGE),
    "webp": ("Bild", ["PNG", "JPEG", "HEIC", "TIFF", "BMP", "GIF", "ICO", "PDF"], "PNG", TaskType.IMAGE),
    "tiff": ("Bild", ["PNG", "JPEG", "HEIC", "WEBP", "BMP", "GIF", "ICO", "PDF"], "PNG", TaskType.IMAGE),
    "tif":  ("Bild", ["PNG", "JPEG", "HEIC", "WEBP", "BMP", "GIF", "ICO", "PDF"], "PNG", TaskType.IMAGE),
    "bmp":  ("Bild", ["PNG", "JPEG", "HEIC", "WEBP", "TIFF", "GIF", "ICO", "PDF"], "PNG", TaskType.IMAGE),
    "gif":  ("Bild", ["PNG", "JPEG", "WEBP", "BMP", "TIFF", "PDF"], "PNG", TaskType.IMAGE),
    "ico":  ("Bild", ["PNG", "JPEG", "WEBP", "BMP", "TIFF"], "PNG", TaskType.IMAGE),
    "psd":  ("Bild", ["PNG", "JPEG", "WEBP", "TIFF", "BMP", "PDF"], "PNG", TaskType.IMAGE),
    "avif": ("Bild", ["PNG", "JPEG", "WEBP", "TIFF", "PDF"], "PNG", TaskType.IMAGE),

    # Spreadsheets / Tables (strictly separated from docx)
    "xlsx": ("Tabelle", ["CSV", "PDF", "JSON", "HTML"], "CSV", TaskType.DOCUMENT),
    "xls":  ("Tabelle", ["CSV", "XLSX", "PDF", "JSON", "HTML"], "CSV", TaskType.DOCUMENT),
    "csv":  ("Tabelle", ["XLSX", "PDF", "JSON", "HTML", "TXT"], "XLSX", TaskType.DOCUMENT),
    "tsv":  ("Tabelle", ["XLSX", "CSV", "PDF", "JSON", "HTML"], "XLSX", TaskType.DOCUMENT),

    # Documents & Text (strictly separated from xlsx/csv tables)
    "pdf":  ("Dokument", ["DOCX", "TXT", "PNG", "JPG", "HTML"], "DOCX", TaskType.DOCUMENT),
    "docx": ("Dokument", ["PDF", "TXT", "HTML", "RTF"], "PDF", TaskType.DOCUMENT),
    "doc":  ("Dokument", ["DOCX", "PDF", "TXT", "HTML"], "PDF", TaskType.DOCUMENT),
    "txt":  ("Dokument", ["PDF", "DOCX", "HTML"], "PDF", TaskType.DOCUMENT),
    "md":   ("Dokument", ["PDF", "DOCX", "HTML", "TXT"], "PDF", TaskType.DOCUMENT),
    "rtf":  ("Dokument", ["DOCX", "PDF", "TXT", "HTML"], "PDF", TaskType.DOCUMENT),
    "html": ("Dokument", ["PDF", "DOCX", "TXT"], "PDF", TaskType.DOCUMENT),
}


def get_file_extension(file_path: str) -> str:
    """Extract clean lowercase extension without leading dot."""
    return os.path.splitext(file_path)[1].lower().lstrip(".")


def detect_file_info(file_path_or_url: str) -> Tuple[str, List[str], str, TaskType]:
    """
    Detect category, compatible target formats, default format, and TaskType.
    Returns (category, compatible_formats, default_format, task_type).
    """
    if "youtube.com" in file_path_or_url or "youtu.be" in file_path_or_url:
        return (
            "YouTube",
            ["MP3", "MP4", "WAV", "FLAC", "M4A", "MOV"],
            "MP3",
            TaskType.YOUTUBE,
        )

    ext = get_file_extension(file_path_or_url)
    if ext in FORMAT_RULES:
        return FORMAT_RULES[ext]

    # Fallback for unrecognized file types
    return ("Datei", ["TXT"], "TXT", TaskType.DOCUMENT)


def is_valid_conversion(source_path: str, target_format: str) -> bool:
    """Strict validation whether a conversion from source to target is permitted."""
    _, allowed, _, _ = detect_file_info(source_path)
    return target_format.upper() in [fmt.upper() for fmt in allowed]


def get_quality_presets(target_format: str) -> List[str]:
    """Return available quality/bitrate presets for the selected target format."""
    fmt = target_format.upper()
    
    # Audio bitrates
    if fmt == "MP3":
        return ["320k (Hohe Qualität)", "256k", "192k", "128k"]
    if fmt in ["AAC", "M4A"]:
        return ["256k (Standard)", "320k", "192k", "128k"]
    if fmt in ["OGG", "OPUS"]:
        return ["192k (Standard)", "256k", "128k"]
    if fmt in ["WAV", "FLAC", "AIFF"]:
        return ["Lossless (Verlustfrei)"]

    # Video presets
    if fmt in ["MP4", "MOV", "MKV", "WEBM", "AVI"]:
        return ["Original", "1080p Full HD", "720p HD", "480p"]
    if fmt == "GIF":
        return ["Standard (15 fps)", "High Quality (30 fps)"]

    # Image presets
    if fmt in ["JPEG", "JPG"]:
        return ["Sehr hoch (95%)", "Maximum (100%)", "Hoch (85%)", "Mittel (75%)"]
    if fmt == "HEIC":
        return ["Sehr hoch (95%)", "Maximum (100%)", "Hoch (85%)"]
    if fmt == "WEBP":
        return ["Sehr hoch (95%)", "Lossless (Verlustfrei)", "Hoch (85%)"]
    if fmt in ["PNG", "TIFF", "BMP"]:
        return ["Lossless (Verlustfrei)"]
    if fmt == "ICO":
        return ["Multi-Size (16 bis 256)"]

    # Document & Tables
    return ["Standard"]
