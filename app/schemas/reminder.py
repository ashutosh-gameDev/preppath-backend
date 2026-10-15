import uuid
from datetime import date, datetime, time

from pydantic import model_validator

from app.schemas.common import ORMModel

VALID_KINDS = {"daily", "once"}


class ReminderCreate(ORMModel):
    title: str
    kind: str = "daily"
    time_of_day: time
    on_date: date | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def _validate(self) -> "ReminderCreate":
        if self.kind not in VALID_KINDS:
            raise ValueError("kind must be one of daily, once")
        if self.kind == "once" and self.on_date is None:
            raise ValueError("on_date is required for a one-time reminder")
        if self.kind == "daily":
            self.on_date = None
        return self


class ReminderUpdate(ORMModel):
    title: str | None = None
    kind: str | None = None
    time_of_day: time | None = None
    on_date: date | None = None
    is_active: bool | None = None


class ReminderOut(ORMModel):
    id: uuid.UUID
    title: str
    kind: str
    time_of_day: time
    on_date: date | None
    is_active: bool
    created_at: datetime
