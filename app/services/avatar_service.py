# app/services/avatar_service.py
import os
import uuid
from typing import Optional

from flask import current_app, url_for
from werkzeug.datastructures import FileStorage

from app.i18n import gettext as _

MAX_AVATAR_BYTES = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png", "webp")


def detect_image_type(head: bytes) -> Optional[str]:
    """Identify the real image format from its signature (never trust the filename)."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


class AvatarService:
    @staticmethod
    def _folder() -> str:
        return os.path.join(current_app.static_folder, "uploads", "avatars")

    @staticmethod
    def url(user) -> Optional[str]:
        """Public URL of a user's picture, or None when they have not uploaded one."""
        filename = getattr(user, "avatar", None)
        if not filename:
            return None
        return url_for("static", filename=f"uploads/avatars/{filename}")

    @staticmethod
    def validate(file: FileStorage) -> Optional[str]:
        """Return an error message, or None when the upload is an acceptable image."""
        data = file.stream.read(MAX_AVATAR_BYTES + 1)
        file.stream.seek(0)
        if len(data) > MAX_AVATAR_BYTES:
            return _("រូបភាពត្រូវមានទំហំ 2MB ឬតូចជាងនេះ។")
        if detect_image_type(data[:12]) is None:
            return _("ឯកសារនេះមិនមែនជារូបភាព JPG, PNG ឬ WebP ត្រឹមត្រូវទេ។")
        return None

    @staticmethod
    def save(file: FileStorage) -> str:
        """Store a validated upload under a random name and return the filename."""
        ext = detect_image_type(file.stream.read(12))
        file.stream.seek(0)
        os.makedirs(AvatarService._folder(), exist_ok=True)
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(AvatarService._folder(), filename))
        return filename

    @staticmethod
    def delete(filename: Optional[str]) -> None:
        if not filename:
            return
        path = os.path.join(AvatarService._folder(), os.path.basename(filename))
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
