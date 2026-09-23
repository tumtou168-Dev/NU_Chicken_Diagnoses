# app/models/expert_system.py
from utils.timezone import now_kh
from extensions import db
from app.models.associations import tbl_cases_symptoms, tbl_rules_symptoms
from app.models.bilingual import BilingualMixin


class Category(BilingualMixin, db.Model):
    __tablename__ = "tbl_categories"

    id = db.Column(db.Integer, db.Sequence('seq_categories_id'), primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    name_km = db.Column(db.String(120))
    description = db.Column(db.String(255))
    description_km = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)

    diseases = db.relationship("Disease", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class Symptom(BilingualMixin, db.Model):
    __tablename__ = "tbl_symptoms"

    id = db.Column(db.Integer, db.Sequence('seq_symptoms_id'), primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    name_km = db.Column(db.String(120))
    description = db.Column(db.String(255))
    description_km = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)

    cases = db.relationship(
        "Case",
        secondary=tbl_cases_symptoms,
        back_populates="symptoms",
    )
    rules = db.relationship(
        "Rule",
        secondary=tbl_rules_symptoms,
        back_populates="symptoms",
    )

    def __repr__(self) -> str:
        return f"<Symptom {self.name}>"


class Disease(BilingualMixin, db.Model):
    __tablename__ = "tbl_diseases"

    id = db.Column(db.Integer, db.Sequence('seq_diseases_id'), primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    name_km = db.Column(db.String(120))
    description = db.Column(db.String(255), nullable=False)
    description_km = db.Column(db.String(255))
    treatment = db.Column(db.String(255), nullable=False)
    treatment_km = db.Column(db.String(255))
    category_id = db.Column(db.Integer, db.ForeignKey("tbl_categories.id"))
    doctor_id = db.Column(db.Integer, db.ForeignKey("tbl_users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)

    category = db.relationship("Category", back_populates="diseases")
    doctor = db.relationship("UserTable", foreign_keys=[doctor_id])
    rules = db.relationship("Rule", back_populates="disease", cascade="all, delete-orphan")
    cases = db.relationship("Case", back_populates="disease")

    def __repr__(self) -> str:
        return f"<Disease {self.name}>"


class Rule(BilingualMixin, db.Model):
    __tablename__ = "tbl_rules"

    id = db.Column(db.Integer, db.Sequence('seq_rules_id'), primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    title_km = db.Column(db.String(120))
    description = db.Column(db.String(255), nullable=False)
    description_km = db.Column(db.String(255))
    priority = db.Column(db.Integer, nullable=False, default=1)
    confidence = db.Column(db.Float, nullable=False, default=80.0)
    disease_id = db.Column(db.Integer, db.ForeignKey("tbl_diseases.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)

    disease = db.relationship("Disease", back_populates="rules")
    symptoms = db.relationship(
        "Symptom",
        secondary=tbl_rules_symptoms,
        back_populates="rules",
    )

    def __repr__(self) -> str:
        return f"<Rule {self.title}>"


class Case(db.Model):
    __tablename__ = "tbl_cases"

    id = db.Column(db.Integer, db.Sequence('seq_cases_id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("tbl_users.id"))
    disease_id = db.Column(db.Integer, db.ForeignKey("tbl_diseases.id"))
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=now_kh, nullable=False)

    symptoms = db.relationship(
        "Symptom",
        secondary=tbl_cases_symptoms,
        back_populates="cases",
    )
    disease = db.relationship("Disease", back_populates="cases")
    user = db.relationship("UserTable")

    def __repr__(self) -> str:
        return f"<Case {self.id}>"
