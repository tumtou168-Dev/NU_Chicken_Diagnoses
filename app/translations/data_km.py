# Khmer display text for built-in roles and permissions, keyed by the English name stored in the database.
# The stored names stay English because the code checks them (e.g. has_role("Admin")); only what is shown is translated.
# Roles or permissions an admin creates are not listed and simply display as typed.
DATA_KM = {
    # roles
    "Admin": "អ្នកគ្រប់គ្រង",
    "Doctor": "គ្រូពេទ្យ",
    "User": "អ្នកប្រើប្រាស់",
    "System administrator": "អ្នកគ្រប់គ្រងប្រព័ន្ធ",
    "Knowledge author": "អ្នកបង្កើតចំណេះដឹង",
    "Diagnosis user": "អ្នកប្រើប្រាស់សម្រាប់ធ្វើរោគវិនិច្ឆ័យ",
    # permissions
    "Create Users": "បង្កើតអ្នកប្រើប្រាស់",
    "Edit Users": "កែប្រែអ្នកប្រើប្រាស់",
    "Delete Users": "លុបអ្នកប្រើប្រាស់",
    "Manage Roles": "គ្រប់គ្រងតួនាទី",
    "Manage Permissions": "គ្រប់គ្រងសិទ្ធិ",
    "Author Expert Rules": "បង្កើតវិធានអ្នកជំនាញ",
    "Manage Symptoms": "គ្រប់គ្រងរោគសញ្ញា",
    "Manage Diseases": "គ្រប់គ្រងជំងឺ",
    "Manage Rules": "គ្រប់គ្រងវិធាន",
    "Manage Categories": "គ្រប់គ្រងប្រភេទ",
    "Run Diagnosis": "ធ្វើរោគវិនិច្ឆ័យ",
    "View Case History": "មើលប្រវត្តិករណី",
    "Manage Page Texts": "គ្រប់គ្រងអត្ថបទទំព័រ",
}
