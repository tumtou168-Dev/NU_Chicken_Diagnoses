# app/services/expert_system_service.py
from typing import List, Optional
from extensions import db
from app.models.expert_system import Category, Symptom, Disease, Rule, Case


class CategoryService:
    @staticmethod
    def get_all() -> List[Category]:
        return Category.query.order_by(Category.name.asc()).all()

    @staticmethod
    def get_by_id(category_id: int) -> Optional[Category]:
        return Category.query.get(category_id)

    @staticmethod
    def create(data: dict) -> Category:
        category = Category(
            name=data["name"],
            name_km=data.get("name_km") or None,
            description=data.get("description") or "",
            description_km=data.get("description_km") or None,
        )
        db.session.add(category)
        db.session.commit()
        return category

    @staticmethod
    def update(category: Category, data: dict) -> Category:
        category.name = data["name"]
        category.name_km = data.get("name_km") or None
        category.description = data.get("description") or ""
        category.description_km = data.get("description_km") or None
        db.session.commit()
        return category

    @staticmethod
    def delete(category: Category) -> None:
        db.session.delete(category)
        db.session.commit()


class SymptomService:
    @staticmethod
    def get_all() -> List[Symptom]:
        return Symptom.query.order_by(Symptom.name.asc()).all()

    @staticmethod
    def get_by_id(symptom_id: int) -> Optional[Symptom]:
        return Symptom.query.get(symptom_id)

    @staticmethod
    def create(data: dict) -> Symptom:
        symptom = Symptom(
            name=data["name"],
            name_km=data.get("name_km") or None,
            description=data.get("description") or "",
            description_km=data.get("description_km") or None,
        )
        db.session.add(symptom)
        db.session.commit()
        return symptom

    @staticmethod
    def update(symptom: Symptom, data: dict) -> Symptom:
        symptom.name = data["name"]
        symptom.name_km = data.get("name_km") or None
        symptom.description = data.get("description") or ""
        symptom.description_km = data.get("description_km") or None
        db.session.commit()
        return symptom

    @staticmethod
    def delete(symptom: Symptom) -> None:
        db.session.delete(symptom)
        db.session.commit()


class DiseaseService:
    @staticmethod
    def get_all() -> List[Disease]:
        return Disease.query.order_by(Disease.name.asc()).all()

    @staticmethod
    def get_by_id(disease_id: int) -> Optional[Disease]:
        return Disease.query.get(disease_id)

    @staticmethod
    def create(data: dict) -> Disease:
        disease = Disease(
            name=data["name"],
            name_km=data.get("name_km") or None,
            description=data["description"],
            description_km=data.get("description_km") or None,
            treatment=data["treatment"],
            treatment_km=data.get("treatment_km") or None,
            category_id=data.get("category_id") or None,
        )
        db.session.add(disease)
        db.session.commit()
        return disease

    @staticmethod
    def update(disease: Disease, data: dict) -> Disease:
        disease.name = data["name"]
        disease.name_km = data.get("name_km") or None
        disease.description = data["description"]
        disease.description_km = data.get("description_km") or None
        disease.treatment = data["treatment"]
        disease.treatment_km = data.get("treatment_km") or None
        disease.category_id = data.get("category_id") or None
        db.session.commit()
        return disease

    @staticmethod
    def delete(disease: Disease) -> None:
        db.session.delete(disease)
        db.session.commit()


class RuleService:
    @staticmethod
    def get_all() -> List[Rule]:
        return Rule.query.order_by(Rule.priority.asc(), Rule.id.asc()).all()

    @staticmethod
    def get_by_id(rule_id: int) -> Optional[Rule]:
        return Rule.query.get(rule_id)

    @staticmethod
    def create(data: dict, symptom_ids: List[int]) -> Rule:
        rule = Rule(
            title=data["title"],
            title_km=data.get("title_km") or None,
            description=data["description"],
            description_km=data.get("description_km") or None,
            priority=data["priority"],
            confidence=data["confidence"],
            disease_id=data["disease_id"],
        )
        if symptom_ids:
            # Ensure symptom_ids are integers
            symptom_ids = [int(sid) for sid in symptom_ids]
            rule.symptoms = Symptom.query.filter(Symptom.id.in_(symptom_ids)).all()
        db.session.add(rule)
        db.session.commit()
        return rule

    @staticmethod
    def update(rule: Rule, data: dict, symptom_ids: List[int]) -> Rule:
        rule.title = data["title"]
        rule.title_km = data.get("title_km") or None
        rule.description = data["description"]
        rule.description_km = data.get("description_km") or None
        rule.priority = data["priority"]
        rule.confidence = data["confidence"]
        rule.disease_id = data["disease_id"]
        if symptom_ids:
             # Ensure symptom_ids are integers
            symptom_ids = [int(sid) for sid in symptom_ids]
            rule.symptoms = Symptom.query.filter(Symptom.id.in_(symptom_ids)).all()
        else:
            rule.symptoms = []
        db.session.commit()
        return rule

    @staticmethod
    def delete(rule: Rule) -> None:
        db.session.delete(rule)
        db.session.commit()


class CaseService:
    @staticmethod
    def get_all() -> List[Case]:
        return Case.query.order_by(Case.created_at.desc()).all()

    @staticmethod
    def get_by_user(user_id: int) -> List[Case]:
        return Case.query.filter_by(user_id=user_id).order_by(Case.created_at.desc()).all()

    @staticmethod
    def get_page(page: int, user_id: Optional[int] = None, per_page: int = 20):
        query = Case.query if user_id is None else Case.query.filter_by(user_id=user_id)
        return query.order_by(Case.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def stats(user_id: Optional[int] = None) -> dict:
        """Total / high-confidence / low-confidence counts via SQL COUNT, without loading every row."""
        base = db.select(db.func.count(Case.id))
        if user_id is not None:
            base = base.filter_by(user_id=user_id)
        return {
            "total": db.session.scalar(base),
            "high": db.session.scalar(base.filter(Case.confidence > 80)),
            "low": db.session.scalar(base.filter(Case.confidence <= 50)),
        }

    @staticmethod
    def get_by_id(case_id: int) -> Optional[Case]:
        return Case.query.get(case_id)
