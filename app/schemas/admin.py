import uuid
from datetime import date, datetime

from app.schemas.common import ORMModel


class AdminDashboardStats(ORMModel):
    total_users: int
    active_users_7d: int
    total_questions: int
    total_tests: int
    total_courses: int
    total_pyq_papers: int
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


class PapersOverviewItem(ORMModel):
    """One row of the admin dashboard's content-overview table - what PYQ
    papers exist, which course/category each belongs to, how many questions
    are in it, who uploaded them, and how many of those questions still need
    an image (see admin/dashboard.py papers_overview)."""
    id: uuid.UUID
    exam_name: str
    year: int | None
    label: str | None
    course_id: uuid.UUID | None
    course_name: str | None
    # The subject most of this paper's questions are tagged to - a paper has
    # no subject of its own (only course_id), so this is a majority vote
    # over Question.subject_id, same pattern the student-facing PYQ browser
    # already uses to work out a paper's "effective" course.
    subject_name: str | None
    question_count: int
    needs_image_count: int
    uploaders: list[str]


class UploaderStatItem(ORMModel):
    """One row of the dashboard's "who uploaded how many questions" table."""
    user_id: uuid.UUID | None
    label: str
    role: str | None
    question_count: int
    published_count: int
    last_upload_at: datetime | None


class CoursePapersItem(ORMModel):
    """One row of the "papers per course" breakdown - how many PYQ papers
    are tagged to this course (PYQPaper.course_id is a direct field, unlike
    subject - see papers_overview's majority-vote comment for why subject
    needs inferring)."""
    course_id: uuid.UUID | None
    course_name: str
    paper_count: int
