# app/services/file_store.py
import os
from typing import Optional

from flask import current_app, url_for

from extensions import db
from app.models.stored_file import StoredFile

FOLDERS = ("avatars", "chat", "chat_audio")

# Every type the upload services accept (they check the real format, then name the file by it).
CONTENT_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
    "webm": "audio/webm", "ogg": "audio/ogg", "wav": "audio/wav", "m4a": "audio/mp4", "mp3": "audio/mpeg",
}


def _key(folder: str, filename: str) -> str:
    return f"{folder}/{os.path.basename(filename)}"


def save(folder: str, filename: str, data: bytes) -> None:
    """Store an upload in the database (see StoredFile for why not on disk)."""
    content_type = CONTENT_TYPES.get(filename.rsplit(".", 1)[-1].lower(), "application/octet-stream")
    db.session.merge(StoredFile(key=_key(folder, filename), content_type=content_type, data=data))
    db.session.commit()


def delete(folder: str, filename: Optional[str]) -> None:
    if not filename:
        return
    StoredFile.query.filter_by(key=_key(folder, filename)).delete()
    db.session.commit()
    # Uploads from before files moved into the database may still be on disk.
    try:
        os.remove(os.path.join(current_app.static_folder, "uploads", folder, os.path.basename(filename)))
    except FileNotFoundError:
        pass


def url(folder: str, filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    return url_for("media.serve", folder=folder, filename=filename)
