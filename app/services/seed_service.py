# app/services/seed_service.py
from extensions import db
from app.models import PermissionTable, RoleTable, UserTable
from app.models.expert_system import Category, Symptom, Disease, Rule


def _get_or_create(model, defaults=None, **kwargs):
    instance = db.session.scalar(db.select(model).filter_by(**kwargs))
    if instance:
        return instance
    params = dict(defaults or {})
    params.update(kwargs)
    instance = model(**params)
    db.session.add(instance)
    return instance


def seed_permissions_and_roles():
    permissions = [
        ("USER_CREATE", "Create Users", "Users"),
        ("USER_EDIT", "Edit Users", "Users"),
        ("USER_DELETE", "Delete Users", "Users"),
        ("ROLE_MANAGE", "Manage Roles", "Roles"),
        ("PERMISSION_MANAGE", "Manage Permissions", "Permissions"),
        ("author_rules", "Author Expert Rules", "Expert System"),
        ("manage_symptoms", "Manage Symptoms", "Expert System"),
        ("manage_diseases", "Manage Diseases", "Expert System"),
        ("manage_rules", "Manage Rules", "Expert System"),
        ("manage_categories", "Manage Categories", "Expert System"),
        ("run_diagnosis", "Run Diagnosis", "Expert System"),
        ("view_cases", "View Case History", "Expert System"),
    ]

    perm_objs = []
    for code, name, module in permissions:
        perm = _get_or_create(
            PermissionTable,
            code=code,
            defaults={"name": name, "module": module},
        )
        perm.name = name
        perm.module = module
        perm_objs.append(perm)

    admin_role = _get_or_create(RoleTable, name="Admin", defaults={"description": "System administrator"})
    doctor_role = _get_or_create(RoleTable, name="Doctor", defaults={"description": "Knowledge author"})
    user_role = _get_or_create(RoleTable, name="User", defaults={"description": "Diagnosis user"})

    db.session.flush()

    admin_role.permissions = perm_objs
    doctor_role.permissions = [
        p for p in perm_objs
        if p.code in {
            "author_rules",
            "manage_symptoms",
            "manage_diseases",
            "manage_rules",
            "manage_categories",
            "view_cases",
            "run_diagnosis", # Doctor should also be able to run diagnosis
        }
    ]
    user_role.permissions = [p for p in perm_objs if p.code in {"run_diagnosis", "view_cases"}]

    db.session.commit()


def seed_admin_user():
    admin = db.session.scalar(db.select(UserTable).filter_by(username="admin"))
    if admin:
        return
    admin_role = db.session.scalar(db.select(RoleTable).filter_by(name="Admin"))
    if not admin_role:
        return
    admin = UserTable(
        username="admin",
        email="admin@example.com",
        full_name="System Administrator",
        is_active=True,
    )
    admin.set_password("Admin@123")
    admin.roles = [admin_role]
    db.session.add(admin)
    db.session.commit()


def seed_expert_data():
    if db.session.scalar(db.select(Disease).limit(1)):
        return

    cat_resp = _get_or_create(Category, name="Respiratory", defaults={"description": "Breathing-related illnesses"})
    cat_digest = _get_or_create(Category, name="Digestive", defaults={"description": "Gastrointestinal illnesses"})
    cat_neuro = _get_or_create(Category, name="Neurological", defaults={"description": "Nervous system illnesses"})
    cat_bact = _get_or_create(Category, name="Bacterial", defaults={"description": "Bacterial infections"})

    diseases = {
        "infectious_bronchitis": Disease(
            name="Infectious Bronchitis",
            description="Highly contagious respiratory disease affecting chickens.",
            treatment="Isolate affected birds, provide supportive care, consult a vet about vaccination strategy.",
            category=cat_resp,
        ),
        "newcastle": Disease(
            name="Newcastle Disease",
            description="Viral disease causing respiratory and neurological signs.",
            treatment="Isolate, notify vet, and follow vaccination protocols.",
            category=cat_neuro,
        ),
        "coccidiosis": Disease(
            name="Coccidiosis",
            description="Parasitic disease affecting the intestinal tract.",
            treatment="Administer anticoccidial medication and improve litter hygiene.",
            category=cat_digest,
        ),
        "fowl_cholera": Disease(
            name="Fowl Cholera",
            description="Bacterial infection causing sudden illness and death.",
            treatment="Treat with antibiotics under veterinary guidance and improve sanitation.",
            category=cat_bact,
        ),
        "marek": Disease(
            name="Marek's Disease",
            description="Viral disease causing paralysis and tumors.",
            treatment="No cure; vaccinate chicks and isolate affected birds.",
            category=cat_neuro,
        ),
    }
    db.session.add_all(diseases.values())
    db.session.flush()

    # Symptoms live in the database, not in code: a rule is only seeded when every symptom it names exists.
    rule_specs = [
        ("Respiratory infection pattern", "Coughing + sneezing + nasal discharge", 1, 85.0, "infectious_bronchitis",
         ["Coughing", "Sneezing", "Nasal discharge"]),
        ("Neurological respiratory combo", "Coughing + nasal discharge + lethargy", 2, 80.0, "newcastle",
         ["Coughing", "Nasal discharge", "Lethargy"]),
        ("Coccidiosis signature", "Bloody diarrhea + lethargy", 1, 90.0, "coccidiosis",
         ["Bloody diarrhea", "Lethargy"]),
        ("Fowl cholera indicators", "Swollen face + lethargy + ruffled feathers", 2, 78.0, "fowl_cholera",
         ["Swollen face", "Lethargy", "Ruffled feathers"]),
        ("Marek's disease pattern", "Lameness + lethargy", 3, 75.0, "marek",
         ["Lameness", "Lethargy"]),
    ]
    by_name = {sym.name: sym for sym in db.session.scalars(db.select(Symptom))}
    for title, description, priority, confidence, disease_key, symptom_names in rule_specs:
        if not all(name in by_name for name in symptom_names):
            continue
        db.session.add(Rule(
            title=title, description=description, priority=priority, confidence=confidence,
            disease=diseases[disease_key], symptoms=[by_name[name] for name in symptom_names],
        ))
    db.session.commit()


def seed_all():
    seed_permissions_and_roles()
    seed_admin_user()
    seed_expert_data()
