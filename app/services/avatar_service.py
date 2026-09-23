# app/services/avatar_service.py
import io
import os
import uuid
from typing import Optional

from flask import current_app, url_for
from werkzeug.datastructures import FileStorage

from app.i18n import gettext as _

MAX_AVATAR_BYTES = 2 * 1024 * 1024   # what is stored; bigger uploads are shrunk in save()
AVATAR_SIDE = 512                     # px; shown at most ~120px, so this stays sharp on hi-DPI screens
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
        """Return an error message, or None when the upload is an acceptable image.
        Large photos are accepted and shrunk in save(); the request as a whole is capped by MAX_CONTENT_LENGTH."""
        head = file.stream.read(12)
        file.stream.seek(0)
        if detect_image_type(head) is None:
            return _("ឯកសារនេះមិនមែនជារូបភាព JPG, PNG ឬ WebP ត្រឹមត្រូវទេ។")
        return None

    @staticmethod
    def _shrink(data: bytes) -> Optional[bytes]:
        """Downscale to AVATAR_SIDE and re-encode as JPEG, or None if Pillow can't read it."""
        try:
            from PIL import Image, ImageOps

            img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))  # phone photos carry rotation in EXIF
            img.thumbnail((AVATAR_SIDE, AVATAR_SIDE))
            if img.mode != "RGB":
                # JPEG has no alpha channel — flatten transparency onto white.
                rgba = img.convert("RGBA")
                img = Image.new("RGB", rgba.size, (255, 255, 255))
                img.paste(rgba, mask=rgba.split()[-1])
            out = io.BytesIO()
            img.save(out, "JPEG", quality=85, optimize=True)
            return out.getvalue()
        except Exception:
            current_app.logger.exception("Could not shrink avatar")
            return None

    @staticmethod
    def save(file: FileStorage) -> str:
        """Store a validated upload under a random name and return the filename."""
        data = file.stream.read()
        file.stream.seek(0)
        ext = detect_image_type(data[:12])
        if len(data) > MAX_AVATAR_BYTES:
            shrunk = AvatarService._shrink(data)
            if shrunk is not None:  # else keep the original; it is still within MAX_CONTENT_LENGTH
                data, ext = shrunk, "jpg"
        os.makedirs(AvatarService._folder(), exist_ok=True)
        filename = f"{uuid.uuid4().hex}.{ext}"
        with open(os.path.join(AvatarService._folder(), filename), "wb") as fh:
            fh.write(data)
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
