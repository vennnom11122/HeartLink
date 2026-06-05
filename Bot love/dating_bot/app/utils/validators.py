from __future__ import annotations

from app.utils.constants import MAX_BIO_LENGTH, MAX_NAME_LENGTH, MAX_VALENTINE_MESSAGE_LENGTH
from app.utils.text_filters import validate_public_text


def validate_name(name: str) -> tuple[bool, str | None]:
    return validate_public_text(name, max_length=MAX_NAME_LENGTH)


def validate_age(raw_age: str) -> tuple[bool, int | str]:
    value = (raw_age or "").strip()
    if not value.isdigit():
        return False, "Возраст нужно указать числом."
    age = int(value)
    if age < 18:
        return False, "Бот доступен только пользователям 18+."
    if age > 99:
        return False, "Укажи возраст от 18 до 99."
    return True, age


def validate_bio(bio: str) -> tuple[bool, str | None]:
    return validate_public_text(bio, max_length=MAX_BIO_LENGTH)


def validate_valentine_message(message: str) -> tuple[bool, str | None]:
    return validate_public_text(message, max_length=MAX_VALENTINE_MESSAGE_LENGTH, allow_empty=True)

