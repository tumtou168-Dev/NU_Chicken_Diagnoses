# app/forms/validation.py
"""Validators whose messages are translated when the form is rendered (lazy strings)."""
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange

from app.i18n import lazy

REQUIRED = lazy("សូមបំពេញវាលនេះ។")
INVALID_EMAIL = lazy("សូមបញ្ចូលអាសយដ្ឋានអ៊ីមែលឱ្យត្រឹមត្រូវ។")
PASSWORD_MISMATCH = lazy("ពាក្យសម្ងាត់មិនដូចគ្នាទេ។")


def required():
    return DataRequired(message=REQUIRED)


def email():
    return Email(message=INVALID_EMAIL)


def length(min=-1, max=-1):
    if min > -1 and max > -1:
        message = lazy("ត្រូវមានពី %(min)s ដល់ %(max)s តួអក្សរ។", min=min, max=max)
    elif min > -1:
        message = lazy("ត្រូវមានយ៉ាងតិច %(min)s តួអក្សរ។", min=min)
    else:
        message = lazy("ត្រូវមានយ៉ាងច្រើន %(max)s តួអក្សរ។", max=max)
    return Length(min=min, max=max, message=message)


def number_range(min, max):
    return NumberRange(min=min, max=max, message=lazy("តម្លៃត្រូវនៅចន្លោះពី %(min)s ដល់ %(max)s។", min=min, max=max))


def passwords_match(field_name="password"):
    return EqualTo(field_name, message=PASSWORD_MISMATCH)
