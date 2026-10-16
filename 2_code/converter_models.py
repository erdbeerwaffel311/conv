"""Data structures and enums for conversion tasks."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import os


class TaskType(Enum):
    LOCAL_FILE = "LOCAL_FILE"
    YOUTUBE = "YOUTUBE"
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"


class TaskStatus(Enum):
    PENDING = "Wartend"
    RUNNING = "Läuft"
    SUCCESS = "Abgeschlossen"
    FAILED = "Fehlgeschlagen"
    CANCELLED = "Abgebrochen"


@dataclass
class ConversionItem:
    task_id: str
    task_type: TaskType
    source: str  # File path or URL
    target_format: str  # e.g. "MP3", "MP4", "WAV", "MOV", "PNG", "DOCX"
    quality: str  # e.g. "320k", "1080p", "Sehr hoch (95%)", "Standard"
    output_dir: str
    output_file: Optional[str] = None
    title: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    status_text: str = "Wartend"
    embed_thumbnail: bool = True
    error_message: Optional[str] = None

    def display_source(self) -> str:
        if self.task_type in (TaskType.LOCAL_FILE, TaskType.IMAGE, TaskType.DOCUMENT):
            return os.path.basename(self.source)
        return self.title if self.title else self.source
