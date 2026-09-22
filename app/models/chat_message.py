# app/models/chat_message.py
from datetime import datetime
from extensions import db


class ChatMessage(db.Model):
    """One message in a support conversation between a normal user and staff (Admin/Doctor).

    Every message in a conversation shares the same thread_user_id (the normal user side),
    regardless of which staff member replied — staff share one inbox per user.
    """
    __tablename__ = "tbl_chat_messages"

    id = db.Column(db.Integer, db.Sequence("seq_chat_messages_id"), primary_key=True)
    thread_user_id = db.Column(db.Integer, db.ForeignKey("tbl_users.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("tbl_users.id"), nullable=False)
    is_from_staff = db.Column(db.Boolean, default=False, nullable=False)
    body = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    read_by_user = db.Column(db.Boolean, default=False, nullable=False)
    read_by_staff = db.Column(db.Boolean, default=False, nullable=False)

    # Set only on a "contact the doctor" request raised from a diagnosis result.
    case_id = db.Column(db.Integer, db.ForeignKey("tbl_cases.id"), nullable=True)
    flock_size = db.Column(db.Integer, nullable=True)
    flock_age_weeks = db.Column(db.Integer, nullable=True)
    vaccinated_count = db.Column(db.Integer, nullable=True)
    death_count = db.Column(db.Integer, nullable=True)
    image = db.Column(db.String(255), nullable=True)  # filename under static/uploads/chat

    thread_user = db.relationship("UserTable", foreign_keys=[thread_user_id])
    sender = db.relationship("UserTable", foreign_keys=[sender_id])
    case = db.relationship("Case")

    @property
    def is_contact_request(self) -> bool:
        return self.flock_size is not None

    def __repr__(self) -> str:
        return f"<ChatMessage thread={self.thread_user_id} from={self.sender_id}>"
