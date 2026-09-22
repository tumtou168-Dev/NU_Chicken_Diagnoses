# app/services/chat_image_service.py
import os
import uuid
from typing import Optional

from flask import current_app, url_for
from werkzeug.datastructures import FileStorage

from app.i18n import gettext as _
from app.services.avatar_service import detect_image_type

MAX_CHAT_IMAGE_BYTES = 2 * 1024 * 1024


class ChatImageService:
    """Optional photo attached to a "contact the doctor" request. Mirrors AvatarService's
    signature-based validation, stored separately under uploads/chat."""

    @staticmethod
    def _folder() -> str:
        return os.path.join(current_app.static_folder, "uploads", "chat")

    @staticmethod
    def url(filename: Optional[str]) -> Optional[str]:
        if not filename:
            return None
        return url_for("static", filename=f"uploads/chat/{filename}")

    @staticmethod
    def validate(file: FileStorage) -> Optional[str]:
        """Return an error message, or None when the upload is an acceptable image."""
        data = file.stream.read(MAX_CHAT_IMAGE_BYTES + 1)
        file.stream.seek(0)
        if len(data) > MAX_CHAT_IMAGE_BYTES:
            return _("រូបភាពត្រូវមានទំហំ 2MB ឬតូចជាងនេះ។")
        if detect_image_type(data[:12]) is None:
            return _("ឯកសារនេះមិនមែនជារូបភាព JPG, PNG ឬ WebP ត្រឹមត្រូវទេ។")
        return None

    @staticmethod
    def save(file: FileStorage) -> str:
        ext = detect_image_type(file.stream.read(12))
        file.stream.seek(0)
        os.makedirs(ChatImageService._folder(), exist_ok=True)
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(ChatImageService._folder(), filename))
        return filename
