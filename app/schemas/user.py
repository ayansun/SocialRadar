"""Schemas for registration, login and the current user."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, description="Letters, digits, _ . -")
    password: str = Field(min_length=8, max_length=72)

    @field_validator("username")
    @classmethod
    def check_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.match(value):
            raise ValueError("Username may contain only letters, digits, _ . -")
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        # bcrypt reads at most 72 bytes (non-latin letters take 2+ bytes each).
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password is too long (at most 72 bytes)")
        return value


class UserResponse(BaseModel):
    """Public data about a user. The password hash is never returned."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    role: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
