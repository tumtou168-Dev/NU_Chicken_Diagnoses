from app.models.expert_system import Symptom, Rule, Case
from extensions import db

class DiagnosisService:
    @staticmethod
    def get_all_symptoms():
        """Fetches all symptoms for the Doctor and User journeys."""
        return Symptom.query.all()

    @staticmethod
    def get_all_rules():
        """Fetches all authored rules for the Knowledge Base view."""
        return Rule.query.all()

    @staticmethod
    def run_inference(selected_symptom_ids, limit=3):
        """
        Forward Chaining Inference Engine: Matches user input against Doctor rules.
        """
        all_rules = Rule.query.all()
        results = []

        for rule in all_rules:
            # Get the set of symptom IDs required for this rule
            rule_symptom_ids = {s.id for s in rule.symptoms}
            input_ids = set(selected_symptom_ids)
            
            # Find matching symptoms
            matches = input_ids.intersection(rule_symptom_ids)
            if matches:
                # Calculate confidence (Match / Total Required)
                match_ratio = len(matches) / len(rule_symptom_ids)
                weighted = match_ratio * (rule.confidence or 100.0)
                confidence = min(weighted, 100.0)
                results.append({
                    "disease": rule.disease,
                    "confidence": round(confidence, 2),
                    "matched_count": len(matches),
                    "treatment": rule.disease.treatment,
                    "rule": rule,
                })

        # Sort by highest match percentage, keep only the best rule per disease,
        # and return the top `limit` diseases.
        results.sort(key=lambda x: x['confidence'], reverse=True)
        top, seen = [], set()
        for result in results:
            if result["disease"].id in seen:
                continue
            seen.add(result["disease"].id)
            top.append(result)
            if len(top) == limit:
                break
        return top

    @staticmethod
    def record_case(user_id, selected_symptom_ids, top_result):
        if not top_result:
            return None
        case = Case(
            user_id=user_id,
            disease_id=top_result["disease"].id,
            confidence=top_result["confidence"],
        )
        case.symptoms = Symptom.query.filter(Symptom.id.in_(selected_symptom_ids)).all()
        db.session.add(case)
        db.session.commit()
        return case
