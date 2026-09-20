from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.pyq_paper import PYQPaper
from app.models.question import Question
from app.models.test import Test, TestAttempt
from app.models.user import User
from app.schemas.admin import (
    AdminDashboardCharts,
    AdminDashboardStats,
    DailySeriesPoint,
    PapersOverviewItem,
    PopularItem,
    UploaderStatItem,
)
from app.schemas.statistics import LeaderboardOut
from app.services import leaderboard_service

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
    total_pyq_papers = db.execute(select(func.count(PYQPaper.id))).scalar_one()
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
        total_pyq_papers=total_pyq_papers,
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


@router.get("/papers-overview", response_model=list[PapersOverviewItem])
def papers_overview(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """What PYQ papers exist, their course/category, how many questions are
    tagged to each, and who uploaded them - the content overview table on
    the admin dashboard (point 11: 'what paper we have what categories paper
    who uploaded and which questions in which')."""
    papers = db.execute(select(PYQPaper).order_by(PYQPaper.exam_name, PYQPaper.year.desc())).scalars().all()
    if not papers:
        return []
    paper_ids = [p.id for p in papers]

    courses = {c.id: c.name for c in db.execute(select(Course)).scalars().all()}

    counts = dict(
        db.execute(
            select(Question.pyq_paper_id, func.count(Question.id))
            .where(Question.pyq_paper_id.in_(paper_ids))
            .group_by(Question.pyq_paper_id)
        ).all()
    )

    uploaders_by_paper: dict = {}
    uploader_rows = db.execute(
        select(Question.pyq_paper_id, User.username, User.full_name, User.email)
        .join(User, User.id == Question.created_by)
        .where(Question.pyq_paper_id.in_(paper_ids))
        .distinct()
    ).all()
    for paper_id, username, full_name, email in uploader_rows:
        label = username or full_name or email
        uploaders_by_paper.setdefault(paper_id, set()).add(label)

    return [
        PapersOverviewItem(
            id=p.id,
            exam_name=p.exam_name,
            year=p.year,
            label=p.label,
            course_id=p.course_id,
            course_name=courses.get(p.course_id) if p.course_id else None,
            question_count=counts.get(p.id, 0),
            uploaders=sorted(uploaders_by_paper.get(p.id, set())),
        )
        for p in papers
    ]


@router.get("/leaderboard", response_model=LeaderboardOut)
def dashboard_leaderboard(
    scope: str = "global", limit: int = 10, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """The same live leaderboard students see, surfaced on the admin
    dashboard (point 9) - `current_user`/`current_user_entry` will just
    reflect the calling admin's own (near-certainly absent) rank, which is
    harmless here."""
    if scope == "weekly":
        return leaderboard_service.weekly_leaderboard(db, admin.id, limit)
    if scope == "monthly":
        return leaderboard_service.monthly_leaderboard(db, admin.id, limit)
    return leaderboard_service.global_leaderboard(db, admin.id, limit)


@router.get("/uploader-stats", response_model=list[UploaderStatItem])
def uploader_stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Total questions each team member has uploaded (all statuses), most
    first. Questions with no recorded uploader (older rows, or a deleted
    account) are grouped under "Unknown"."""
    rows = db.execute(
        select(
            Question.created_by,
            User.username,
            User.full_name,
            User.email,
            User.role,
            func.count(Question.id),
            func.count(Question.id).filter(Question.status == "published"),
            func.max(Question.created_at),
        )
        .outerjoin(User, User.id == Question.created_by)
        .group_by(Question.created_by, User.username, User.full_name, User.email, User.role)
        .order_by(func.count(Question.id).desc())
    ).all()
    return [
        UploaderStatItem(
            user_id=uid,
            label=(username or full_name or email) if uid else "Unknown",
            role=role,
            question_count=total,
            published_count=published,
            last_upload_at=last,
        )
        for uid, username, full_name, email, role, total, published, last in rows
    ]
