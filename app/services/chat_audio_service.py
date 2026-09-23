# app/services/chat_audio_service.py
import os
import uuid
from typing import Optional

from flask import current_app, url_for
from werkzeug.datastructures import FileStorage

from app.i18n import gettext as _

MAX_CHAT_AUDIO_BYTES = 5 * 1024 * 1024
MAX_CHAT_AUDIO_SECONDS = 120


def detect_audio_type(header: bytes) -> Optional[str]:
    """Sniff the container format from the first bytes, mirroring detect_image_type."""
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm"
    if header.startswith(b"OggS"):
        return "ogg"
    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "wav"
    if header[4:8] == b"ftyp":
        return "m4a"
    if header.startswith(b"ID3") or (len(header) > 1 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0):
        return "mp3"
    return None


class ChatAudioService:
    """A voice message recorded in the chat widget. Mirrors ChatImageService's
    signature-based validation, stored separately under uploads/chat_audio."""

    @staticmethod
    def _folder() -> str:
        return os.path.join(current_app.static_folder, "uploads", "chat_audio")

    @staticmethod
    def url(filename: Optional[str]) -> Optional[str]:
        if not filename:
            return None
        return url_for("static", filename=f"uploads/chat_audio/{filename}")

    @staticmethod
    def validate(file: FileStorage) -> Optional[str]:
        """Return an error message, or None when the upload is an acceptable audio clip."""
        data = file.stream.read(MAX_CHAT_AUDIO_BYTES + 1)
        file.stream.seek(0)
        if len(data) > MAX_CHAT_AUDIO_BYTES:
            return _("សារជាសំឡេងត្រូវមានទំហំ 5MB ឬតូចជាងនេះ។")
        if detect_audio_type(data[:12]) is None:
            return _("ឯកសារនេះមិនមែនជាសំឡេងត្រឹមត្រូវទេ។")
        return None

    @staticmethod
    def save(file: FileStorage) -> str:
        ext = detect_audio_type(file.stream.read(12))
        file.stream.seek(0)
        os.makedirs(ChatAudioService._folder(), exist_ok=True)
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(ChatAudioService._folder(), filename))
        return filename

    @staticmethod
    def delete(filename: Optional[str]) -> None:
        if not filename:
            return
        path = os.path.join(ChatAudioService._folder(), os.path.basename(filename))
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
