import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class StudySessionCreate(ORMModel):
    duration_seconds: int


class StudySessionOut(ORMModel):
    id: uuid.UUID
    duration_seconds: int
    created_at: datetime


class LeaderboardEntry(ORMModel):
    user_id: uuid.UUID
    display_name: str
    total_seconds: int
    rank: int


class StudyLeaderboardOut(ORMModel):
    period: str
    top: list[LeaderboardEntry]
    # The caller's own rank/total this month, even if outside `top`.
    my_rank: int | None
    my_total_seconds: int
    winner_count: int
    reward_days: int
