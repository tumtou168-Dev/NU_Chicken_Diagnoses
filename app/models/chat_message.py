# app/models/chat_message.py
from utils.timezone import now_kh
from extensions import db


class ChatMessage(db.Model):
    """One chat message. Two kinds of conversation share this table:

    - Support thread (thread_user_id set): a normal user and staff (Admin/Doctor). Every message
      in it shares the normal user's id, whichever staff member replied — staff share one inbox.
    - Direct staff message (recipient_id set, thread_user_id NULL): one Admin/Doctor to another,
      private to the two of them, with its own read flag.
    """
    __tablename__ = "tbl_chat_messages"

    id = db.Column(db.Integer, db.Sequence("seq_chat_messages_id"), primary_key=True)
    thread_user_id = db.Column(db.Integer, db.ForeignKey("tbl_users.id"), nullable=True, index=True)   # NULL for a direct staff message
    sender_id = db.Column(db.Integer, db.ForeignKey("tbl_users.id"), nullable=False)
    is_from_staff = db.Column(db.Boolean, default=False, nullable=False)
    body = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False, index=True)
    read_by_user = db.Column(db.Boolean, default=False, nullable=False)
    read_by_staff = db.Column(db.Boolean, default=False, nullable=False)

    # Set only on a "contact the doctor" request raised from a diagnosis result.
    case_id = db.Column(db.Integer, db.ForeignKey("tbl_cases.id"), nullable=True)
    flock_size = db.Column(db.Integer, nullable=True)
    flock_age_weeks = db.Column(db.Integer, nullable=True)
    vaccinated_count = db.Column(db.Integer, nullable=True)
    death_count = db.Column(db.Integer, nullable=True)
    image = db.Column(db.String(255), nullable=True)  # filename under static/uploads/chat
    caption = db.Column(db.String(1000), nullable=True)  # optional text under a plain image message

    # Set only on a voice message recorded in the chat widget.
    audio = db.Column(db.String(255), nullable=True)  # filename under static/uploads/chat_audio
    audio_duration = db.Column(db.Integer, nullable=True)  # seconds, rounded

    # Set only on a direct staff-to-staff message.
    recipient_id = db.Column(db.Integer, db.ForeignKey("tbl_users.id"), nullable=True, index=True)
    read_by_recipient = db.Column(db.Boolean, default=False, nullable=False)

    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    edited_at = db.Column(db.DateTime, nullable=True)

    thread_user = db.relationship("UserTable", foreign_keys=[thread_user_id])
    sender = db.relationship("UserTable", foreign_keys=[sender_id])
    recipient = db.relationship("UserTable", foreign_keys=[recipient_id])
    case = db.relationship("Case")

    @property
    def is_direct(self) -> bool:
        return self.recipient_id is not None

    @property
    def is_contact_request(self) -> bool:
        return self.flock_size is not None

    @property
    def is_audio(self) -> bool:
        return self.audio is not None

    @property
    def is_image(self) -> bool:
        """A plain image message — same `image` column as a contact request, but
        without the flock fields that mark it as one."""
        return self.image is not None and not self.is_contact_request

    @property
    def is_editable(self) -> bool:
        """Only a plain text message can be edited — not audio, an image, or a contact request."""
        return not self.is_deleted and not self.is_audio and not self.is_image and not self.is_contact_request

    def __repr__(self) -> str:
        return f"<ChatMessage thread={self.thread_user_id} from={self.sender_id}>"


class ChatMessageHidden(db.Model):
    """A "delete for me" — hides one message from one user's view only; everyone else still sees it."""
    __tablename__ = "tbl_chat_message_hidden"

    message_id = db.Column(db.Integer, db.ForeignKey("tbl_chat_messages.id", ondelete="CASCADE"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("tbl_users.id", ondelete="CASCADE"), primary_key=True)
    hidden_at = db.Column(db.DateTime, default=now_kh, nullable=False)
