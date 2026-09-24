# app/services/chat_image_service.py
import io
import uuid
from typing import Optional

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.i18n import gettext as _
from app.services import file_store
from app.services.avatar_service import detect_image_type

MAX_CHAT_IMAGE_BYTES = 2 * 1024 * 1024
MAX_CHAT_IMAGE_SIDE = 1600


class ChatImageService:
    """Optional photo attached to a "contact the doctor" request. Mirrors AvatarService's
    signature-based validation, stored in the database under the "chat" folder."""

    @staticmethod
    def url(filename: Optional[str]) -> Optional[str]:
        return file_store.url("chat", filename)

    @staticmethod
    def validate(file: FileStorage) -> Optional[str]:
        """Return an error message, or None when the upload is an acceptable image.
        Photos over 2 MB are accepted and shrunk in save(); the request as a whole is
        already capped by MAX_CONTENT_LENGTH."""
        head = file.stream.read(12)
        file.stream.seek(0)
        if detect_image_type(head) is None:
            return _("ឯកសារនេះមិនមែនជារូបភាព JPG, PNG ឬ WebP ត្រឹមត្រូវទេ។")
        return None

    @staticmethod
    def _shrink(data: bytes) -> Optional[bytes]:
        """Downscale and re-encode a too-large photo as JPEG, or None if Pillow can't read it."""
        try:
            from PIL import Image, ImageOps

            img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
            img.thumbnail((MAX_CHAT_IMAGE_SIDE, MAX_CHAT_IMAGE_SIDE))
            if img.mode != "RGB":
                # JPEG has no alpha channel — flatten transparency onto white.
                rgba = img.convert("RGBA")
                img = Image.new("RGB", rgba.size, (255, 255, 255))
                img.paste(rgba, mask=rgba.split()[-1])
            for quality in (85, 70, 55):
                out = io.BytesIO()
                img.save(out, "JPEG", quality=quality, optimize=True)
                if out.tell() <= MAX_CHAT_IMAGE_BYTES:
                    break
            return out.getvalue()
        except Exception:
            current_app.logger.exception("Could not shrink chat image")
            return None

    @staticmethod
    def save(file: FileStorage) -> str:
        data = file.stream.read()
        file.stream.seek(0)
        ext = detect_image_type(data[:12])
        if len(data) > MAX_CHAT_IMAGE_BYTES:
            shrunk = ChatImageService._shrink(data)
            if shrunk is not None:
                data, ext = shrunk, "jpg"
        filename = f"{uuid.uuid4().hex}.{ext}"
        file_store.save("chat", filename, data)
        return filename

    @staticmethod
    def delete(filename: Optional[str]) -> None:
        file_store.delete("chat", filename)
