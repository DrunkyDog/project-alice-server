from enum import Enum
from typing import Union, Optional


class SentenceType(Enum):
    # Speaking phase
    FIRST = "FIRST"  # First sentence
    MIDDLE = "MIDDLE"  # Speaking
    LAST = "LAST"  # Last sentence


class ContentType(Enum):
    # Content type
    TEXT = "TEXT"  # Text content
    FILE = "FILE"  # File content
    ACTION = "ACTION"  # Action content


class InterfaceType(Enum):
    # Interface type
    DUAL_STREAM = "DUAL_STREAM"  # Dual stream
    SINGLE_STREAM = "SINGLE_STREAM"  # Single stream
    NON_STREAM = "NON_STREAM"  # Non-stream


class TTSMessageDTO:
    def __init__(
        self,
        sentence_id: str,
        # Speaking phase
        sentence_type: SentenceType,
        # Content type
        content_type: ContentType,
        # Content detail, generally the text to be converted or lyrics of audio
        content_detail: Optional[str] = None,
        # If content type is file, then file path is required
        content_file: Optional[str] = None,
    ):
        self.sentence_id = sentence_id
        self.sentence_type = sentence_type
        self.content_type = content_type
        self.content_detail = content_detail
        self.content_file = content_file
