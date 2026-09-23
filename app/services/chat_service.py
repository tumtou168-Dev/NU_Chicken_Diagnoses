# app/services/chat_service.py
from extensions import db
from app.i18n import gettext as _
from app.models.chat_message import ChatMessage, ChatMessageHidden
from app.models.user import UserTable
from utils.timezone import now_kh


class ChatService:
    """Support chat between a normal ('User' role) account and staff (Admin/Doctor).

    Every normal user has exactly one conversation, keyed by their own user id
    (thread_user_id). Staff share a single inbox: any Admin/Doctor can read and
    reply to any thread, and a reply marks the thread read for all staff.
    """

    @staticmethod
    def is_staff(user: UserTable) -> bool:
        return user.has_role("Admin") or user.has_role("Doctor")

    @classmethod
    def any_staff_online(cls) -> bool:
        """Whether a doctor/admin is around — shown to a normal user in the chat header."""
        cutoff = now_kh() - UserTable.ONLINE_WINDOW
        recent = db.session.scalars(db.select(UserTable).where(UserTable.last_seen_at >= cutoff)).all()
        return any(cls.is_staff(u) for u in recent)

    @staticmethod
    def can_delete(message: ChatMessage, user: UserTable) -> bool:
        return message.sender_id == user.id or user.has_role("Admin")

    @staticmethod
    def display_body(message: ChatMessage) -> str:
        """The body text to show for a message — a deleted one is replaced with a placeholder."""
        if message.is_deleted:
            return _("សារនេះត្រូវបានលុប")
        if message.is_image and message.caption:
            return message.caption
        return message.body

    @classmethod
    def can_view(cls, message: ChatMessage, user: UserTable) -> bool:
        return message.thread_user_id == user.id or message.sender_id == user.id or cls.is_staff(user)

    @classmethod
    def thread_messages(cls, thread_user_id: int, viewer: UserTable | None = None, limit: int = 200) -> list[ChatMessage]:
        """Messages in a thread, oldest first. With a viewer, the ones they deleted "for me" are left out."""
        query = db.select(ChatMessage).filter_by(thread_user_id=thread_user_id)
        if viewer is not None:
            hidden = db.select(ChatMessageHidden.message_id).where(ChatMessageHidden.user_id == viewer.id)
            query = query.where(ChatMessage.id.not_in(hidden))
        return db.session.scalars(query.order_by(ChatMessage.created_at.asc()).limit(limit)).all()

    @classmethod
    def send(cls, thread_user_id: int, sender: UserTable, body: str) -> ChatMessage:
        body = body.strip()
        if not body:
            raise ValueError("empty message")
        is_staff = cls.is_staff(sender)
        message = ChatMessage(
            thread_user_id=thread_user_id,
            sender_id=sender.id,
            is_from_staff=is_staff,
            body=body[:1000],
            read_by_user=not is_staff,
            read_by_staff=is_staff,
        )
        db.session.add(message)
        db.session.commit()
        return message

    @classmethod
    def send_audio(cls, thread_user_id: int, sender: UserTable, audio: str, duration: int | None) -> ChatMessage:
        """A voice message recorded in the chat widget."""
        is_staff = cls.is_staff(sender)
        message = ChatMessage(
            thread_user_id=thread_user_id,
            sender_id=sender.id,
            is_from_staff=is_staff,
            body=_("សារជាសំឡេង"),
            read_by_user=not is_staff,
            read_by_staff=is_staff,
            audio=audio,
            audio_duration=duration,
        )
        db.session.add(message)
        db.session.commit()
        return message

    @classmethod
    def send_image(cls, thread_user_id: int, sender: UserTable, image: str, caption: str = "") -> ChatMessage:
        """A plain photo shared in the chat widget (not a contact-request card), with an optional caption."""
        is_staff = cls.is_staff(sender)
        message = ChatMessage(
            thread_user_id=thread_user_id,
            sender_id=sender.id,
            is_from_staff=is_staff,
            body=_("រូបភាព"),
            read_by_user=not is_staff,
            read_by_staff=is_staff,
            image=image,
            caption=caption.strip()[:1000] or None,
        )
        db.session.add(message)
        db.session.commit()
        return message

    @classmethod
    def send_contact_request(
        cls,
        user: UserTable,
        case_id: int,
        flock_size: int,
        flock_age_weeks: int,
        vaccinated_count: int,
        death_count: int,
        image: str | None,
        note: str = "",
    ) -> ChatMessage:
        """A structured "contact the doctor" message raised from a diagnosis result."""
        message = ChatMessage(
            thread_user_id=user.id,
            sender_id=user.id,
            is_from_staff=False,
            body=note.strip()[:1000] or "-",
            read_by_user=True,
            read_by_staff=False,
            case_id=case_id,
            flock_size=flock_size,
            flock_age_weeks=flock_age_weeks,
            vaccinated_count=vaccinated_count,
            death_count=death_count,
            image=image,
        )
        db.session.add(message)
        db.session.commit()
        return message

    @classmethod
    def edit(cls, message_id: int, editor: UserTable, body: str) -> ChatMessage:
        """Only the original sender may edit their own message, and only while it's
        still plain text (not a voice message or a contact-request card)."""
        message = db.session.get(ChatMessage, message_id)
        if not message or message.sender_id != editor.id:
            raise LookupError("message not found")
        if not message.is_editable:
            raise ValueError("not editable")
        body = body.strip()
        if not body:
            raise ValueError("empty message")
        message.body = body[:1000]
        message.edited_at = now_kh()
        db.session.commit()
        return message

    @classmethod
    def delete(cls, message_id: int, editor: UserTable) -> ChatMessage:
        """Delete for everyone. The original sender may delete their own message, and an Admin may delete any
        message (moderation). Soft-deleted so the conversation keeps its shape — the client
        renders a "message deleted" placeholder."""
        message = db.session.get(ChatMessage, message_id)
        if not message or not cls.can_delete(message, editor):
            raise LookupError("message not found")
        if message.is_deleted:
            return message
        message.is_deleted = True
        db.session.commit()
        return message

    @classmethod
    def delete_for_me(cls, message_id: int, user: UserTable) -> None:
        """Hide a message from this user's view only — anyone in the conversation may do this
        to any message, including one someone else sent or one already deleted for everyone."""
        message = db.session.get(ChatMessage, message_id)
        if not message or not cls.can_view(message, user):
            raise LookupError("message not found")
        if not db.session.get(ChatMessageHidden, (message_id, user.id)):
            db.session.add(ChatMessageHidden(message_id=message_id, user_id=user.id))
            db.session.commit()

    @classmethod
    def mark_read(cls, thread_user_id: int, as_staff: bool) -> None:
        column = ChatMessage.read_by_staff if as_staff else ChatMessage.read_by_user
        db.session.execute(
            db.update(ChatMessage)
            .where(ChatMessage.thread_user_id == thread_user_id, column.is_(False))
            .values(**{("read_by_staff" if as_staff else "read_by_user"): True})
        )
        db.session.commit()

    @classmethod
    def unread_count_for_user(cls, user_id: int) -> int:
        return db.session.scalar(
            db.select(db.func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.thread_user_id == user_id, ChatMessage.read_by_user.is_(False))
        ) or 0

    @classmethod
    def unread_count_for_staff(cls) -> int:
        return db.session.scalar(
            db.select(db.func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.read_by_staff.is_(False))
        ) or 0

    @classmethod
    def staff_threads(cls, viewer: UserTable) -> list[dict]:
        """One row per normal user who has ever exchanged a message, newest activity first.
        The preview skips messages the viewer deleted "for me"."""
        users = db.session.scalars(
            db.select(UserTable).join(ChatMessage, ChatMessage.thread_user_id == UserTable.id).distinct()
        ).all()

        rows = []
        for user in users:
            messages = cls.thread_messages(user.id, viewer)
            if not messages:
                continue
            last = messages[-1]
            unread = sum(1 for m in messages if not m.read_by_staff)
            rows.append({
                "user": user,
                "last_message": last,
                "last_message_preview": cls.display_body(last),
                "unread_count": unread,
            })
        rows.sort(key=lambda r: r["last_message"].created_at, reverse=True)
        return rows
