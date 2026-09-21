# Khmer display of audit-log entries. The log stores English text at the moment of the action; it is translated
# when shown, so old entries follow the language toggle too.
import re

TARGETS = {
    "User": "អ្នកប្រើប្រាស់", "Role": "តួនាទី", "Permission": "សិទ្ធិ", "Category": "ប្រភេទ", "Symptom": "រោគសញ្ញា",
    "Disease": "ជំងឺ", "Rule": "វិធាន", "Case": "ករណី", "PageText": "អត្ថបទទំព័រ",
}
ACTIONS = {"DIAGNOSE": "ធ្វើរោគវិនិច្ឆ័យ", "LOGOUT": "ចាកចេញ", "REGISTER": "ចុះឈ្មោះ"}

FIXED = {
    "User logged in": "អ្នកប្រើប្រាស់បានចូលប្រព័ន្ធ",
    "User logged out": "អ្នកប្រើប្រាស់បានចាកចេញ",
    "New user registered": "អ្នកប្រើប្រាស់ថ្មីបានចុះឈ្មោះ",
}
PATTERNS = [
    (re.compile(r"^Created (\w+): (.*)$", re.S), "បានបង្កើត{0}៖ {1}"),
    (re.compile(r"^Updated (\w+): (.*)$", re.S), "បានកែប្រែ{0}៖ {1}"),
    (re.compile(r"^Deleted (\w+): (.*)$", re.S), "បានលុប{0}៖ {1}"),
    (re.compile(r"^Updated page text: (.*)$", re.S), "បានកែប្រែអត្ថបទទំព័រ៖ {0}"),
    (re.compile(r"^Reset page text to default: (.*)$", re.S), "បានស្តារអត្ថបទទំព័រទៅលំនាំដើម៖ {0}"),
    (re.compile(r"^User ran diagnosis, result: (.*)$", re.S), "អ្នកប្រើប្រាស់បានធ្វើរោគវិនិច្ឆ័យ លទ្ធផល៖ {0}"),
]
_NOUNS = {k.lower(): v for k, v in TARGETS.items()}


def detail_km(text):
    if not text:
        return text
    if text in FIXED:
        return FIXED[text]
    for rx, fmt in PATTERNS:
        m = rx.match(text)
        if m:
            groups = list(m.groups())
            if rx.pattern.startswith(("^Created", "^Updated (\\w+)", "^Deleted")):
                groups[0] = _NOUNS.get(groups[0].lower(), groups[0])
            return fmt.format(*groups)
    return text
