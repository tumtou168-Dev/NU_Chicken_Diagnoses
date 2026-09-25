# app/services/field_guide_seed.py
"""Diseases, symptoms and rules from two field sources:

- the local chicken-raising guide (ឯកសារស្រាវជ្រាវគំរូបច្ចេកទេសចិញ្ចឹមមាន់ស្រុក, section ៣.៨, pages ១៤-១៧)
- the Module 13 deck "ជំងឺមាន់៖ រោគវិនិច្ឆ័យ និង ការព្យាបាល" (slides 26-68; vitamin treatments are general practice)

Where both cover a disease, its treatment text merges the two.

Safe to run again and on an existing database: a symptom is reused when it exists under any of
its names, so older databases (e.g. "Swollen face" instead of "Swollen face / eyes") get no duplicates.

Apply to a running database:  python -m app.services.field_guide_seed
"""
from extensions import db
from app.models.expert_system import Category, Symptom, Disease, Rule


# name -> name_km, for categories created here when missing
CATEGORIES = {
    "Respiratory": "ផ្លូវដង្ហើម",
    "Digestive": "ប្រព័ន្ធរំលាយអាហារ",
    "Neurological": "ប្រព័ន្ធប្រសាទ",
    "Bacterial": "បាក់តេរី",
    "Viral": "វីរុស",
    "Skin & Feathers": "ស្បែក និងរោម",
    "Nutritional": "កង្វះអាហារូបត្ថម្ភ",
}

# (names — the first is used when creating, name_km, description, description_km)
SYMPTOMS = {
    "sneezing": (["Sneezing"], "កណ្តាស់", "Frequent sneezing or head shaking", "មាន់កណ្តាស់ ឬក្រវីក្បាលញឹកញាប់"),
    "coughing": (["Coughing"], "ក្អក", "Frequent coughing or hacking sounds", "មាន់ក្អក ឬបញ្ចេញសំឡេងស្អកញឹកញាប់"),
    "nasal": (["Nasal discharge"], "ហៀរសំបោរ", "Clear or thick mucus discharge from nostrils", "ហៀរសំបោរថ្លា ឬខាប់ចេញពីច្រមុះ"),
    "breathing": (["Labored breathing"], "ដកដង្ហើមពិបាក", "Breathing with open mouth and gasping for air", "ដកដង្ហើមហត់ ហាមាត់ និងដង្ហក់យកខ្យល់"),
    "face": (["Swollen face / eyes", "Swollen face"], "ហើមមុខ / ភ្នែក", "Swelling around eyes, head, or wattles", "ហើមជុំវិញភ្នែក ក្បាល ឬសិរក្រោម"),
    "bloody": (["Bloody diarrhea"], "រាគមានឈាម", "Droppings with red mucus or blood", "លាមកមានស្លេសពណ៌ក្រហម ឬមានឈាម"),
    "green": (["Greenish diarrhea"], "រាគពណ៌បៃតង", "Watery green droppings", "លាមករាគទឹកពណ៌បៃតង (ខៀវ)"),
    "watery": (["Watery diarrhea", "Diarrhea"], "រាគទឹក", "Loose, watery or wet droppings", "លាមករាគរាវ ឬសើម"),
    "lethargy": (["Lethargy"], "ស្ពឹកស្រពន់ / អស់កម្លាំង", "Inactive, huddled, eyes closed, low energy", "មិនសូវកម្រើក សំកុក បិទភ្នែកសំងំដេក"),
    "feathers": (["Ruffled feathers"], "រោមបះ", "Fluffed, unkempt, or messy plumage", "រោមបះ ក្រញុញ មិនរលោង"),
    "appetite": (["Loss of appetite"], "ស៊ីចំណីថយចុះ", "Eating less or refusing feed", "ស៊ីចំណីតិច ឬមិនស៊ីចំណី"),
    "eggs": (["Decreased egg production"], "ពងធ្លាក់ចុះ", "Sudden drop in egg laying rate", "ការធ្លាក់ចុះភ្លាមៗនៃបរិមាណពង"),
    "neck": (["Neck twisting"], "រមួលក", "Twisted neck or head tremors", "រមួលក ឬក្បាលញ័រ"),
    "eyes": (["Watery eyes"], "ហៀរទឹកភ្នែក", "Constant tearing from the eyes", "ហៀរទឹកភ្នែកជាប្រចាំ"),
    "joints": (["Swollen joints / feet"], "ហើមបាតជើង / សន្លាក់", "Swollen foot pads or joints, often with lameness", "ហើមបាតជើង សន្លាក់ជើង និងខ្វិន"),
    "weight": (["Weight loss"], "ស្រកទម្ងន់លឿន", "Rapid loss of body weight and poor growth", "ស្រកទម្ងន់លឿន និងលូតលាស់យឺត"),
    "noisy": (["Noisy breathing"], "ដកដង្ហើមឮសូរ", "Rattling or wheezing sound when breathing", "ដកដង្ហើមឮសូរសំឡេង"),
    "chicks": (["High chick mortality"], "កូនមាន់ងាប់ច្រើន", "Many young chicks dying", "អត្រាស្លាប់ខ្ពស់ចំពោះកូនមាន់"),
    "paralysis": (["Paralysis"], "ខ្វិន", "Loss of movement in wings or legs", "ខ្វិនស្លាប ឬជើង"),
    "lame": (["Lameness / Leg weakness", "Lameness"], "ខ្វិនជើង / ពិបាកដើរ", "Difficulty walking or standing", "ពិបាកដើរ ជើងទន់ ឬដួល"),
    "comb": (["Comb cyanosis / Dark comb"], "សិរពណ៌ស្វាយ / ស្លេក", "Swollen, bruised, bluish or dark comb and wattles", "ហើម ជាំឈាម ឬសិរ និងលេងប្រែពណ៌ស្វាយ"),
    "sudden_death": (["Sudden death"], "ងាប់ភ្លាមៗ", "Birds healthy one day and dead the next, many at once", "មាន់មានសុខភាពល្អ ហើយស្រាប់តែងាប់ច្រើនក្បាលភ្លាមៗ"),
    "wings": (["Drooping wings"], "ធ្លាក់ស្លាប", "Wings hang down loosely", "ស្លាបធ្លាក់ចុះ មិនអាចលើកបាន"),
    "leg_bruise": (["Bruised legs"], "ជាំឈាមនៅជើង", "Red-purple bleeding spots under the leg skin", "ជាំឈាមពណ៌ក្រហមស្វាយនៅក្រោមស្បែកជើង"),
    "eye_pus": (["Pus in eyes"], "ភ្នែកមានខ្ទុះ", "Pus or crust in the eyes", "មានខ្ទុះ ឬកករនៅក្នុងភ្នែក"),
    "neck_stretch": (["Gasping with neck stretched"], "លាតកដកដង្ហើម", "Stretches the neck up to gasp for air", "លាតក និងចង្កាឡើងដើម្បីដកដង្ហើម"),
    "blood_cough": (["Coughing up blood"], "ក្អកចេញឈាម", "Coughs up blood and mucus from the windpipe", "ក្អកចេញឈាម និងស្លេសពីបំពង់ខ្យល់"),
    "shell": (["Misshapen or thin-shelled eggs"], "ពងខុសទ្រង់ទ្រាយ", "Wrinkled, thin or misshapen shells with watery whites", "សំបកពងស្តើង ជ្រួញ ខុសទ្រង់ទ្រាយ ហើយសស៊ុតរាវ"),
    "thirst": (["Increased thirst"], "ស្រេកទឹក", "Drinks much more water than usual", "ផឹកទឹកច្រើនជាងធម្មតា"),
    "white_diarrhea": (["White diarrhea"], "រាគពណ៌ស", "White or whitish-yellow watery droppings", "លាមករាគទឹកពណ៌ស ឬសលឿង"),
    "vent": (["Soiled vent feathers"], "លាមកស្អិតគូទ", "Droppings stuck to the feathers around the vent", "លាមកស្អិតជាប់រោមជុំវិញគូទ"),
    "worms": (["Worms in droppings"], "មានព្រូនក្នុងលាមក", "Worms visible in the droppings", "ឃើញព្រូនក្នុងលាមក"),
    "limp_neck": (["Limp neck / drooping eyelids"], "ទន់ក / ធ្លាក់ត្របកភ្នែក", "Cannot hold the head up; eyelids droop", "មិនអាចងើបក្បាល ត្របកភ្នែកធ្លាក់"),
    "skin_scabs": (["Scabs on comb / face"], "ដុំពកលើសិរ / មុខ", "Wart-like scabs on featherless skin that grow into yellow crusts", "ដុំពកដូចឬសលើស្បែកគ្មានរោម រីកធំ ពណ៌លឿង មានក្រមរក្រៀម"),
    "mouth_lesions": (["Yellow lesions in mouth / throat"], "ដំបៅក្នុងមាត់ / បំពង់ក", "Yellow patches in the mouth, gullet or windpipe", "ស្នាមពណ៌លឿងក្នុងមាត់ បំពង់អាហារ ឬបំពង់ខ្យល់"),
    "lice": (["Lice or mites in feathers"], "មានចៃ / ស្រមើរ", "Small insects in the feathers, often around the vent", "មានចៃ ឬស្រមើរក្នុងរោម ជាពិសេសជុំវិញគូទ"),
    "restless": (["Restless / itchy"], "មិនស្ងៀម / រមាស់", "Restless, scratching, sleeps badly", "មិនស្ងៀម រមាស់ ដេកមិនស្រួល"),
    "pecking": (["Pecking wounds"], "របួសដោយចឹកគ្នា", "Bleeding wounds from being pecked by other birds", "មានរបួស ឬហូរឈាមដោយសារមាន់ចឹកគ្នា"),
    "splayed": (["Legs splayed (one forward, one back)"], "ជើងលាតសន្ធឹងទៅមុខ និងក្រោយ", "One leg stretched forward and the other back", "ជើងមួយលាតទៅមុខ ជើងមួយទៀតលាតទៅក្រោយ"),
    "eyelids_stuck": (["Eyelids stuck together"], "ត្របកភ្នែកស្អិតជាប់គ្នា", "Sores on the eyes; the eyelids stick together", "មានស្លាកស្នាមលើភ្នែក ត្របកភ្នែកស្អិតជាប់គ្នា"),
    "feathers_black": (["Red / brown feathers turning black"], "រោមក្រហម / ត្នោតប្រែជាខ្មៅ", "Red or brown feathers turn black", "រោមពណ៌ក្រហម ឬត្នោត ប្រែជាពណ៌ខ្មៅ"),
    "eye_beak_scabs": (["Scabs around eyes and beak"], "ក្រមរក្រៀមជុំវិញភ្នែក និងចំពុះ", "Crusty scabs around the eyes and beak", "មានក្រមរក្រៀមនៅជុំវិញភ្នែក និងចំពុះ"),
    "cracked_feet": (["Dry, cracked foot soles"], "បាតជើងស្ងួត បែកក្រហែង", "Foot soles dry, cracked and wrinkled, sometimes bruised", "បាតជើងស្ងួត បែកក្រហែង និងក្រិន ជួនមានជាំឈាម"),
}

# name (existing diseases are matched on it), name_km and category (both used only when creating),
# description, description_km, treatment, treatment_km
DISEASES = [
    (
        "Infectious Bronchitis", "ជំងឺរលាកទងសួតឆ្លង", "Respiratory",
        "Viral disease that infects chickens of all ages and spreads fast from flock to flock, but kills few. "
        "Signs: sneezing, watery diarrhea (kidney/variant strains) and a sharp drop in egg production.",
        "ជំងឺបង្កដោយវីរុស ឆ្លងលើមាន់គ្រប់អាយុ ចម្លងលឿនពីហ្វូងមួយទៅហ្វូងមួយ ប៉ុន្តែអត្រាស្លាប់ទាប។ "
        "រោគសញ្ញា៖ កណ្តាស់ រាគទឹក (ប្រភេទខូចក្រលៀន) និងពងធ្លាក់ចុះខ្លាំង។",
        "Amoxicillin + Enrofloxacin, or Amoxicillin + Colistin, for 3 days in a row. "
        "Then give vitamins, minerals and electrolytes for the next 3 days.",
        "ប្រើ Amoxicillin + Enrofloxacin ឬ Amoxicillin + Colistin ចំនួន ៣ថ្ងៃជាប់ៗគ្នា។ "
        "បន្ទាប់មកប្រើវីតាមីន មីណេរ៉ាល់ និងអេឡិចត្រូលីត ចំនួន ៣ថ្ងៃបន្ទាប់។",
    ),
    (
        "Coccidiosis", "ជំងឺកុកស៊ីដ្យូស៊ីស", "Digestive",
        "Protozoan intestinal disease spread through dirty water and feed and frequent weather changes. "
        "Signs: wet droppings with red mucus, rapid weight loss, poor growth and reduced feed intake.",
        "ជំងឺបង្កដោយពពួកប្រូតូស័រ ឆ្លងតាមរយៈទឹក ចំណីកខ្វក់ និងការផ្លាស់ប្តូរអាកាសធាតុញឹកញាប់។ "
        "រោគសញ្ញា៖ លាមកសើមមានស្លេសពណ៌ក្រហម ស្រកទម្ងន់លឿន លូតលាស់យឺត និងស៊ីចំណីថយចុះ។",
        "Sulfa 33 (Sulfadimerazine) 10 ml per litre of drinking water for 3 days, Amprolium, or "
        "Trimethoprim/Sulfonamides + Amoxicillin. If the last batch had it, give Toltrazuril on days 13-15. Keep litter dry.",
        "ប្រើ Sulfa 33 (Sulfadimerazine) ១០ ម.ល ក្នុងទឹក ១លីត្រ ឱ្យផឹក ៣ថ្ងៃ ឬ Amprolium ឬ "
        "Trimethoprim/Sulfonamides + Amoxicillin។ បើវគ្គមុនមានជំងឺនេះ ឱ្យ Toltrazuril ថ្ងៃទី១៣-១៥។ រក្សាកម្រាលឱ្យស្ងួត។",
    ),
    (
        "Newcastle Disease", "ជំងឺញូវកាស", "Viral",
        "Viral disease with no cure that spreads fast through the air, direct contact and shared farm equipment. "
        "Signs: sneezing, green diarrhea, twisted neck, reduced feed intake, shriveled face and legs.",
        "ជំងឺបង្កដោយវីរុស គ្មានថ្នាំព្យាបាល ឆ្លងរហ័សតាមខ្យល់ ការប៉ះពាល់ផ្ទាល់ និងសម្ភារៈក្នុងកសិដ្ឋាន។ "
        "រោគសញ្ញា៖ កណ្តាស់ រាគពណ៌ខៀវ រមួលក ស៊ីចំណីថយចុះ មុខ និងជើងស្វិត។",
        "No treatment (virus). Vaccinate with I2 eye drops at 1 day old and again 3 weeks later (protects over "
        "6 months). Keep new birds apart for 2 weeks. For vaccine reactions give Paracetamol.",
        "គ្មានការព្យាបាលទេ ព្រោះបង្កដោយវីរុស។ បន្តក់វ៉ាក់សាំង I2 តាមភ្នែកពេលមាន់អាយុ ១ថ្ងៃ និងរំលឹក ៣សប្តាហ៍ក្រោយ "
        "(ការពារលើស ៦ខែ)។ ក្រុងមាន់ថ្មី ២សប្តាហ៍។ បើមានប្រតិកម្មវ៉ាក់សាំង ប្រើ Paracetamol។",
    ),
    (
        "Mycoplasmosis", "ជំងឺមីកូប្លាស្មា", "Respiratory",
        "Bacterial disease common in dirty houses with poor ventilation. Signs: swollen face and eyelids, "
        "thick nasal discharge, constant tearing, labored breathing, swollen feet/joints and lameness.",
        "ជំងឺបង្កដោយបាក់តេរី កើតច្រើននៅកន្លែងមិនស្អាត ខ្យល់ចេញចូលមិនល្អ។ រោគសញ្ញា៖ ហើមមុខ "
        "និងត្របកភ្នែក ហៀរសំបោរខាប់ ហៀរទឹកភ្នែកជាប្រចាំ ពិបាកដកដង្ហើម ហើមបាតជើង សន្លាក់ និងខ្វិន។",
        "Tylosin, Erythromycin, Chlortetracycline or Enrofloxacin in drinking water for 7 days, plus a tonic "
        "(AD3E, B-complex). Give a fever reducer first if fever is high. Farms: Tylosin + vitamin C for 7 days on arrival.",
        "ប្រើ Tylosin, Erythromycin, Chlortetracycline ឬ Enrofloxacin លាយទឹកឱ្យផឹក ៧ថ្ងៃ និងថ្នាំប៉ូវកម្លាំង "
        "(AD3E, B-complex)។ បើក្តៅខ្លួនខ្លាំង ប្រើថ្នាំបញ្ចុះកម្តៅមុន។ កសិដ្ឋាន៖ Tylosin + វីតាមីន C ៧ថ្ងៃពេលមកដល់។",
    ),
    (
        "Colibacillosis", "ជំងឺកូលីបាក់ស៊ីឡូស៊ីស", "Bacterial",
        "Bacterial disease of stressed birds, often after Mycoplasma or Bronchitis, spread by dirty feed and "
        "water. Signs: diarrhea, huddling with closed eyes, ruffled feathers, noisy breathing, many chick deaths.",
        "ជំងឺបង្កដោយបាក់តេរី កើតពេលសត្វស្ត្រេស ច្រើនតាមក្រោយជំងឺមីកូប្លាស្មា ឬរលាកទងសួត ឆ្លងតាមចំណី "
        "ទឹកគ្មានអនាម័យ។ រោគសញ្ញា៖ រាគ សំកុកបិទភ្នែក រោមបះ ដកដង្ហើមឮសូរ និងកូនមាន់ងាប់ច្រើន។",
        "Enrofloxacin or Tetracycline for 3 to 5 days. Treatment does not work unless the farm "
        "provides clean water, clean feed and a clean, hygienic house.",
        "ប្រើ Enrofloxacin ឬ Tetracycline រយៈពេល ៣ ទៅ ៥ថ្ងៃ។ ការព្យាបាលគ្មានប្រសិទ្ធភាពទេ "
        "បើមិនផ្តល់ទឹកស្អាត ចំណីស្អាត និងទីជម្រកស្អាតមានអនាម័យ។",
    ),
    # ---- from the Module 13 deck ----
    (
        "Avian Influenza", "ជំងឺផ្តាសាយបក្សី", "Viral",
        "Viral disease; suspect it when many birds die fast. Signs: labored breathing, paralysis and head "
        "trembling, swollen or bruised comb and wattles, bruised legs, not eating, huddling, ruffled feathers.",
        "ជំងឺបង្កដោយវីរុស។ បើមាន់ងាប់ច្រើន និងលឿន ត្រូវគិតដល់ជំងឺនេះ។ រោគសញ្ញា៖ ពិបាកដកដង្ហើម ខ្វិន ញ័រក្បាល "
        "ហើម/ជាំឈាមនៅសិរ និងលេង ជាំឈាមនៅជើង មិនស៊ីចំណី សំកុក រោមបះ។",
        "Do not cut open dead birds. Call a vet or the National Veterinary Research Institute (012 833-795 / "
        "012 214-970). Isolate sick birds, burn or bury dead ones, disinfect the coop, never sell sick birds.",
        "កុំវះកាត់សាកសព។ ទូរស័ព្ទទៅពេទ្យសត្វ ឬវិទ្យាស្ថានជាតិស្រាវជ្រាវបសុព្យាបាល (012 833-795 / 012 214-970)។ "
        "ញែកបក្សីឈឺ ដុត ឬកប់បក្សីងាប់ សម្អាតទ្រុង និងមិនលក់បក្សីឈឺ។",
    ),
    (
        "Infectious Laryngotracheitis", "ជំងឺរលាកបំពង់សំលេង និងបំពង់ខ្យល់", "Respiratory",
        "Viral disease of the larynx and windpipe. Signs: severe gasping, stretching the neck up to breathe, "
        "coughing, and coughing up blood and mucus. The windpipe is filled with blood.",
        "ជំងឺបង្កដោយវីរុស លើបំពង់សំលេង និងបំពង់ខ្យល់។ រោគសញ្ញា៖ ថប់ដង្ហើមខ្លាំង លាតកដកដង្ហើម ក្អក "
        "និងក្អកចេញឈាម និងស្លេស។ បំពង់ខ្យល់មានឈាម។",
        "The guide gives no drug: antibiotics do not work against viruses. Isolate sick birds and follow "
        "biosecurity: clean the coop and keep new birds apart for 14 days.",
        "ឯកសារមិនមានថ្នាំព្យាបាលទេ ព្រោះអង់ទីប៊ីយ៉ូទិកមិនមានប្រសិទ្ធភាពលើវីរុស។ ញែកមាន់ឈឺ "
        "និងអនុវត្តជីវសុវត្ថិភាព៖ សម្អាតទ្រុង ដាក់មាន់ថ្មីដាច់ដោយឡែក ១៤ថ្ងៃ។",
    ),
    (
        "Infectious Coryza", "ជំងឺកូរីសា", "Respiratory",
        "Bacterial disease; older birds catch it more easily. Signs: heavy nasal discharge, sneezing, sometimes "
        "a swollen face, but no serious breathing trouble. Spread by sick birds, carriers and dirty drinking water.",
        "ជំងឺបង្កដោយបាក់តេរី សត្វកាន់តែចាស់កាន់តែងាយឆ្លង។ រោគសញ្ញា៖ ហៀរសំបោរខ្លាំង កណ្តាស់ ជួនហើមមុខ "
        "តែមិនមានបញ្ហាដកដង្ហើមធ្ងន់ធ្ងរទេ។ ឆ្លងតាមការប៉ះពាល់សត្វឈឺ និងទឹកផឹកមានមេរោគ។",
        "Erythromycin and Oxytetracycline in drinking water for 5 days. In severe cases (birds not eating), "
        "inject Oxytetracycline.",
        "ប្រើ Erythromycin និង Oxytetracycline លាយក្នុងទឹកឱ្យផឹករយៈពេល ៥ថ្ងៃ។ ករណីធ្ងន់ធ្ងរ (មិនស៊ីចំណី) "
        "ត្រូវចាក់ Oxytetracycline។",
    ),
    (
        "Fowl Cholera", "ជំងឺអាសន្នរោគ", "Bacterial",
        "Pasteurella bacteria, often with Mycoplasma, parasites, poor nutrition or hygiene. Signs: sudden "
        "death, swollen wattles, sinuses, feet and joints, pus in the eyes, gasping, discharge from nose and mouth.",
        "ជំងឺបង្កដោយបាក់តេរី ប៉ាស្ទឺរេឡា ច្រើនកើតជាមួយមីកូប្លាស្មា បរាសិត កង្វះជីវជាតិ និងអនាម័យ។ រោគសញ្ញា៖ "
        "ងាប់លឿន ហើមលេង ខ្ទង់ច្រមុះ បាតជើង សន្លាក់ ភ្នែកមានខ្ទុះ ដង្ហក់ ហៀរសំបោរពីច្រមុះ និងមាត់។",
        "Inject Oxytetracycline 50 mg per bird and mix Tetracycline into feed for 30 days. Bury dead birds. "
        "The bacteria live for months in wet places, so clean up and let the sun dry the area.",
        "ចាក់ Oxytetracycline ៥០ ម.ក្រ/ក្បាល និងលាយ Tetracycline ក្នុងចំណីឱ្យស៊ី ៣០ថ្ងៃ។ កប់សាកសពមាន់ងាប់។ "
        "បាក់តេរីរស់បានច្រើនខែនៅកន្លែងសើម ដូច្នេះត្រូវសម្អាត និងហាលថ្ងៃ។",
    ),
    (
        "Marek's Disease", "ជំងឺម៉ារ៉ិក", "Neurological",
        "Viral tumour disease. Signs: leg paralysis with legs splayed in opposite directions (one forward, one "
        "back). Inside: enlarged nerves, mainly behind the legs, and tumours in liver, spleen, kidneys, heart, lungs.",
        "ជំងឺមហារីកបង្កដោយវីរុស។ រោគសញ្ញា៖ ខ្វិនជើង ជើងលាតសន្ធឹងទៅទិសផ្សេងគ្នា (មួយទៅមុខ មួយទៅក្រោយ)។ "
        "ខាងក្នុង៖ សរសៃប្រសាទរីកធំ និងមានដុំពកនៅថ្លើម ផាល តម្រងនោម បេះដូង សួត។",
        "No treatment. Prevent by vaccination.",
        "គ្មានការព្យាបាល។ ការពារដោយចាក់វ៉ាក់សាំង។",
    ),
    (
        "Salmonellosis", "ជំងឺសាល់ម៉ូណេឡូស៊ីស", "Bacterial",
        "Salmonella bacteria. Pullorum: chicks under 2 weeks, white-yellow diarrhea, pasted vents, not eating, "
        "head hanging down. Typhoid: adult birds, not eating, huddling, yellow to green diarrhea.",
        "បាក់តេរីសាល់ម៉ូណេឡា។ ប្រភេទ Pullorose៖ កូនមាន់អាយុក្រោម ២សប្តាហ៍ រាគពណ៌សលឿង លាមកស្អិតជាប់គូទ "
        "មិនស៊ីចំណី ក្បាលចុះក្រោម។ ប្រភេទ Typhose៖ មាន់ធំ មិនស៊ីចំណី សំកុក រាគពណ៌លឿងទៅខៀវ។",
        "Enrofloxacin. It spreads through eggs and contact with carrier birds, and can infect people: "
        "cook chicken meat and eggs thoroughly.",
        "ប្រើ Enrofloxacin។ ឆ្លងតាមស៊ុត និងការប៉ះពាល់សត្វផ្ទុកមេរោគ ហើយអាចឆ្លងមនុស្ស៖ "
        "ត្រូវចម្អិនសាច់មាន់ និងស៊ុតឱ្យឆ្អិនល្អ។",
    ),
    (
        "Gumboro Disease", "ជំងឺហ្គុំបូរ៉ូ", "Viral",
        "Viral disease, mostly in chickens under 10 weeks. Signs: severe weakness (cannot hold themselves up), "
        "watery white diarrhea, soiled and inflamed vent. Inside: swollen yellow bursa, sometimes bloody.",
        "ជំងឺបង្កដោយវីរុស ច្រើនកើតលើមាន់អាយុក្រោម ១០សប្តាហ៍។ រោគសញ្ញា៖ អស់កម្លាំងខ្លាំង រាគទឹកពណ៌ស "
        "ប្រឡាក់រោមគូទ និងរលាកគូទ។ ខាងក្នុង៖ ថង់គូទហើម ពណ៌លឿង ជួនមានឈាម។",
        "No treatment, though some birds recover. Prevent by vaccination.",
        "គ្មានការព្យាបាលទេ តែសត្វខ្លះអាចជា។ ការពារដោយចាក់វ៉ាក់សាំង។",
    ),
    (
        "Internal Parasites (Roundworms)", "បរាសិតខាងក្នុង (ព្រូន)", "Digestive",
        "Roundworms (Ascaris) and tapeworms. Signs: slow growth, few eggs, and birds catch other diseases "
        "easily. Worms may be seen in the droppings.",
        "ព្រូនមូល (Ascaris) និងតេនញ៉ា។ រោគសញ្ញា៖ លូតលាស់យឺត ពងបានតិច និងងាយទទួលជំងឺ។ អាចឃើញព្រូនក្នុងលាមក។",
        "Tetramisole (100 mg for a 2 kg chicken), or Piperazine or Levamisole.",
        "ប្រើ Tetramisole (មាន់ទម្ងន់ ២គីឡូក្រាម ប្រើ ១០០ មីលីក្រាម) ឬ Piperazine ឬ Levamisole។",
    ),
    (
        "Botulism", "ជំងឺបូទុយលីស", "Neurological",
        "Poisoning by Clostridium botulinum toxin, usually from eating maggots on rotting carcasses. Signs: weak "
        "legs, drooping wings, limp neck and drooping eyelids; weakness starts in the legs and moves upward.",
        "ការពុលដោយជាតិពុលបាក់តេរី Clostridium botulinum ច្រើនដោយសារស៊ីដង្កូវលើសាកសពរលួយ។ រោគសញ្ញា៖ "
        "ទន់ជើង ធ្លាក់ស្លាប ទន់ក និងធ្លាក់ត្របកភ្នែក ចាប់ផ្តើមពីជើង រួចឡើងទៅស្លាប ក និងត្របកភ្នែក។",
        "Treatment rarely works; Pen-Strep can be tried. Prevent by collecting and burying dead animals.",
        "ការព្យាបាលមិនសូវមានប្រសិទ្ធភាពទេ អាចប្រើ Pen-Strep។ ការពារដោយប្រមូល និងកប់សាកសពសត្វ។",
    ),
    (
        "Fowl Pox", "ជំងឺអុតមាន់", "Skin & Feathers",
        "Viral disease. Signs: wart-like scabs on featherless skin that grow and merge into yellow crusts. Wet "
        "form: yellow lesions in the mouth, gullet and windpipe that make breathing hard. Spread by wounds and mosquitoes.",
        "ជំងឺបង្កដោយវីរុស។ រោគសញ្ញា៖ ដុំពកលើស្បែកគ្មានរោម រីកធំ ពណ៌លឿង មានក្រមរក្រៀម។ ទម្រង់សើម៖ "
        "ស្នាមក្នុងមាត់ បំពង់អាហារ និងបំពង់ខ្យល់ ធ្វើឱ្យពិបាកដកដង្ហើម។ ឆ្លងតាមរបួស និងមូស។",
        "No treatment. Vaccinate by wing-web stab from 10 days old. The vaccine is live, so vaccinate only healthy birds.",
        "គ្មានការព្យាបាលទេ។ ចាក់វ៉ាក់សាំងដោយជួសស្លាប ពេលមាន់អាយុចាប់ពី ១០ថ្ងៃ។ "
        "វ៉ាក់សាំងនេះជាវ៉ាក់សាំងរស់ ដូច្នេះចាក់តែមាន់ដែលមានសុខភាពល្អ។",
    ),
    (
        "External Parasites (Lice & Mites)", "បរាសិតខាងក្រៅ (ចៃ ស្រមើរ)", "Skin & Feathers",
        "Mostly lice, which damage the skin. Birds are restless, eat less and sleep badly, leading to slow "
        "growth, fewer eggs and more disease. Check the feathers around the vent.",
        "ភាគច្រើនជាចៃ ដែលធ្វើឱ្យដាច់រលាត់ស្បែក។ មាន់មិនស្ងៀម មិនសូវស៊ី ដេកមិនស្រួល ធ្វើឱ្យលូតលាស់យឺត "
        "ពងបានតិច និងងាយទទួលជំងឺ។ ពិនិត្យរោមជុំវិញគូទ។",
        "Dust birds with Malathion 5% and repeat every 3 months. Clean the nests too.",
        "ប្រើ Malathion 5% បាញ់ផ្ទាល់លើមាន់ ហើយរំលឹករៀងរាល់ ៣ខែម្តង។ ត្រូវសម្អាតសំបុកផងដែរ។",
    ),
    (
        "Feather Pecking (Cannibalism)", "ការចឹកគ្នា", "Skin & Feathers",
        "Birds peck each other, sometimes to death, often from 2-3 weeks old before full feathering; worse once "
        "there are wounds. Causes: lack of protein, salt or minerals, internal parasites, crowding.",
        "មាន់ចឹកគ្នារហូតដល់ស្លាប់ ច្រើនចាប់ផ្តើមពេលអាយុ ២-៣សប្តាហ៍ មុនដុះរោមពេញ ហើយកាន់តែខ្លាំងបើមានរបួស។ "
        "បុព្វហេតុ៖ កង្វះប្រូតេអ៊ីន អំបិល សារធាតុរ៉ែ បរាសិតខាងក្នុង និងទីកន្លែងចង្អៀត។",
        "Trim beaks, feed a high-protein diet and give the birds enough space.",
        "កាត់ចំពុះ ផ្តល់ចំណីមានជាតិប្រូតេអ៊ីនខ្ពស់ និងទុកកន្លែងឱ្យបានធំទូលាយ។",
    ),
    # Vitamin deficiencies (slide 68). The deck gives signs only; the treatments are general practice, not from it.
    (
        "Vitamin A Deficiency", "កង្វះវីតាមីន A", "Nutritional",
        "Lack of vitamin A, which keeps the moist membranes healthy. Signs: sores on the eyes and eyelids "
        "stuck together. Poorly fed birds also catch opportunistic diseases easily.",
        "កង្វះវីតាមីន A ដែលជួយបង្កើតភ្នាសសើម។ រោគសញ្ញា៖ ស្លាកស្នាមនៅលើភ្នែក ត្របកភ្នែកស្អិតជាប់គ្នា។ "
        "មាន់ខ្វះជីវជាតិងាយឆ្លងជំងឺឱកាសនិយម។",
        "Not in the guide; general practice: give vitamin A or AD3E in drinking water and more green feed. "
        "Improve the diet, since poor nutrition lets other diseases in.",
        "ឯកសារមិនបានផ្តល់ការព្យាបាលទេ។ ជាទូទៅ៖ ផ្តល់វីតាមីន A ឬ AD3E ក្នុងទឹកផឹក និងបន្ថែមចំណីបន្លែបៃតង។ "
        "ត្រូវកែលម្អចំណី ព្រោះកង្វះជីវជាតិធ្វើឱ្យជំងឺផ្សេងៗងាយចូល។",
    ),
    (
        "Vitamin D Deficiency", "កង្វះវីតាមីន D", "Nutritional",
        "Lack of vitamin D. Sign: in chickens with red or brown feathers, the feathers turn black.",
        "កង្វះវីតាមីន D។ រោគសញ្ញា៖ មាន់ដែលមានរោមពណ៌ក្រហម និងត្នោត ប្រែជាពណ៌ខ្មៅ។",
        "Not in the guide; general practice: give vitamin D3 or AD3E in drinking water and let the birds "
        "out into the sunlight.",
        "ឯកសារមិនបានផ្តល់ការព្យាបាលទេ។ ជាទូទៅ៖ ផ្តល់វីតាមីន D3 ឬ AD3E ក្នុងទឹកផឹក "
        "និងឱ្យមាន់ចេញហាលថ្ងៃ។",
    ),
    (
        "Vitamin B Deficiency", "កង្វះវីតាមីន B", "Nutritional",
        "Lack of B vitamins. Signs: scabs around the eyes and beak; foot soles dry, cracked and wrinkled, "
        "sometimes with bruising.",
        "កង្វះវីតាមីន B។ រោគសញ្ញា៖ មានក្រមរក្រៀមនៅជុំវិញភ្នែក និងចំពុះ។ បាតជើងស្ងួត បែកក្រហែង និងក្រិន "
        "ជួនមានជាំឈាម។",
        "Not in the guide; general practice: give a vitamin B-complex supplement in drinking water and a "
        "balanced feed.",
        "ឯកសារមិនបានផ្តល់ការព្យាបាលទេ។ ជាទូទៅ៖ ផ្តល់វីតាមីន B-complex ក្នុងទឹកផឹក និងចំណីមានជីវជាតិគ្រប់គ្រាន់។",
    ),
]

# title, title_km, priority, confidence, disease, symptom keys
RULES = [
    # local chicken-raising guide
    ("Infectious Bronchitis - Respiratory & Egg Drop", "ជំងឺរលាកទងសួតឆ្លង - ផ្លូវដង្ហើម និងពងធ្លាក់",
     1, 90.0, "Infectious Bronchitis", ["sneezing", "nasal", "eggs"]),
    ("Infectious Bronchitis - Kidney (Variant) Strain", "ជំងឺរលាកទងសួតឆ្លង - ប្រភេទខូចក្រលៀន",
     2, 80.0, "Infectious Bronchitis", ["sneezing", "watery", "eggs"]),
    ("Coccidiosis - Bloody Droppings & Weight Loss", "ជំងឺកុកស៊ីដ្យូស៊ីស - លាមកមានឈាម និងស្រកទម្ងន់",
     1, 90.0, "Coccidiosis", ["bloody", "weight", "appetite"]),
    ("Coccidiosis - Early Signs", "ជំងឺកុកស៊ីដ្យូស៊ីស - រោគសញ្ញាដំបូង",
     2, 70.0, "Coccidiosis", ["watery", "weight", "appetite"]),
    ("Newcastle - Twisted Neck & Green Diarrhea", "ជំងឺញូវកាស - រមួលក និងរាគពណ៌បៃតង",
     1, 92.0, "Newcastle Disease", ["sneezing", "green", "neck", "appetite"]),
    ("Mycoplasmosis - Face & Eyes", "ជំងឺមីកូប្លាស្មា - មុខ និងភ្នែក",
     1, 90.0, "Mycoplasmosis", ["face", "nasal", "eyes", "breathing"]),
    ("Mycoplasmosis - Joints & Breathing", "ជំងឺមីកូប្លាស្មា - សន្លាក់ និងផ្លូវដង្ហើម",
     2, 75.0, "Mycoplasmosis", ["joints", "breathing", "appetite"]),
    ("Colibacillosis - Chicks", "ជំងឺកូលីបាក់ស៊ីឡូស៊ីស - កូនមាន់",
     1, 88.0, "Colibacillosis", ["watery", "lethargy", "chicks", "appetite"]),
    ("Colibacillosis - Respiratory", "ជំងឺកូលីបាក់ស៊ីឡូស៊ីស - ផ្លូវដង្ហើម",
     2, 80.0, "Colibacillosis", ["feathers", "noisy", "coughing", "breathing"]),
    # Module 13 deck
    ("Infectious Bronchitis - Egg Shell Damage", "ជំងឺរលាកទងសួតឆ្លង - សំបកពងខូច",
     1, 90.0, "Infectious Bronchitis", ["coughing", "noisy", "shell"]),
    ("Coccidiosis - Young Chicks", "ជំងឺកុកស៊ីដ្យូស៊ីស - កូនមាន់",
     1, 92.0, "Coccidiosis", ["bloody", "thirst", "weight", "feathers", "lethargy"]),
    ("Newcastle - Nervous Signs", "ជំងឺញូវកាស - សញ្ញាប្រព័ន្ធប្រសាទ",
     1, 90.0, "Newcastle Disease", ["wings", "paralysis", "neck"]),
    ("Newcastle - Respiratory Signs", "ជំងឺញូវកាស - សញ្ញាផ្លូវដង្ហើម",
     2, 80.0, "Newcastle Disease", ["breathing", "coughing", "sneezing", "green"]),
    ("Mycoplasmosis - Chronic Breathing", "ជំងឺមីកូប្លាស្មា - ផ្លូវដង្ហើមរ៉ាំរ៉ៃ",
     2, 70.0, "Mycoplasmosis", ["noisy", "coughing", "sneezing", "breathing"]),
    ("Avian Influenza - Sudden Deaths & Bruising", "ជំងឺផ្តាសាយបក្សី - ងាប់ភ្លាមៗ និងជាំឈាម",
     1, 90.0, "Avian Influenza", ["sudden_death", "comb", "leg_bruise", "breathing"]),
    ("Laryngotracheitis - Bloody Cough", "ជំងឺរលាកបំពង់សំលេង - ក្អកចេញឈាម",
     1, 92.0, "Infectious Laryngotracheitis", ["neck_stretch", "coughing", "blood_cough"]),
    ("Laryngotracheitis - Severe Gasping", "ជំងឺរលាកបំពង់សំលេង - ថប់ដង្ហើមខ្លាំង",
     2, 75.0, "Infectious Laryngotracheitis", ["neck_stretch", "breathing", "coughing"]),
    ("Infectious Coryza - Facial & Nasal", "ជំងឺកូរីសា - ហើមមុខ និងហៀរសំបោរ",
     1, 90.0, "Infectious Coryza", ["face", "nasal", "sneezing"]),
    ("Fowl Cholera - Swollen Wattles & Sudden Death", "ជំងឺអាសន្នរោគ - ហើមលេង និងងាប់លឿន",
     1, 88.0, "Fowl Cholera", ["sudden_death", "face", "eye_pus", "nasal"]),
    ("Fowl Cholera - Swollen Joints", "ជំងឺអាសន្នរោគ - ហើមសន្លាក់",
     2, 70.0, "Fowl Cholera", ["joints", "face", "breathing"]),
    ("Marek's - Splayed Legs", "ជំងឺម៉ារ៉ិក - ជើងលាតសន្ធឹង",
     1, 92.0, "Marek's Disease", ["splayed", "lame", "paralysis"]),
    ("Salmonellosis - Pullorum (Chicks)", "ជំងឺសាល់ម៉ូណេឡូស៊ីស - Pullorose (កូនមាន់)",
     1, 90.0, "Salmonellosis", ["white_diarrhea", "vent", "appetite", "chicks"]),
    ("Salmonellosis - Typhoid (Adults)", "ជំងឺសាល់ម៉ូណេឡូស៊ីស - Typhose (មាន់ធំ)",
     2, 65.0, "Salmonellosis", ["green", "appetite", "lethargy"]),
    ("Gumboro - White Diarrhea & Weakness", "ជំងឺហ្គុំបូរ៉ូ - រាគពណ៌ស និងអស់កម្លាំង",
     1, 85.0, "Gumboro Disease", ["white_diarrhea", "vent", "lethargy"]),
    ("Roundworms - Worms in Droppings", "ព្រូន - ឃើញព្រូនក្នុងលាមក",
     1, 95.0, "Internal Parasites (Roundworms)", ["worms", "weight"]),
    ("Botulism - Limp Neck", "ជំងឺបូទុយលីស - ទន់ក",
     1, 92.0, "Botulism", ["limp_neck", "lame", "wings"]),
    ("Fowl Pox - Dry (Skin) Form", "ជំងឺអុតមាន់ - ទម្រង់ស្ងួត (ស្បែក)",
     1, 90.0, "Fowl Pox", ["skin_scabs"]),
    ("Fowl Pox - Wet Form", "ជំងឺអុតមាន់ - ទម្រង់សើម",
     2, 85.0, "Fowl Pox", ["mouth_lesions", "breathing"]),
    ("External Parasites - Lice & Mites", "បរាសិតខាងក្រៅ - ចៃ និងស្រមើរ",
     1, 95.0, "External Parasites (Lice & Mites)", ["lice", "restless"]),
    ("Feather Pecking - Wounds", "ការចឹកគ្នា - របួស",
     1, 90.0, "Feather Pecking (Cannibalism)", ["pecking"]),
    ("Vitamin A Deficiency - Stuck Eyelids", "កង្វះវីតាមីន A - ត្របកភ្នែកស្អិត",
     1, 85.0, "Vitamin A Deficiency", ["eyelids_stuck"]),
    ("Vitamin D Deficiency - Feathers Turning Black", "កង្វះវីតាមីន D - រោមប្រែជាខ្មៅ",
     1, 85.0, "Vitamin D Deficiency", ["feathers_black"]),
    ("Vitamin B Deficiency - Scabs & Cracked Feet", "កង្វះវីតាមីន B - ក្រមរក្រៀម និងបាតជើងបែក",
     1, 90.0, "Vitamin B Deficiency", ["eye_beak_scabs", "cracked_feet"]),
]


def _symptom(key: str) -> Symptom:
    names, name_km, desc, desc_km = SYMPTOMS[key]
    for name in names:
        found = db.session.scalar(db.select(Symptom).filter_by(name=name))
        if found:
            return found
    symptom = Symptom(name=names[0], name_km=name_km, description=desc, description_km=desc_km)
    db.session.add(symptom)
    db.session.flush()
    return symptom


def _category(name: str) -> Category:
    category = db.session.scalar(db.select(Category).filter_by(name=name))
    if category is None:
        category = Category(name=name, name_km=CATEGORIES.get(name))
        db.session.add(category)
        db.session.flush()
    return category


def seed_field_guide_data() -> None:
    symptoms = {key: _symptom(key) for key in SYMPTOMS}

    diseases = {}
    for name, name_km, category, desc, desc_km, treat, treat_km in DISEASES:
        disease = db.session.scalar(db.select(Disease).filter_by(name=name))
        if disease is None:
            disease = Disease(name=name, name_km=name_km, category_id=_category(category).id)
            db.session.add(disease)
        disease.description, disease.description_km = desc, desc_km
        disease.treatment, disease.treatment_km = treat, treat_km
        db.session.flush()
        diseases[name] = disease

    for title, title_km, priority, confidence, disease_name, keys in RULES:
        disease = diseases[disease_name]
        rule = db.session.scalar(db.select(Rule).filter_by(title=title, disease_id=disease.id))
        if rule is None:
            rule = Rule(title=title, disease_id=disease.id)
            db.session.add(rule)
        rule_symptoms = [symptoms[k] for k in keys]
        rule.title_km = title_km
        rule.description = ", ".join(s.name for s in rule_symptoms) + "."
        rule.description_km = " ".join(s.name_km or s.name for s in rule_symptoms) + "។"
        rule.priority = priority
        rule.confidence = confidence
        rule.symptoms = rule_symptoms

    db.session.commit()
    print("Seeded field guide data successfully!")


if __name__ == "__main__":
    from app import create_app

    with create_app().app_context():
        seed_field_guide_data()
