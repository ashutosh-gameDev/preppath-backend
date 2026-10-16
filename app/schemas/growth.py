import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class TopReferrerOut(ORMModel):
    user_id: uuid.UUID
    email: str
    full_name: str | None
    referred_count: int


class AdminStudyLeaderboardEntry(ORMModel):
    user_id: uuid.UUID
    email: str
    full_name: str | None
    total_seconds: int
    rank: int


class AdminLeaderboardRewardOut(ORMModel):
    period: str
    rank_position: int
    user_id: uuid.UUID
    email: str
    full_name: str | None
    total_seconds: int
    created_at: datetime


class AdminStudyLeaderboardOut(ORMModel):
    current_period: str
    current_standings: list[AdminStudyLeaderboardEntry]
    past_rewards: list[AdminLeaderboardRewardOut]
