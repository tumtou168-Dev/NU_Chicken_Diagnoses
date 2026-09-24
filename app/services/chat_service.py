# app/services/chat_service.py
from extensions import db
from app.i18n import gettext as _
from app.models.chat_message import ChatMessage, ChatMessageHidden
from app.models.user import UserTable
from utils.timezone import now_kh


class ChatService:
    """Support chat between a normal ('User' role) account and staff (Admin/Doctor), plus
    direct messages between staff.

    Every normal user has exactly one support conversation, keyed by their own user id
    (thread_user_id). Staff share a single inbox: any Admin/Doctor can read and
    reply to any thread, and a reply marks the thread read for all staff.

    A direct staff message has recipient_id instead of thread_user_id: private to its two
    staff members, with its own read flag (read_by_recipient). Its read_by_user/read_by_staff
    are set True so the support-thread queries never count it.
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

    @classmethod
    def can_delete(cls, message: ChatMessage, user: UserTable) -> bool:
        """Delete for everyone: the sender, or an Admin moderating a support thread.
        A direct staff message can only be deleted by its sender."""
        if message.is_direct:
            return message.sender_id == user.id
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
        if message.is_direct:
            return user.id in (message.sender_id, message.recipient_id)
        return message.thread_user_id == user.id or message.sender_id == user.id or cls.is_staff(user)

    @classmethod
    def direct_peer(cls, viewer: UserTable, peer_id: int) -> UserTable:
        """The staff member `viewer` may message directly — another active Admin/Doctor."""
        peer = db.session.get(UserTable, peer_id)
        if not peer or peer.id == viewer.id or not peer.is_active or not cls.is_staff(peer) or not cls.is_staff(viewer):
            raise LookupError("no such staff member")
        return peer

    @classmethod
    def thread_messages(cls, thread_user_id: int, viewer: UserTable | None = None, limit: int = 200) -> list[ChatMessage]:
        """Messages in a thread, oldest first. With a viewer, the ones they deleted "for me" are left out."""
        query = db.select(ChatMessage).filter_by(thread_user_id=thread_user_id)
        if viewer is not None:
            hidden = db.select(ChatMessageHidden.message_id).where(ChatMessageHidden.user_id == viewer.id)
            query = query.where(ChatMessage.id.not_in(hidden))
        return db.session.scalars(query.order_by(ChatMessage.created_at.asc()).limit(limit)).all()

    @classmethod
    def _create(cls, sender: UserTable, thread_user_id: int | None, recipient_id: int | None, **fields) -> ChatMessage:
        """Save a message into a support thread (thread_user_id) or as a direct staff message (recipient_id)."""
        if recipient_id is not None:
            cls.direct_peer(sender, recipient_id)
            flags = dict(thread_user_id=None, recipient_id=recipient_id, is_from_staff=True,
                         read_by_user=True, read_by_staff=True, read_by_recipient=False)
        else:
            is_staff = cls.is_staff(sender)
            flags = dict(thread_user_id=thread_user_id, is_from_staff=is_staff,
                         read_by_user=not is_staff, read_by_staff=is_staff)
        message = ChatMessage(sender_id=sender.id, **flags, **fields)
        db.session.add(message)
        db.session.commit()
        return message

    @classmethod
    def send(cls, thread_user_id: int | None, sender: UserTable, body: str, recipient_id: int | None = None) -> ChatMessage:
        body = body.strip()
        if not body:
            raise ValueError("empty message")
        return cls._create(sender, thread_user_id, recipient_id, body=body[:1000])

    @classmethod
    def send_audio(cls, thread_user_id: int | None, sender: UserTable, audio: str, duration: int | None,
                   recipient_id: int | None = None) -> ChatMessage:
        """A voice message recorded in the chat widget."""
        return cls._create(sender, thread_user_id, recipient_id, body=_("សារជាសំឡេង"), audio=audio, audio_duration=duration)

    @classmethod
    def send_image(cls, thread_user_id: int | None, sender: UserTable, image: str, caption: str = "",
                   recipient_id: int | None = None) -> ChatMessage:
        """A plain photo shared in the chat widget (not a contact-request card), with an optional caption."""
        return cls._create(sender, thread_user_id, recipient_id, body=_("រូបភាព"), image=image,
                           caption=caption.strip()[:1000] or None)

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
        if not message or not cls.can_view(message, editor) or not cls.can_delete(message, editor):
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

    @staticmethod
    def is_seen(message: ChatMessage) -> bool:
        """Whether the other side has opened the conversation since this message was sent.
        Sending sets the sender's own flag (see _create), so it is the other side's flag that counts:
        a direct message's recipient, the user for a staff reply, any staff member for a user's message."""
        if message.is_direct:
            return message.read_by_recipient
        return message.read_by_user if message.is_from_staff else message.read_by_staff

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
    def latest_unread(cls, viewer: UserTable) -> ChatMessage | None:
        """The newest message this viewer hasn't read yet (and hasn't deleted "for me") — drives
        the new-message notification. Staff: any support thread plus their own direct messages;
        a user: only their own thread."""
        query = db.select(ChatMessage).where(ChatMessage.sender_id != viewer.id)
        if cls.is_staff(viewer):
            query = query.where(db.or_(
                db.and_(ChatMessage.thread_user_id.is_not(None), ChatMessage.read_by_staff.is_(False)),
                db.and_(ChatMessage.recipient_id == viewer.id, ChatMessage.read_by_recipient.is_(False)),
            ))
        else:
            query = query.where(ChatMessage.thread_user_id == viewer.id, ChatMessage.read_by_user.is_(False))
        hidden = db.select(ChatMessageHidden.message_id).where(ChatMessageHidden.user_id == viewer.id)
        query = query.where(ChatMessage.id.not_in(hidden))
        return db.session.scalars(query.order_by(ChatMessage.id.desc()).limit(1)).first()

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

    # --- Direct staff messages -------------------------------------------------------------

    @classmethod
    def _direct_query(cls, a_id: int, b_id: int):
        return db.select(ChatMessage).where(db.or_(
            db.and_(ChatMessage.sender_id == a_id, ChatMessage.recipient_id == b_id),
            db.and_(ChatMessage.sender_id == b_id, ChatMessage.recipient_id == a_id),
        ))

    @classmethod
    def direct_messages(cls, viewer: UserTable, peer_id: int, limit: int = 200) -> list[ChatMessage]:
        """The conversation between two staff members, oldest first, minus what the viewer deleted "for me"."""
        hidden = db.select(ChatMessageHidden.message_id).where(ChatMessageHidden.user_id == viewer.id)
        query = cls._direct_query(viewer.id, peer_id).where(ChatMessage.id.not_in(hidden))
        return db.session.scalars(query.order_by(ChatMessage.created_at.asc()).limit(limit)).all()

    @classmethod
    def mark_direct_read(cls, viewer: UserTable, peer_id: int) -> None:
        db.session.execute(
            db.update(ChatMessage)
            .where(ChatMessage.sender_id == peer_id, ChatMessage.recipient_id == viewer.id,
                   ChatMessage.read_by_recipient.is_(False))
            .values(read_by_recipient=True)
        )
        db.session.commit()

    @classmethod
    def unread_direct_count(cls, viewer: UserTable) -> int:
        return db.session.scalar(
            db.select(db.func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.recipient_id == viewer.id, ChatMessage.read_by_recipient.is_(False))
        ) or 0

    @classmethod
    def team_threads(cls, viewer: UserTable) -> list[dict]:
        """Every other active Admin/Doctor, for the inbox's Team tab: people with a conversation
        first (newest activity first), then everyone else by name."""
        staff = [u for u in db.session.scalars(db.select(UserTable).where(UserTable.is_active.is_(True), UserTable.id != viewer.id)).all()
                 if cls.is_staff(u)]
        rows = []
        for user in staff:
            messages = cls.direct_messages(viewer, user.id)
            last = messages[-1] if messages else None
            rows.append({
                "user": user,
                "last_message": last,
                "last_message_preview": cls.display_body(last) if last else "",
                "unread_count": sum(1 for m in messages if m.recipient_id == viewer.id and not m.read_by_recipient),
            })
        rows.sort(key=lambda r: (r["last_message"] is None,
                                 -(r["last_message"].created_at.timestamp()) if r["last_message"] else 0,
                                 r["user"].full_name.lower()))
        return rows
