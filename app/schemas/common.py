"""Enums and helpers shared by several schemas."""

from enum import Enum

from pydantic import BaseModel


class Platform(str, Enum):
    BLUESKY = "bluesky"
    THREADS = "threads"


class LeadStatus(str, Enum):
    NEW = "new"
    SAVED = "saved"
    CONTACTED = "contacted"
    DISMISSED = "dismissed"


class PostSource(str, Enum):
    """Where a post came from. Real API sources can be added here later."""

    MANUAL = "manual"  # added through POST /api/posts
    DEMO = "demo"  # test data from POST /api/demo/seed


class ErrorResponse(BaseModel):
    """Shape of business errors (404, 409, 422 raised by services)."""

    detail: str


def normalize_text(value: str) -> str:
    """Lowercase the text and collapse repeated whitespace.

    "  Нужен   САЙТ " -> "нужен сайт"
    The same function is used for keywords and for post text, which is what
    makes keyword matching case-insensitive.
    """
    return " ".join(value.lower().split())


MAX_PHRASE_LENGTH = 60


def normalize_phrases(values: list[str]) -> list[str]:
    """Normalize a list of keywords and remove duplicates, keeping order."""
    result: list[str] = []
    for value in values:
        phrase = normalize_text(value)
        if not phrase:
            raise ValueError("Keywords cannot be empty")
        if len(phrase) > MAX_PHRASE_LENGTH:
            raise ValueError(
                f"Keywords must be at most {MAX_PHRASE_LENGTH} characters long"
            )
        if phrase not in result:
            result.append(phrase)
    return result
