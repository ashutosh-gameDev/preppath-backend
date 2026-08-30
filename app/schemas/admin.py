import uuid
from datetime import date

from app.schemas.common import ORMModel


class AdminDashboardStats(ORMModel):
    total_users: int
    active_users_7d: int
    total_questions: int
    total_tests: int
    total_courses: int
    total_exams: int
    questions_attempted_today: int
    tests_completed_today: int


class DailySeriesPoint(ORMModel):
    date: date
    value: int


class PopularItem(ORMModel):
    id: uuid.UUID
    name: str
    count: int


class AdminDashboardCharts(ORMModel):
    daily_registrations: list[DailySeriesPoint]
    daily_active_users: list[DailySeriesPoint]
    questions_attempted: list[DailySeriesPoint]
    popular_courses: list[PopularItem]
    popular_tests: list[PopularItem]
