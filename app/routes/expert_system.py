# app/routes/expert_system.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, Response
from flask_login import login_required, current_user
from app.i18n import gettext as _
from utils.decorators import require_permission
from extensions import db
from app.forms.expert_system_forms import (
    doctor_choices_query,
    CategoryForm,
    SymptomForm,
    DiseaseForm,
    RuleForm,
    PageTextForm,
)
from app.services.diagnosis_service import DiagnosisService
from app.services.expert_system_service import (
    CategoryService,
    SymptomService,
    DiseaseService,
    RuleService,
    CaseService,
)
from app.services.audit_service import AuditService
from app.services.page_text_service import PageTextService
from app.services.page_feature_service import PageFeatureService

expert_system_bp = Blueprint("expert_system", __name__, url_prefix="/expert-system")


@expert_system_bp.route("/author-rules")
@login_required
@require_permission("author_rules")
def author_rules():
    return redirect(url_for("expert_system.rules_index"))


@expert_system_bp.route("/diagnose", methods=["GET", "POST"])
@login_required
@require_permission("run_diagnosis")
def diagnose():
    if not PageFeatureService.is_enabled("diagnose"):
        return render_template("expert_system/maintenance.html")

    symptoms = DiagnosisService.get_all_symptoms()
    diagnosis_results = None
    selected_ids = []
    case = None

    if request.method == "POST":
        selected_ids = [int(id) for id in request.form.getlist("symptoms")]
        if selected_ids:
            diagnosis_results = DiagnosisService.run_inference(selected_ids)
            if diagnosis_results:
                # A language switch on the results page resubmits the same symptoms just to get
                # the text re-rendered in the new language — that isn't a new diagnosis, so reuse
                # the existing case instead of writing a duplicate history row.
                reuse_case_id = request.form.get("reuse_case_id", type=int)
                reused_case = CaseService.get_by_id(reuse_case_id) if reuse_case_id else None
                if reused_case and reused_case.user_id == current_user.id:
                    case = reused_case
                else:
                    case = DiagnosisService.record_case(
                        current_user.id,
                        selected_ids,
                        diagnosis_results[0],
                    )
                    AuditService.log("DIAGNOSE", "Case", case.id, f"User ran diagnosis, result: {case.disease.name}")
        else:
            flash(_("សូមជ្រើសរើសរោគសញ្ញាយ៉ាងហោចណាស់មួយ។"), "warning")

    return render_template(
        "expert_system/diagnose.html",
        symptoms=symptoms,
        results=diagnosis_results,
        selected_ids=set(selected_ids),
        case_id=case.id if case else None,
        case=case,
    )


@expert_system_bp.route("/narrate", methods=["GET", "POST"])
@login_required
def narrate():
    """Generates and streams AI Voice audio using Edge-TTS neural voices.
    - Female Khmer (km-KH-SreymomNeural)
    - Female English (en-US-AriaNeural)
    Supports narrating a specific saved case history by case_id or custom text.
    """
    from app.services.voice_service import VoiceService

    if not (current_user.has_permission("run_diagnosis") or current_user.has_permission("view_cases")):
        abort(403)

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        text = (data.get("text") or "").strip()
        lang = data.get("lang") or "km"
        case_id = data.get("case_id")
        mode = data.get("mode") or "full"
    else:
        text = (request.args.get("text") or "").strip()
        lang = request.args.get("lang") or "km"
        case_id = request.args.get("case_id", type=int)
        mode = request.args.get("mode") or "full"

    if case_id:
        case = CaseService.get_by_id(case_id)
        if not case:
            abort(404, "Case not found")
        # Security check: User can only access their own case unless Admin or Doctor
        if not (current_user.has_role("Admin") or current_user.has_role("Doctor")):
            if case.user_id != current_user.id:
                abort(403, "Forbidden")

        disease_name = ""
        desc = ""
        treatment = ""
        if case.disease:
            if lang == "en":
                disease_name = case.disease.name or "Unknown"
                desc = case.disease.description or ""
                treatment = case.disease.treatment or ""
            else:
                disease_name = case.disease.name_km or case.disease.name or "មិនស្គាល់"
                desc = case.disease.description_km or case.disease.description or ""
                treatment = case.disease.treatment_km or case.disease.treatment or ""
        else:
            disease_name = "Unknown" if lang == "en" else "មិនស្គាល់"

        symptoms = []
        if case.symptoms:
            for s in case.symptoms:
                s_name = (s.name if lang == "en" else (s.name_km or s.name))
                if s_name:
                    symptoms.append(s_name)

        if mode == "summary":
            if lang == "en":
                sym_str = ", ".join(symptoms) if symptoms else "none recorded"
                text = f"Diagnostic Case #{case.id}. Diagnosed disease: {disease_name}. Confidence level: {case.confidence:.1f} percent. Symptoms: {sym_str}."
            else:
                sym_str = " និង ".join(symptoms) if symptoms else "គ្មាន"
                text = f"ករណីរោគវិនិច្ឆ័យលេខ #{case.id}។ ជំងឺ {disease_name}។ កម្រិតទំនុកចិត្ត {case.confidence:.1f} ភាគរយ។ រោគសញ្ញារួមមាន៖ {sym_str}។"
        else:
            if lang == "en":
                sym_str = ", ".join(symptoms) if symptoms else "none recorded"
                text = f"Case History Diagnostic Report #{case.id}. Diagnosed disease: {disease_name}. Confidence level: {case.confidence:.1f} percent. Observed symptoms: {sym_str}. Disease description: {desc}. Recommended treatment: {treatment}."
            else:
                sym_str = " និង ".join(symptoms) if symptoms else "គ្មាន"
                text = f"របាយការណ៍ប្រវត្តិនៃការធ្វើរោគវិនិច្ឆ័យករណី #{case.id}។ រោគវិនិច្ឆ័យគឺជំងឺ {disease_name}។ កម្រិតទំនុកចិត្ត {case.confidence:.1f} ភាគរយ។ រោគសញ្ញាដែលបានសង្កេតរួមមាន៖ {sym_str}។ ការពិពណ៌នាអំពីជំងឺ៖ {desc}។ ការព្យាបាលដែលបានណែនាំ៖ {treatment}។"

    elif not text:
        disease_name = request.values.get("name", "").strip()
        confidence = request.values.get("confidence", "").strip()
        description = request.values.get("desc", "").strip()
        treatment = request.values.get("treatment", "").strip()

        if disease_name:
            if lang == "en":
                text = f"Diagnosis result: {disease_name}. Confidence level: {confidence} percent. {description}. Recommended treatment: {treatment}."
            else:
                text = f"លទ្ធផលនៃការវិភាគគឺជំងឺ {disease_name}។ កម្រិតទំនុកចិត្ត {confidence} ភាគរយ។ {description}។ ការព្យាបាលដែលបានណែនាំ៖ {treatment}។"

    if not text:
        abort(400, "Missing text or case_id for speech generation")

    try:
        audio_bytes = VoiceService.text_to_speech(text, lang=lang)
        return Response(
            audio_bytes,
            mimetype="audio/mpeg",
            headers={
                "Content-Type": "audio/mpeg",
                "Cache-Control": "public, max-age=86400",
                "Accept-Ranges": "bytes",
                "Content-Length": str(len(audio_bytes)),
            },
        )
    except Exception as e:
        abort(500, f"Speech synthesis failed: {e}")


@expert_system_bp.route("/cases")
@login_required
@require_permission("view_cases")
def cases_index():
    if not PageFeatureService.is_enabled("cases"):
        return render_template("layouts/maintenance.html")

    page = request.args.get("page", 1, type=int)
    # Admin/Doctor see every case; everyone else only their own.
    scope_user_id = None if (current_user.has_role("Admin") or current_user.has_role("Doctor")) else current_user.id
    pager = CaseService.get_page(page, user_id=scope_user_id)

    return render_template(
        "expert_system/cases/index.html",
        cases=pager.items,
        pager=pager,
        stats=CaseService.stats(user_id=scope_user_id),
    )


@expert_system_bp.route("/cases/<int:case_id>")
@login_required
@require_permission("view_cases")
def cases_detail(case_id: int):
    case = CaseService.get_by_id(case_id)
    if case is None:
        abort(404)
        
    # Security check: User can only view their own case unless they are Admin/Doctor
    if not (current_user.has_role("Admin") or current_user.has_role("Doctor")):
        if case.user_id != current_user.id:
            abort(403)
            
    return render_template("expert_system/cases/detail.html", case=case)


@expert_system_bp.route("/categories")
@login_required
@require_permission("manage_categories")
def categories_index():
    categories = CategoryService.get_all()
    form = CategoryForm()
    return render_template("expert_system/categories/index.html", categories=categories, form=form)


@expert_system_bp.route("/categories/create", methods=["GET", "POST"])
@login_required
@require_permission("manage_categories")
def categories_create():
    form = CategoryForm()
    if request.method == "GET":
        return redirect(url_for("expert_system.categories_index", open_create=1))
    if form.validate_on_submit():
        category = CategoryService.create(
            {"name": form.name.data, "name_km": form.name_km.data,
             "description": form.description.data, "description_km": form.description_km.data}
        )
        AuditService.log("CREATE", "Category", category.id, f"Created category: {category.name}")
        flash(_("បានបង្កើតប្រភេទ '%(name)s' ដោយជោគជ័យ។", name=category.name), "success")
        return redirect(url_for("expert_system.categories_index"))
    categories = CategoryService.get_all()
    return render_template(
        "expert_system/categories/index.html",
        categories=categories,
        form=form,
        show_create_modal=True,
    )


@expert_system_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
@require_permission("manage_categories")
def categories_edit(category_id: int):
    category = CategoryService.get_by_id(category_id)
    if category is None:
        abort(404)
    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        CategoryService.update(
            category,
            {"name": form.name.data, "name_km": form.name_km.data,
             "description": form.description.data, "description_km": form.description_km.data},
        )
        AuditService.log("UPDATE", "Category", category.id, f"Updated category: {category.name}")
        flash(_("បានកែប្រែប្រភេទដោយជោគជ័យ។"), "success")
        return redirect(url_for("expert_system.categories_index"))
    return render_template(
        "expert_system/categories/edit.html",
        form=form,
        category=category,
    )


@expert_system_bp.route("/categories/<int:category_id>/delete", methods=["GET", "POST"])
@login_required
@require_permission("manage_categories")
def categories_delete(category_id: int):
    category = CategoryService.get_by_id(category_id)
    if category is None:
        abort(404)
    if request.method == "POST":
        category_name = category.name
        CategoryService.delete(category)
        AuditService.log("DELETE", "Category", category_id, f"Deleted category: {category_name}")
        flash(_("បានលុបប្រភេទដោយជោគជ័យ។"), "success")
        return redirect(url_for("expert_system.categories_index"))
    return render_template(
        "expert_system/categories/delete_confirm.html",
        category=category,
    )


@expert_system_bp.route("/symptoms")
@login_required
@require_permission("manage_symptoms")
def symptoms_index():
    symptoms = SymptomService.get_all()
    form = SymptomForm()
    return render_template("expert_system/symptoms/index.html", symptoms=symptoms, form=form)


@expert_system_bp.route("/symptoms/create", methods=["GET", "POST"])
@login_required
@require_permission("manage_symptoms")
def symptoms_create():
    form = SymptomForm()
    if request.method == "GET":
        return redirect(url_for("expert_system.symptoms_index", open_create=1))
    if form.validate_on_submit():
        symptom = SymptomService.create(
            {"name": form.name.data, "name_km": form.name_km.data,
             "description": form.description.data, "description_km": form.description_km.data}
        )
        AuditService.log("CREATE", "Symptom", symptom.id, f"Created symptom: {symptom.name}")
        flash(_("បានបង្កើតរោគសញ្ញា '%(name)s' ដោយជោគជ័យ។", name=symptom.name), "success")
        return redirect(url_for("expert_system.symptoms_index"))
    symptoms = SymptomService.get_all()
    return render_template(
        "expert_system/symptoms/index.html",
        symptoms=symptoms,
        form=form,
        show_create_modal=True,
    )


@expert_system_bp.route("/symptoms/<int:symptom_id>/edit", methods=["GET", "POST"])
@login_required
@require_permission("manage_symptoms")
def symptoms_edit(symptom_id: int):
    symptom = SymptomService.get_by_id(symptom_id)
    if symptom is None:
        abort(404)
    form = SymptomForm(obj=symptom)
    if form.validate_on_submit():
        SymptomService.update(
            symptom,
            {"name": form.name.data, "name_km": form.name_km.data,
             "description": form.description.data, "description_km": form.description_km.data},
        )
        AuditService.log("UPDATE", "Symptom", symptom.id, f"Updated symptom: {symptom.name}")
        flash(_("បានកែប្រែរោគសញ្ញាដោយជោគជ័យ។"), "success")
        return redirect(url_for("expert_system.symptoms_index"))
    return render_template(
        "expert_system/symptoms/edit.html",
        form=form,
        symptom=symptom,
    )


@expert_system_bp.route("/symptoms/<int:symptom_id>/delete", methods=["GET", "POST"])
@login_required
@require_permission("manage_symptoms")
def symptoms_delete(symptom_id: int):
    symptom = SymptomService.get_by_id(symptom_id)
    if symptom is None:
        abort(404)
    if request.method == "POST":
        symptom_name = symptom.name
        SymptomService.delete(symptom)
        AuditService.log("DELETE", "Symptom", symptom_id, f"Deleted symptom: {symptom_name}")
        flash(_("បានលុបរោគសញ្ញាដោយជោគជ័យ។"), "success")
        return redirect(url_for("expert_system.symptoms_index"))
    return render_template(
        "expert_system/symptoms/delete_confirm.html",
        symptom=symptom,
    )


def _diseases_page_context() -> dict:
    return {
        "diseases": DiseaseService.get_all(),
        "categories": CategoryService.get_all(),
        "doctors": db.session.scalars(doctor_choices_query()).all(),
    }


@expert_system_bp.route("/diseases")
@login_required
@require_permission("manage_diseases")
def diseases_index():
    form = DiseaseForm()
    # A doctor adding a disease is most likely verifying it themselves.
    if current_user.has_role("Doctor"):
        form.doctor_id.data = current_user.id
    return render_template("expert_system/diseases/index.html", form=form, **_diseases_page_context())


@expert_system_bp.route("/diseases/create", methods=["GET", "POST"])
@login_required
@require_permission("manage_diseases")
def diseases_create():
    form = DiseaseForm()
    if request.method == "GET":
        return redirect(url_for("expert_system.diseases_index", open_create=1))
    if form.validate_on_submit():
        disease = DiseaseService.create(
            {
                "name": form.name.data,
                "name_km": form.name_km.data,
                "description": form.description.data,
                "description_km": form.description_km.data,
                "treatment": form.treatment.data,
                "treatment_km": form.treatment_km.data,
                "category_id": form.category_id.data,
                "doctor_id": form.doctor_id.data,
            },
        )
        AuditService.log("CREATE", "Disease", disease.id, f"Created disease: {disease.name}")
        flash(_("បានបង្កើតជំងឺ '%(name)s' ដោយជោគជ័យ។", name=disease.name), "success")
        return redirect(url_for("expert_system.diseases_index"))
    return render_template(
        "expert_system/diseases/index.html",
        form=form,
        show_create_modal=True,
        **_diseases_page_context(),
    )


@expert_system_bp.route("/diseases/<int:disease_id>/edit", methods=["GET", "POST"])
@login_required
@require_permission("manage_diseases")
def diseases_edit(disease_id: int):
    disease = DiseaseService.get_by_id(disease_id)
    if disease is None:
        abort(404)
    form = DiseaseForm(obj=disease)
    if form.validate_on_submit():
        update_data = {
            "name": form.name.data,
            "name_km": form.name_km.data,
            "description": form.description.data,
            "description_km": form.description_km.data,
            "treatment": form.treatment.data,
            "treatment_km": form.treatment_km.data,
            "category_id": form.category_id.data,
            "doctor_id": form.doctor_id.data,
        }
        DiseaseService.update(disease, update_data)
        AuditService.log("UPDATE", "Disease", disease.id, f"Updated disease: {disease.name}")
        flash(_("បានកែប្រែជំងឺដោយជោគជ័យ។"), "success")
        return redirect(url_for("expert_system.diseases_index"))
    return render_template(
        "expert_system/diseases/edit.html",
        form=form,
        disease=disease,
    )


@expert_system_bp.route("/diseases/<int:disease_id>/delete", methods=["GET", "POST"])
@login_required
@require_permission("manage_diseases")
def diseases_delete(disease_id: int):
    disease = DiseaseService.get_by_id(disease_id)
    if disease is None:
        abort(404)
    if request.method == "POST":
        disease_name = disease.name
        DiseaseService.delete(disease)
        AuditService.log("DELETE", "Disease", disease_id, f"Deleted disease: {disease_name}")
        flash(_("បានលុបជំងឺដោយជោគជ័យ។"), "success")
        return redirect(url_for("expert_system.diseases_index"))
    return render_template(
        "expert_system/diseases/delete_confirm.html",
        disease=disease,
    )


def _rules_page_context() -> dict:
    return {
        "rules": RuleService.get_all(),
        "diseases": DiseaseService.get_all(),
        "symptoms": SymptomService.get_all(),
        "doctors": db.session.scalars(doctor_choices_query()).all(),
    }


@expert_system_bp.route("/rules")
@login_required
@require_permission("manage_rules")
def rules_index():
    form = RuleForm()
    # A doctor adding a rule is most likely approving it themselves.
    if current_user.has_role("Doctor"):
        form.approved_by_id.data = current_user.id
    return render_template("expert_system/rules/index.html", form=form, **_rules_page_context())


@expert_system_bp.route("/rules/create", methods=["GET", "POST"])
@login_required
@require_permission("manage_rules")
def rules_create():
    form = RuleForm()
    if request.method == "GET":
        return redirect(url_for("expert_system.rules_index", open_create=1))
    if form.validate_on_submit():
        rule = RuleService.create(
            {
                "title": form.title.data,
                "title_km": form.title_km.data,
                "description": form.description.data,
                "description_km": form.description_km.data,
                "priority": form.priority.data,
                "confidence": form.confidence.data,
                "disease_id": form.disease_id.data,
                "approved_by_id": form.approved_by_id.data,
            },
            symptom_ids=form.symptom_ids.data or [],
        )
        AuditService.log("CREATE", "Rule", rule.id, f"Created rule: {rule.title}")
        flash(_("បានបង្កើតវិធាន '%(title)s' ដោយជោគជ័យ។", title=rule.title), "success")
        return redirect(url_for("expert_system.rules_index"))
    
    # If validation fails, print errors to console for debugging
    if form.errors:
        print(f"Form validation errors: {form.errors}")
        
    return render_template(
        "expert_system/rules/index.html",
        form=form,
        show_create_modal=True,
        **_rules_page_context(),
    )


@expert_system_bp.route("/rules/<int:rule_id>/edit", methods=["GET", "POST"])
@login_required
@require_permission("manage_rules")
def rules_edit(rule_id: int):
    rule = RuleService.get_by_id(rule_id)
    if rule is None:
        abort(404)
    form = RuleForm(original_rule=rule, obj=rule)
    if form.validate_on_submit():
        RuleService.update(
            rule,
            {
                "title": form.title.data,
                "title_km": form.title_km.data,
                "description": form.description.data,
                "description_km": form.description_km.data,
                "priority": form.priority.data,
                "confidence": form.confidence.data,
                "disease_id": form.disease_id.data,
                "approved_by_id": form.approved_by_id.data,
            },
            symptom_ids=form.symptom_ids.data or [],
        )
        AuditService.log("UPDATE", "Rule", rule.id, f"Updated rule: {rule.title}")
        flash(_("បានកែប្រែវិធានដោយជោគជ័យ។"), "success")
        return redirect(url_for("expert_system.rules_index"))
        
    # If validation fails, print errors to console for debugging
    if form.errors:
        print(f"Form validation errors: {form.errors}")

    return render_template(
        "expert_system/rules/edit.html",
        form=form,
        rule=rule,
    )


@expert_system_bp.route("/rules/<int:rule_id>/delete", methods=["GET", "POST"])
@login_required
@require_permission("manage_rules")
def rules_delete(rule_id: int):
    rule = RuleService.get_by_id(rule_id)
    if rule is None:
        abort(404)
    if request.method == "POST":
        rule_title = rule.title
        RuleService.delete(rule)
        AuditService.log("DELETE", "Rule", rule_id, f"Deleted rule: {rule_title}")
        flash(_("បានលុបវិធានដោយជោគជ័យ។"), "success")
        return redirect(url_for("expert_system.rules_index"))
    return render_template(
        "expert_system/rules/delete_confirm.html",
        rule=rule,
    )


@expert_system_bp.route("/page-texts")
@login_required
@require_permission("manage_page_texts")
def page_texts_index():
    items = PageTextService.get_all()
    pages = sorted({item.page for item in items})
    page_enabled = {page: PageFeatureService.is_enabled(page) for page in pages}
    return render_template("expert_system/page_texts/index.html", items=items, page_enabled=page_enabled)


@expert_system_bp.route("/page-texts/<page>/toggle", methods=["POST"])
@login_required
@require_permission("manage_page_texts")
def page_texts_toggle(page: str):
    enabled = not PageFeatureService.is_enabled(page)
    PageFeatureService.set_enabled(page, enabled)
    AuditService.log("UPDATE", "PageFeature", None,
                      f"{'Enabled' if enabled else 'Disabled'} page: {page}")
    flash(_("បានធ្វើបច្ចុប្បន្នភាពស្ថានភាពទំព័រ។"), "success")
    return redirect(url_for("expert_system.page_texts_index"))


@expert_system_bp.route("/page-texts/<int:text_id>/edit", methods=["GET", "POST"])
@login_required
@require_permission("manage_page_texts")
def page_texts_edit(text_id: int):
    item = PageTextService.get_by_id(text_id)
    if item is None:
        abort(404)
    form = PageTextForm(obj=item)
    if form.validate_on_submit():
        PageTextService.update(item, form.text_km.data, form.text_en.data)
        AuditService.log("UPDATE", "PageText", item.id, f"Updated page text: {item.key}")
        flash(_("បានកែប្រែអត្ថបទដោយជោគជ័យ។"), "success")
        return redirect(url_for("expert_system.page_texts_index"))
    return render_template("expert_system/page_texts/edit.html", form=form, item=item)


@expert_system_bp.route("/page-texts/<int:text_id>/reset", methods=["GET", "POST"])
@login_required
@require_permission("manage_page_texts")
def page_texts_reset(text_id: int):
    item = PageTextService.get_by_id(text_id)
    if item is None:
        abort(404)
    if request.method == "POST":
        PageTextService.reset(item)
        AuditService.log("UPDATE", "PageText", item.id, f"Reset page text to default: {item.key}")
        flash(_("បានស្តារអត្ថបទទៅលំនាំដើមវិញ។"), "success")
        return redirect(url_for("expert_system.page_texts_edit", text_id=item.id))
    return render_template("expert_system/page_texts/reset_confirm.html", item=item)
