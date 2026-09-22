# app/routes/chat_routes.py
from flask import Blueprint, jsonify, request, abort, redirect, url_for, flash
from flask_login import login_required, current_user

from app.i18n import gettext as _, data_text
from app.services.chat_service import ChatService
from app.services.chat_image_service import ChatImageService
from app.services.avatar_service import AvatarService
from app.services.expert_system_service import CaseService
from app.models.user import UserTable

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
    data = {
        "id": message.id,
        "body": message.body,
        "is_from_staff": message.is_from_staff,
        "is_mine": message.sender_id == current_user.id,
        "sender_name": message.sender.full_name,
        "sender_avatar_url": AvatarService.url(message.sender),
        "sender_role": _role_label(message.sender) if message.is_from_staff else "",
        "created_at": message.created_at.strftime("%Y-%m-%d %H:%M"),
    }
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
    items = [_serialize(m) for m in ChatService.thread_messages(thread_user_id)]
    return jsonify({"messages": items})


@chat_bp.route("/api/send", methods=["POST"])
@login_required
def send():
    thread_user_id = _thread_user_id()
    body = (request.form.get("body") or "").strip()
    if not body:
        return jsonify({"error": "empty"}), 400
    message = ChatService.send(thread_user_id, current_user, body)
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
    rows = ChatService.staff_threads()
    return jsonify({"threads": [
        {
            "user_id": row["user"].id,
            "full_name": row["user"].full_name,
            "avatar_url": AvatarService.url(row["user"]),
            "last_message": row["last_message"].body,
            "last_at": row["last_message"].created_at.strftime("%Y-%m-%d %H:%M"),
            "unread_count": row["unread_count"],
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
