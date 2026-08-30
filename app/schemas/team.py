import uuid
from datetime import datetime

from pydantic import field_validator

from app.schemas.common import ORMModel

USERNAME_PATTERN_HINT = "3-32 characters: letters, numbers, dots, underscores, hyphens"


class TeamMemberCreate(ORMModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not (3 <= len(v) <= 32) or not all(c.isalnum() or c in "._-" for c in v):
            raise ValueError(f"Username must be {USERNAME_PATTERN_HINT}")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class TeamMemberPasswordReset(ORMModel):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class TeamMemberOut(ORMModel):
    id: uuid.UUID
    username: str | None
    is_active: bool
    created_at: datetime
