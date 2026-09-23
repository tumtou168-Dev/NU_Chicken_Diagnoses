from utils.timezone import now_kh
from extensions import db

class AuditLog(db.Model):
    __tablename__ = "tbl_audit_logs"

    id = db.Column(db.Integer, db.Sequence('seq_audit_logs_id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("tbl_users.id"), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    target_type = db.Column(db.String(50), nullable=False) # User, Rule, Disease, etc.
    target_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True) # JSON or text description of changes
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)

    user = db.relationship("UserTable")

    def __repr__(self):
        return f"<AuditLog {self.action} {self.target_type} by {self.user_id}>"
