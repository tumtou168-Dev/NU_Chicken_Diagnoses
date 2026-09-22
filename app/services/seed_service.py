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
    # 1. Categories
    category_data = [
        ("Respiratory", "ផ្លូវដង្ហើម", "Breathing and airway illnesses", "ជំងឺទាក់ទងនឹងការដកដង្ហើម និងបំពង់ខ្យល់"),
        ("Digestive", "ប្រព័ន្ធរំលាយអាហារ", "Gastrointestinal and intestinal illnesses", "ជំងឺប្រព័ន្ធរំលាយអាហារ និងពោះវៀន"),
        ("Neurological", "ប្រព័ន្ធប្រសាទ", "Nervous system and paralysis illnesses", "ជំងឺប្រព័ន្ធប្រសាទ និងការខ្វិន"),
        ("Bacterial", "បាក់តេរី", "Bacterial infections in poultry", "ការឆ្លងមេរោគបាក់តេរីលើបក្សី"),
        ("Viral", "វីរុស", "Viral infections in poultry", "ការឆ្លងមេរោគវីរុសលើបក្សី"),
    ]

    cats = {}
    for name, name_km, desc, desc_km in category_data:
        cat = _get_or_create(Category, name=name, defaults={
            "name_km": name_km,
            "description": desc,
            "description_km": desc_km,
        })
        cat.name_km = name_km
        cat.description = desc
        cat.description_km = desc_km
        cats[name] = cat
    db.session.flush()

    # 2. Symptoms
    symptom_data = [
        ("Coughing", "ក្អក", "Frequent coughing or hacking sounds", "មាន់ក្អក ឬបញ្ចេញសំឡេងស្អកញឹកញាប់"),
        ("Sneezing", "កណ្តាស់", "Frequent sneezing or head shaking", "មាន់កណ្តាស់ ឬក្រវីក្បាលញឹកញាប់"),
        ("Nasal discharge", "ហៀរសំបោរ", "Clear or thick mucus discharge from nostrils", "ហៀរសំបោរថ្លា ឬខាប់ចេញពីច្រមុះ"),
        ("Labored breathing", "ដកដង្ហើមពិបាក", "Breathing with open mouth and gasping for air", "ដកដង្ហើមហត់ ហាខ្ទប់មាត់ និងដង្ហក់យកខ្យល់"),
        ("Swollen face / eyes", "ហើមមុខ / ភ្នែក", "Swelling around eyes, head, or wattles", "ហើមជុំវិញភ្នែក ក្បាល ឬសិរក្រោម"),
        ("Bloody diarrhea", "រាគមានឈាម", "Red or dark bloody droppings", "លាមកមានឈាមក្រហម ឬក្រមៅ"),
        ("Greenish diarrhea", "រាគពណ៌បៃតង", "Watery green droppings", "លាមករាគទឹកពណ៌បៃតង"),
        ("Watery diarrhea", "រាគទឹក", "Loose, watery white or yellowish droppings", "លាមករាគរាវពណ៌ស ឬលឿង"),
        ("Lethargy", "ស្ពឹកស្រពន់ / អស់កម្លាំង", "Inactive, drooping wings, low energy", "មិនសូវកម្រើក ធ្លាក់ស្លាប អស់កម្លាំង"),
        ("Ruffled feathers", "រោមច្របូកច្របល់", "Fluffed, unkempt, or messy plumage", "រោមក្រញុញ ក្រញង់ មិនរលោង"),
        ("Loss of appetite", "មិនស៊ីចំណី", "Refusing to eat or drink", "មិនស៊ីចំណី ឬមិនផឹកទឹក"),
        ("Decreased egg production", "ថយចុះការបញ្ចេញពង", "Sudden drop in egg laying rate", "ការធ្លាក់ចុះភ្លាមៗនៃបរិមាណពង"),
        ("Lameness / Leg weakness", "ខ្វិនជើង / ពិបាកដើរ", "Difficulty walking or standing", "ពិបាកដើរ ជើងទន់ ឬដួល"),
        ("Neck twisting", "រមួលក", "Twisted neck or head tremors", "កោងរមួលក ឬញ័រត្បាល់ក្បាល"),
        ("Paralysis", "ខ្វិន", "Complete loss of movement in wings or legs", "ខ្វិនស្លាប ឬជើងទាំងស្រុង"),
        ("Comb cyanosis / Dark comb", "សិរពណ៌ស្វាយ / ស្លេក", "Bluish or dark discoloration of comb and wattle", "សិរប្រែជាពណ៌ស្វាយ ក្រមៅ ឬស្លេក"),
    ]

    syms = {}
    for name, name_km, desc, desc_km in symptom_data:
        sym = _get_or_create(Symptom, name=name, defaults={
            "name_km": name_km,
            "description": desc,
            "description_km": desc_km,
        })
        sym.name_km = name_km
        sym.description = desc
        sym.description_km = desc_km
        syms[name] = sym
    db.session.flush()

    # 3. Diseases
    disease_data = [
        (
            "Infectious Bronchitis",
            "ជំងឺរលាកទងសួតឆ្លង",
            "Highly contagious viral respiratory disease causing coughing, sneezing, and drop in egg production.",
            "ជំងឺផ្លូវដង្ហើមឆ្លងបង្កដោយវីរុស ដែលបណ្តាលឱ្យក្អក កណ្តាស់ និងធ្លាក់ចុះការបញ្ចេញពង។",
            "Isolate affected birds, provide warm ventilation, administer electrolytes and vitamins, consult a vet for vaccination strategy.",
            "ដាក់មាន់ឈឺដាច់ដោយឡែក ផ្តល់កន្លែងកក់ក្តៅ និងមានខ្យល់ចេញចូលល្អ ផ្តល់វីតាមីននិងអេឡិចត្រូឡាយ និងពិគ្រោះជាមួយពេទ្យសត្វដើម្បីចាក់វ៉ាក់សាំង។",
            cats["Respiratory"],
        ),
        (
            "Newcastle Disease",
            "ជំងឺញូកាសល",
            "Acute viral disease causing respiratory distress, nervous signs (twisted neck), and high mortality.",
            "ជំងឺឆ្លងកាចសាហាវបង្កដោយវីរុស បណ្តាលឱ្យពិបាកដកដង្ហើម រមួលក ខ្វិន និងរាគពណ៌បៃតង។",
            "Strictly quarantine flock, report outbreak, disinfect premises, and vaccinate all healthy birds immediately.",
            "ធ្វើចត្តាឡីស័កហ្វូងមាន់ជាបន្ទាន់ សម្លាប់មេរោគក្នុងទ្រុង និងចាក់វ៉ាក់សាំងការពារដល់មាន់ដែលនៅមានសុខភាពល្អ។",
            cats["Viral"],
        ),
        (
            "Coccidiosis",
            "ជំងឺកុកស៊ីឌីយ៉ូស៊ីស",
            "Intestinal parasitic infection characterized by bloody diarrhea, ruffled feathers, and lethargy.",
            "ជំងឺប៉ារ៉ាស៊ីតពោះវៀន បណ្តាលឱ្យមាន់រាគមានឈាម ធ្លាក់ស្លាប រោមច្របូកច្របល់ និងស្ពឹកស្រពន់។",
            "Administer anticoccidial drugs (e.g., Amprolium, Toltrazuril) in drinking water and keep bedding dry and clean.",
            "ផ្តល់ថ្នាំព្យាបាលកុកស៊ីឌីយ៉ូស៊ីស (ដូចជា Amprolium ឬ Toltrazuril) ក្នុងទឹកផឹក និងផ្លាស់ប្តូរទ្រនាប់ទ្រុងឱ្យស្ងួតស្អាតជានិច្ច។",
            cats["Digestive"],
        ),
        (
            "Fowl Cholera",
            "ជំងឺអាសន្នរោគបក្សី",
            "Bacterial infection causing swollen wattles/face, labored breathing, and greenish diarrhea.",
            "ជំងឺបង្កដោយបាក់តេរី Pasteurella បណ្តាលឱ្យហើមសិរ ហើមមុខ ពិបាកដកដង្ហើម និងងាប់លឿន។",
            "Treat with antibiotics (e.g., Tetracycline or Sulfonamides) under vet supervision and improve coop sanitation.",
            "ព្យាបាលដោយថ្នាំអង់ទីប៊ីយោទិចក្រោមការណែនាំរបស់ពេទ្យសត្វ និងសម្អាតអនាម័យបរិស្ថានទ្រុង។",
            cats["Bacterial"],
        ),
        (
            "Marek's Disease",
            "ជំងឺម៉ារ៉ិក",
            "Viral infection causing progressive paralysis of wings/legs, lameness, and weight loss.",
            "ជំងឺវីរុសដែលបណ្តាលឱ្យខ្វិនជើង និងស្លាប ពិបាកដើរ មិនស៊ីចំណី និងស្គមរីងស្ងួត។",
            "No specific cure; isolate affected birds and vaccinate 1-day-old chicks as preventative measure.",
            "គ្មានថ្នាំព្យាបាលជាសះស្បើយទេ ត្រូវញែកមាន់ឈឺចេញ និងចាក់វ៉ាក់សាំងការពារលើកូនមាន់អាយុ ១ថ្ងៃ។",
            cats["Neurological"],
        ),
        (
            "Infectious Coryza",
            "ជំងឺផ្តាសាយឆ្លង",
            "Acute bacterial respiratory disease causing severe facial swelling and foul-smelling nasal discharge.",
            "ជំងឺផ្លូវដង្ហើមបង្កដោយបាក់តេរី បណ្តាលឱ្យហើមមុខ និងភ្នែកខ្លាំង ព្រមទាំងហៀរសំបោរធុំក្លិនមិនល្អ។",
            "Administer antibiotics (Erythromycin or Sulfadimethoxine) in drinking water and disinfect drinking equipment daily.",
            "ផ្តល់ថ្នាំអង់ទីប៊ីយោទិចក្នុងទឹកផឹក និងលាងសម្អាតស្នូកទឹកជារៀងរាល់ថ្ងៃ។",
            cats["Respiratory"],
        ),
        (
            "Avian Influenza",
            "ជំងឺផ្តាសាយបក្សី",
            "Severe contagious viral infection causing cyanotic (dark purple) comb, facial edema, and acute mortality.",
            "ជំងឺវីរុសកាចសាហាវ បណ្តាលឱ្យសិរប្រែជាពណ៌ស្វាយ ហើមមុខ ពិបាកដកដង្ហើម និងងាប់ភ្លាមៗ។",
            "Immediate quarantine, notify veterinary authorities, do not consume infected meat, and practice strict biosecurity.",
            "ធ្វើចត្តាឡីស័កជាបន្ទាន់ រាយការណ៍ជូនមន្ត្រីបសុពេទ្យ និងអនុវត្តវិធានការជីវសុវត្ថិភាពយ៉ាងតឹងរ៉ឹង។",
            cats["Viral"],
        ),
    ]

    dis = {}
    for name, name_km, desc, desc_km, treat, treat_km, cat in disease_data:
        d = _get_or_create(Disease, name=name, defaults={
            "name_km": name_km,
            "description": desc,
            "description_km": desc_km,
            "treatment": treat,
            "treatment_km": treat_km,
            "category_id": cat.id,
        })
        d.name_km = name_km
        d.description = desc
        d.description_km = desc_km
        d.treatment = treat
        d.treatment_km = treat_km
        d.category_id = cat.id
        dis[name] = d
    db.session.flush()

    # 4. Rules
    rule_specs = [
        # Infectious Bronchitis
        (
            "Infectious Bronchitis - Full Pattern",
            "ជំងឺរលាកទងសួតឆ្លង - ទម្រង់ពេញលេញ",
            "Coughing, sneezing, nasal discharge, and drop in egg production.",
            "ក្អក កណ្តាស់ ហៀរសំបោរ និងធ្លាក់ចុះការបញ្ចេញពង។",
            1, 95.0, dis["Infectious Bronchitis"],
            ["Coughing", "Sneezing", "Nasal discharge", "Decreased egg production"],
        ),
        (
            "Infectious Bronchitis - Respiratory Signs",
            "ជំងឺរលាកទងសួតឆ្លង - សញ្ញាផ្លូវដង្ហើម",
            "Coughing, sneezing, and labored breathing.",
            "ក្អក កណ្តាស់ និងដកដង្ហើមពិបាក។",
            2, 85.0, dis["Infectious Bronchitis"],
            ["Coughing", "Sneezing", "Labored breathing"],
        ),
        # Newcastle Disease
        (
            "Newcastle - Neurological Pattern",
            "ជំងឺញូកាសល - ទម្រង់ប្រព័ន្ធប្រសាទ",
            "Neck twisting, greenish diarrhea, paralysis, and lethargy.",
            "រមួលក រាគពណ៌បៃតង ខ្វិន និងស្ពឹកស្រពន់។",
            1, 95.0, dis["Newcastle Disease"],
            ["Neck twisting", "Greenish diarrhea", "Paralysis", "Lethargy"],
        ),
        (
            "Newcastle - Respiratory & Nervous",
            "ជំងឺញូកាសល - សញ្ញាផ្លូវដង្ហើម និងប្រសាទ",
            "Neck twisting, labored breathing, and loss of appetite.",
            "រមួលក ដកដង្ហើមពិបាក និងមិនស៊ីចំណី។",
            2, 85.0, dis["Newcastle Disease"],
            ["Neck twisting", "Labored breathing", "Loss of appetite"],
        ),
        # Coccidiosis
        (
            "Coccidiosis - Acute Classical",
            "ជំងឺកុកស៊ីឌីយ៉ូស៊ីស - ទម្រង់ស្រួចស្រាវ",
            "Bloody diarrhea, lethargy, ruffled feathers, and loss of appetite.",
            "រាគមានឈាម ស្ពឹកស្រពន់ រោមច្របូកច្របល់ និងមិនស៊ីចំណី។",
            1, 95.0, dis["Coccidiosis"],
            ["Bloody diarrhea", "Lethargy", "Ruffled feathers", "Loss of appetite"],
        ),
        (
            "Coccidiosis - Intestinal Signs",
            "ជំងឺកុកស៊ីឌីយ៉ូស៊ីស - សញ្ញាពោះវៀន",
            "Bloody diarrhea and lethargy.",
            "រាគមានឈាម និងស្ពឹកស្រពន់។",
            2, 85.0, dis["Coccidiosis"],
            ["Bloody diarrhea", "Lethargy"],
        ),
        # Fowl Cholera
        (
            "Fowl Cholera - Acute Signs",
            "ជំងឺអាសន្នរោគបក្សី - ទម្រង់ស្រួចស្រាវ",
            "Swollen face, labored breathing, greenish diarrhea, and lethargy.",
            "ហើមមុខ / ភ្នែក ដកដង្ហើមពិបាក រាគពណ៌បៃតង និងស្ពឹកស្រពន់។",
            1, 90.0, dis["Fowl Cholera"],
            ["Swollen face / eyes", "Labored breathing", "Greenish diarrhea", "Lethargy"],
        ),
        (
            "Fowl Cholera - Facial Swelling Pattern",
            "ជំងឺអាសន្នរោគបក្សី - សញ្ញាហើមមុខ",
            "Swollen face and ruffled feathers.",
            "ហើមមុខ / ភ្នែក និងរោមច្របូកច្របល់។",
            2, 80.0, dis["Fowl Cholera"],
            ["Swollen face / eyes", "Ruffled feathers"],
        ),
        # Marek's Disease
        (
            "Marek's - Paralysis Pattern",
            "ជំងឺម៉ារ៉ិក - ទម្រង់ខ្វិន",
            "Leg weakness, paralysis, and loss of appetite.",
            "ខ្វិនជើង / ពិបាកដើរ ខ្វិន និងមិនស៊ីចំណី។",
            1, 92.0, dis["Marek's Disease"],
            ["Lameness / Leg weakness", "Paralysis", "Loss of appetite"],
        ),
        (
            "Marek's - Lameness & Lethargy",
            "ជំងឺម៉ារ៉ិក - សញ្ញាជើងទន់ និងអស់កម្លាំង",
            "Lameness and lethargy.",
            "ខ្វិនជើង / ពិបាកដើរ និងស្ពឹកស្រពន់។",
            2, 80.0, dis["Marek's Disease"],
            ["Lameness / Leg weakness", "Lethargy"],
        ),
        # Infectious Coryza
        (
            "Infectious Coryza - Facial & Nasal",
            "ជំងឺផ្តាសាយឆ្លង - សញ្ញាហើមមុខ និងហៀរសំបោរ",
            "Swollen face, nasal discharge, and sneezing.",
            "ហើមមុខ / ភ្នែក ហៀរសំបោរ និងកណ្តាស់។",
            1, 90.0, dis["Infectious Coryza"],
            ["Swollen face / eyes", "Nasal discharge", "Sneezing"],
        ),
        # Avian Influenza
        (
            "Avian Influenza - Severe Acute",
            "ជំងឺផ្តាសាយបក្សី - ទម្រង់ធ្ងន់ធ្ងរ",
            "Comb cyanosis (dark comb), swollen face, labored breathing, and lethargy.",
            "សិរពណ៌ស្វាយ / ស្លេក ហើមមុខ / ភ្នែក ដកដង្ហើមពិបាក និងស្ពឹកស្រពន់។",
            1, 95.0, dis["Avian Influenza"],
            ["Comb cyanosis / Dark comb", "Swollen face / eyes", "Labored breathing", "Lethargy"],
        ),
    ]

    for title, title_km, desc, desc_km, priority, confidence, disease_obj, symptom_names in rule_specs:
        rule = _get_or_create(Rule, title=title, disease_id=disease_obj.id, defaults={
            "title_km": title_km,
            "description": desc,
            "description_km": desc_km,
            "priority": priority,
            "confidence": confidence,
        })
        rule.title_km = title_km
        rule.description = desc
        rule.description_km = desc_km
        rule.priority = priority
        rule.confidence = confidence
        rule.symptoms = [syms[s_name] for s_name in symptom_names if s_name in syms]

    db.session.commit()
    print("Seeded expert system data successfully!")


def seed_all():
    seed_permissions_and_roles()
    seed_admin_user()
    seed_expert_data()

