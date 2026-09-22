# app/services/chat_service.py
from extensions import db
from app.models.chat_message import ChatMessage
from app.models.user import UserTable


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
    def thread_messages(cls, thread_user_id: int, limit: int = 200) -> list[ChatMessage]:
        return (
            db.session.scalars(
                db.select(ChatMessage)
                .filter_by(thread_user_id=thread_user_id)
                .order_by(ChatMessage.created_at.asc())
                .limit(limit)
            )
            .all()
        )

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
    def staff_threads(cls) -> list[dict]:
        """One row per normal user who has ever exchanged a message, newest activity first."""
        users = db.session.scalars(
            db.select(UserTable).join(ChatMessage, ChatMessage.thread_user_id == UserTable.id).distinct()
        ).all()

        rows = []
        for user in users:
            messages = cls.thread_messages(user.id)
            if not messages:
                continue
            last = messages[-1]
            unread = sum(1 for m in messages if not m.read_by_staff)
            rows.append({
                "user": user,
                "last_message": last,
                "unread_count": unread,
            })
        rows.sort(key=lambda r: r["last_message"].created_at, reverse=True)
        return rows
