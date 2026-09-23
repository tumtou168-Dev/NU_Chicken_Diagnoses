# app/routes/chat_routes.py
from flask import Blueprint, jsonify, request, abort, redirect, url_for, flash
from flask_login import login_required, current_user

from app.i18n import gettext as _, data_text
from app.services.chat_service import ChatService
from app.services.chat_image_service import ChatImageService
from app.services.chat_audio_service import ChatAudioService
from app.services.avatar_service import AvatarService
from app.services.expert_system_service import CaseService
from app.models.user import UserTable
from extensions import db

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


def _role_label(user: UserTable) -> str:
    role = next((r.name for r in user.roles if r.name in ("Admin", "Doctor")), None)
    return data_text(role) if role else ""


def _thread_user_id() -> int:
    """The normal-user side of the conversation this request is about.

    A normal user only ever sees their own thread. Staff (Admin/Doctor) pass
    ?user_id=<id> to pick which conversation they're viewing.
    """
    if not ChatService.is_staff(current_user):
        return current_user.id
    user_id = request.values.get("user_id", type=int)
    if not user_id:
        abort(400)
    return user_id


def _serialize(message) -> dict:
    is_mine = message.sender_id == current_user.id
    data = {
        "id": message.id,
        "sender_id": message.sender_id,
        "body": ChatService.display_body(message),
        "is_from_staff": message.is_from_staff,
        "is_mine": is_mine,
        "sender_name": message.sender.full_name,
        "sender_avatar_url": AvatarService.url(message.sender),
        "sender_role": _role_label(message.sender) if message.is_from_staff else "",
        "created_at": message.created_at.strftime("%Y-%m-%d %I:%M %p"),
        "is_deleted": message.is_deleted,
        "is_edited": message.edited_at is not None,
        "can_delete": ChatService.can_delete(message, current_user) and not message.is_deleted,
        "can_edit": is_mine and message.is_editable,
    }
    if message.is_deleted:
        return data
    if message.is_audio:
        data["audio_url"] = ChatAudioService.url(message.audio)
        data["audio_duration"] = message.audio_duration
    if message.is_image:
        data["image_url"] = ChatImageService.url(message.image)
        data["caption"] = message.caption or ""
    if message.is_contact_request:
        data["contact_request"] = {
            "case_id": message.case_id,
            "flock_size": message.flock_size,
            "flock_age_weeks": message.flock_age_weeks,
            "vaccinated_count": message.vaccinated_count,
            "death_count": message.death_count,
            "image_url": ChatImageService.url(message.image),
        }
    return data


@chat_bp.route("/api/messages")
@login_required
def messages():
    thread_user_id = _thread_user_id()
    is_staff = ChatService.is_staff(current_user)
    ChatService.mark_read(thread_user_id, as_staff=is_staff)
    items = [_serialize(m) for m in ChatService.thread_messages(thread_user_id, current_user)]
    # The other side's presence for the header dot: the farmer for staff, "any doctor" for a farmer.
    if is_staff:
        peer = db.session.get(UserTable, thread_user_id)
        peer_online = bool(peer and peer.is_online)
    else:
        peer_online = ChatService.any_staff_online()
    return jsonify({"messages": items, "peer_online": peer_online})


@chat_bp.route("/api/send", methods=["POST"])
@login_required
def send():
    thread_user_id = _thread_user_id()
    body = (request.form.get("body") or "").strip()
    if not body:
        return jsonify({"error": "empty"}), 400
    message = ChatService.send(thread_user_id, current_user, body)
    return jsonify({"message": _serialize(message)})


@chat_bp.route("/api/send-audio", methods=["POST"])
@login_required
def send_audio():
    thread_user_id = _thread_user_id()
    file = request.files.get("audio")
    if not file or not file.filename:
        return jsonify({"error": "empty"}), 400

    error = ChatAudioService.validate(file)
    if error:
        return jsonify({"error": error}), 400

    duration = request.form.get("duration", type=int)
    filename = ChatAudioService.save(file)
    message = ChatService.send_audio(thread_user_id, current_user, filename, duration)
    return jsonify({"message": _serialize(message)})


@chat_bp.route("/api/send-image", methods=["POST"])
@login_required
def send_image():
    thread_user_id = _thread_user_id()
    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify({"error": "empty"}), 400

    error = ChatImageService.validate(file)
    if error:
        return jsonify({"error": error}), 400

    filename = ChatImageService.save(file)
    message = ChatService.send_image(thread_user_id, current_user, filename, request.form.get("caption", ""))
    return jsonify({"message": _serialize(message)})


@chat_bp.route("/api/edit", methods=["POST"])
@login_required
def edit():
    message_id = request.form.get("message_id", type=int)
    body = (request.form.get("body") or "").strip()
    if not message_id or not body:
        return jsonify({"error": "empty"}), 400
    try:
        message = ChatService.edit(message_id, current_user, body)
    except LookupError:
        abort(404)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"message": _serialize(message)})


@chat_bp.route("/api/delete", methods=["POST"])
@login_required
def delete():
    """scope=me hides the message from the current user only; scope=everyone (the default)
    replaces it with a "message deleted" placeholder for every participant."""
    message_id = request.form.get("message_id", type=int)
    scope = request.form.get("scope", "everyone")
    if not message_id or scope not in ("me", "everyone"):
        return jsonify({"error": "empty"}), 400
    try:
        if scope == "me":
            ChatService.delete_for_me(message_id, current_user)
            return jsonify({"hidden": message_id})
        message = ChatService.delete(message_id, current_user)
    except LookupError:
        abort(404)
    return jsonify({"message": _serialize(message)})


@chat_bp.route("/api/unread-count")
@login_required
def unread_count():
    if ChatService.is_staff(current_user):
        count = ChatService.unread_count_for_staff()
    else:
        count = ChatService.unread_count_for_user(current_user.id)
    return jsonify({"count": count})


@chat_bp.route("/api/threads")
@login_required
def threads():
    if not ChatService.is_staff(current_user):
        abort(403)
    rows = ChatService.staff_threads(current_user)
    return jsonify({"threads": [
        {
            "user_id": row["user"].id,
            "full_name": row["user"].full_name,
            "avatar_url": AvatarService.url(row["user"]),
            "last_message": row["last_message_preview"],
            "last_at": row["last_message"].created_at.strftime("%Y-%m-%d %I:%M %p"),
            "unread_count": row["unread_count"],
            "is_online": row["user"].is_online,
        }
        for row in rows
    ]})


@chat_bp.route("/contact-doctor", methods=["POST"])
@login_required
def contact_doctor():
    if ChatService.is_staff(current_user):
        abort(403)

    case_id = request.form.get("case_id", type=int)
    case = CaseService.get_by_id(case_id) if case_id else None
    if not case or case.user_id != current_user.id:
        abort(404)

    redirect_url = url_for("expert_system.cases_detail", case_id=case.id)

    def back(message, category):
        flash(message, category)
        return redirect(redirect_url)

    flock_size = request.form.get("flock_size", type=int)
    flock_age_weeks = request.form.get("flock_age_weeks", type=int)
    vaccinated_count = request.form.get("vaccinated_count", type=int)
    death_count = request.form.get("death_count", type=int)
    note = request.form.get("note", "")

    if flock_size is None or flock_size < 0 or flock_age_weeks is None or flock_age_weeks < 0 \
            or vaccinated_count is None or vaccinated_count < 0 or death_count is None or death_count < 0:
        return back(_("សូមបំពេញចំនួនមាន់ អាយុ ចំនួនចាក់វ៉ាក់សាំង និងចំនួនស្លាប់ជាលេខត្រឹមត្រូវ។"), "warning")
    if vaccinated_count > flock_size or death_count > flock_size:
        return back(_("ចំនួនចាក់វ៉ាក់សាំង ឬស្លាប់ មិនអាចលើសពីចំនួនមាន់សរុបបានទេ។"), "warning")

    image_filename = None
    file = request.files.get("image")
    if file and file.filename:
        error = ChatImageService.validate(file)
        if error:
            return back(error, "danger")
        image_filename = ChatImageService.save(file)

    ChatService.send_contact_request(
        current_user,
        case_id=case.id,
        flock_size=flock_size,
        flock_age_weeks=flock_age_weeks,
        vaccinated_count=vaccinated_count,
        death_count=death_count,
        image=image_filename,
        note=note,
    )
    flash(_("បានផ្ញើសំណើទៅកាន់ពេទ្យសត្វរួចរាល់។ សូមរង់ចាំការឆ្លើយតបនៅក្នុងប្រអប់ជជែក។"), "success")
    return redirect(f"{redirect_url}?open_chat=1")
