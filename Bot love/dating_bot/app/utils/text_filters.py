from __future__ import annotations

import re

LINK_RE = re.compile(r"(?i)(https?://|www\.|t\.me/|telegram\.me/|@\w{4,})")
REPEATED_RE = re.compile(r"(.)\1{8,}", re.IGNORECASE)

# This list is intentionally small. In production, use a maintained moderation service.
BAD_WORDS = {
    "spamword",
    "casino",
    "казино",
    "крипта",
}


def contains_link(text: str) -> bool:
    return bool(LINK_RE.search(text or ""))


def contains_bad_words(text: str) -> bool:
    lowered = (text or "").lower()
    return any(word in lowered for word in BAD_WORDS)


def looks_like_spam(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    if REPEATED_RE.search(stripped):
        return True
    words = stripped.split()
    return len(words) >= 8 and len(set(words)) <= 2


def validate_public_text(text: str, *, max_length: int, allow_empty: bool = False) -> tuple[bool, str | None]:
    value = (text or "").strip()
    if not value and not allow_empty:
        return False, "Текст не должен быть пустым."
    if len(value) > max_length:
        return False, f"Слишком длинно. Максимум {max_length} символов."
    if contains_link(value):
        return False, "Ссылки и контакты можно раскрывать только после взаимной симпатии."
    if contains_bad_words(value) or looks_like_spam(value):
        return False, "Похоже на спам или запрещённый текст. Попробуй написать иначе."
    return True, None

