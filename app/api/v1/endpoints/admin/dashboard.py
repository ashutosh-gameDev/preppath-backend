from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.exam import Exam
from app.models.question import Question
from app.models.test import Test, TestAttempt
from app.models.user import User
from app.schemas.admin import AdminDashboardCharts, AdminDashboardStats, DailySeriesPoint, PopularItem

router = APIRouter(prefix="/admin/dashboard", tags=["admin:dashboard"])


@router.get("/stats", response_model=AdminDashboardStats)
def get_stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    week_ago = now - timedelta(days=7)

    total_users = db.execute(select(func.count(User.id))).scalar_one()
    active_users_7d = db.execute(select(func.count(User.id)).where(User.last_active_at >= week_ago)).scalar_one()
    total_questions = db.execute(select(func.count(Question.id))).scalar_one()
    total_tests = db.execute(select(func.count(Test.id))).scalar_one()
    total_courses = db.execute(select(func.count(Course.id))).scalar_one()
    total_exams = db.execute(select(func.count(Exam.id))).scalar_one()
    questions_attempted_today = db.execute(
        select(func.count(Attempt.id)).where(Attempt.attempted_at >= today_start)
    ).scalar_one()
    tests_completed_today = db.execute(
        select(func.count(TestAttempt.id)).where(TestAttempt.submitted_at >= today_start, TestAttempt.status == "submitted")
    ).scalar_one()

    return AdminDashboardStats(
        total_users=total_users,
        active_users_7d=active_users_7d,
        total_questions=total_questions,
        total_tests=total_tests,
        total_courses=total_courses,
        total_exams=total_exams,
        questions_attempted_today=questions_attempted_today,
        tests_completed_today=tests_completed_today,
    )


@router.get("/charts", response_model=AdminDashboardCharts)
def get_charts(days: int = 30, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    def series(model, date_col, extra_where=None) -> list[DailySeriesPoint]:
        day = cast(date_col, Date)
        q = select(day.label("d"), func.count()).where(date_col >= since)
        if extra_where is not None:
            q = q.where(extra_where)
        q = q.group_by(day).order_by(day)
        return [DailySeriesPoint(date=d, value=v) for d, v in db.execute(q).all()]

    daily_registrations = series(User, User.created_at)
    daily_active_users = series(User, User.last_active_at)
    questions_attempted = series(Attempt, Attempt.attempted_at)

    popular_courses_rows = db.execute(
        select(Course.id, Course.name, func.count(Attempt.id))
        .join(Attempt, Attempt.course_id == Course.id)
        .group_by(Course.id, Course.name)
        .order_by(func.count(Attempt.id).desc())
        .limit(5)
    ).all()
    popular_tests_rows = db.execute(
        select(Test.id, Test.title, func.count(TestAttempt.id))
        .join(TestAttempt, TestAttempt.test_id == Test.id)
        .group_by(Test.id, Test.title)
        .order_by(func.count(TestAttempt.id).desc())
        .limit(5)
    ).all()

    return AdminDashboardCharts(
        daily_registrations=daily_registrations,
        daily_active_users=daily_active_users,
        questions_attempted=questions_attempted,
        popular_courses=[PopularItem(id=i, name=n, count=c) for i, n, c in popular_courses_rows],
        popular_tests=[PopularItem(id=i, name=n, count=c) for i, n, c in popular_tests_rows],
    )
