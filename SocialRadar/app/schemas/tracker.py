from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import Platform, normalize_phrases

MAX_NAME_LENGTH = 80
MAX_KEYWORDS = 20


# --- validation helpers shared by TrackerCreate and TrackerUpdate ----------


def clean_name(value: str) -> str:
    name = " ".join(value.split())
    if not name:
        raise ValueError("Tracker name cannot be empty")
    return name


def clean_keywords(values: list[str]) -> list[str]:
    keywords = normalize_phrases(values)
    if not keywords:
        raise ValueError("At least one keyword is required")
    return keywords


def clean_platforms(values: list[Platform]) -> list[Platform]:
    platforms = list(dict.fromkeys(values))  # remove duplicates, keep order
    if not platforms:
        raise ValueError("At least one platform is required")
    return platforms


def check_no_overlap(keywords: list[str], excluded: list[str]) -> None:
    overlap = [word for word in keywords if word in excluded]
    if overlap:
        raise ValueError(
            f"A keyword cannot also be an excluded keyword: {', '.join(overlap)}"
        )


# --- schemas ---------------------------------------------------------------


class TrackerCreate(BaseModel):
    name: str = Field(max_length=MAX_NAME_LENGTH, examples=["Website Leads"])
    keywords: list[str] = Field(
        max_length=MAX_KEYWORDS,
        description="Phrases to look for. Matching is case-insensitive.",
    )
    excluded_keywords: list[str] = Field(
        default_factory=list,
        max_length=MAX_KEYWORDS,
        description="If a post contains any of these phrases it is ignored.",
    )
    platforms: list[Platform]
    is_active: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Website Leads",
                "keywords": ["нужен сайт", "ищу разработчика", "website developer"],
                "excluded_keywords": ["бесплатно", "стажировка"],
                "platforms": ["bluesky", "threads"],
                "is_active": True,
            }
        }
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return clean_name(value)

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, value: list[str]) -> list[str]:
        return clean_keywords(value)

    @field_validator("excluded_keywords")
    @classmethod
    def validate_excluded(cls, value: list[str]) -> list[str]:
        return normalize_phrases(value)

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, value: list[Platform]) -> list[Platform]:
        return clean_platforms(value)

    @model_validator(mode="after")
    def validate_overlap(self) -> "TrackerCreate":
        check_no_overlap(self.keywords, self.excluded_keywords)
        return self


class TrackerUpdate(BaseModel):
    """Partial update: send only the fields you want to change."""

    name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    keywords: list[str] | None = Field(default=None, max_length=MAX_KEYWORDS)
    excluded_keywords: list[str] | None = Field(default=None, max_length=MAX_KEYWORDS)
    platforms: list[Platform] | None = None
    is_active: bool | None = None

    model_config = ConfigDict(
        json_schema_extra={"example": {"keywords": ["need a website"], "is_active": False}}
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return None if value is None else clean_name(value)

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else clean_keywords(value)

    @field_validator("excluded_keywords")
    @classmethod
    def validate_excluded(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else normalize_phrases(value)

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, value: list[Platform] | None) -> list[Platform] | None:
        return None if value is None else clean_platforms(value)

    @model_validator(mode="after")
    def validate_fields(self) -> "TrackerUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if self.keywords is not None and self.excluded_keywords is not None:
            check_no_overlap(self.keywords, self.excluded_keywords)
        return self


class TrackerResponse(BaseModel):
    id: int
    name: str
    keywords: list[str]
    excluded_keywords: list[str]
    platforms: list[Platform]
    is_active: bool
    match_count: int = Field(description="Number of matches found by this tracker")
    created_at: datetime
    updated_at: datetime
