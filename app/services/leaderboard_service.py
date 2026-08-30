"""
Leaderboard / ranking queries.

Design note (see also `models/gamification.py` docstring): rather than a
persisted "leaderboard" snapshot table that needs a cron job to stay fresh,
every leaderboard here is computed live from the `xp_transactions` and
`test_attempts` ledgers, filtered to a minimum attempt count so a single
lucky question can't put someone at rank #1. At MVP scale this is fast with
the indexes already on those tables (`user_id`, `created_at`); if/when scale
requires it, add a materialized snapshot refreshed on a schedule behind the
exact same function signatures - callers won't need to change.

Scoring is intentionally NOT "most questions attempted":
  * Global/weekly/monthly rank by XP, and XP itself is weighted by
    correctness + difficulty + test performance (see `xp_service` /
    `settings_service` defaults) - so grinding wrong answers earns almost
    nothing.
  * Exam rank uses average test percentage score, not attempt volume.
  * Subject rank uses accuracy, gated by a minimum answered count.
All thresholds/weights are configurable via `platform_settings`.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.gamification import XPTransaction
from app.models.test import Test, TestAttempt
from app.models.user import Profile, User
from app.services.settings_service import get_setting


def _entry(user: User, score: float, accuracy: float, questions: int, rank: int, current_user_id: uuid.UUID) -> dict:
    return {
        "rank": rank,
        "user_id": user.id,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "score": round(score, 1),
        "accuracy": accuracy,
        "questions_attempted": questions,
        "is_current_user": user.id == current_user_id,
    }


def global_leaderboard(db: Session, current_user_id: uuid.UUID, limit: int = 50) -> dict:
    min_attempts = int(get_setting(db, "leaderboard.min_attempts") or 10)

    q = (
        select(User, Profile)
        .join(Profile, Profile.user_id == User.id)
        .where(Profile.questions_attempted >= min_attempts, User.is_active.is_(True))
        .order_by(Profile.xp_total.desc())
        .limit(limit)
    )
    rows = db.execute(q).all()
    entries = [
        _entry(
            u,
            p.xp_total,
            round(100 * p.questions_correct / p.questions_attempted, 1) if p.questions_attempted else 0.0,
            p.questions_attempted,
            i + 1,
            current_user_id,
        )
        for i, (u, p) in enumerate(rows)
    ]

    current_rank = global_rank(db, current_user_id, min_attempts)
    current_entry = next((e for e in entries if e["is_current_user"]), None)
    if current_entry is None and current_rank is not None:
        cur = db.execute(
            select(User, Profile).join(Profile, Profile.user_id == User.id).where(User.id == current_user_id)
        ).first()
        if cur:
            u, p = cur
            current_entry = _entry(
                u,
                p.xp_total,
                round(100 * p.questions_correct / p.questions_attempted, 1) if p.questions_attempted else 0.0,
                p.questions_attempted,
                current_rank,
                current_user_id,
            )

    return {
        "scope": "global",
        "scope_label": "Global Leaderboard",
        "entries": entries,
        "current_user_rank": current_rank,
        "current_user_entry": current_entry,
    }


def global_rank(db: Session, user_id: uuid.UUID, min_attempts: int) -> int | None:
    profile = db.get(Profile, user_id)
    if profile is None or profile.questions_attempted < min_attempts:
        return None
    higher = db.execute(
        select(func.count())
        .select_from(Profile)
        .join(User, User.id == Profile.user_id)
        .where(Profile.xp_total > profile.xp_total, Profile.questions_attempted >= min_attempts, User.is_active.is_(True))
    ).scalar_one()
    return higher + 1


def _period_xp_leaderboard(db: Session, current_user_id: uuid.UUID, since: datetime, limit: int, scope: str, label: str) -> dict:
    xp_sum = func.sum(XPTransaction.amount).label("xp_sum")
    q = (
        select(User, xp_sum)
        .join(XPTransaction, XPTransaction.user_id == User.id)
        .where(XPTransaction.created_at >= since, User.is_active.is_(True))
        .group_by(User.id)
        .order_by(xp_sum.desc())
        .limit(limit)
    )
    rows = db.execute(q).all()
    entries = []
    for i, (u, xp) in enumerate(rows):
        profile = db.get(Profile, u.id)
        acc = (
            round(100 * profile.questions_correct / profile.questions_attempted, 1)
            if profile and profile.questions_attempted
            else 0.0
        )
        entries.append(_entry(u, float(xp), acc, profile.questions_attempted if profile else 0, i + 1, current_user_id))

    current_rank = next((e["rank"] for e in entries if e["is_current_user"]), None)
    current_entry = next((e for e in entries if e["is_current_user"]), None)

    return {
        "scope": scope,
        "scope_label": label,
        "entries": entries,
        "current_user_rank": current_rank,
        "current_user_entry": current_entry,
    }


def weekly_leaderboard(db: Session, current_user_id: uuid.UUID, limit: int = 50) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=7)
    return _period_xp_leaderboard(db, current_user_id, since, limit, "weekly", "Weekly Leaderboard")


def monthly_leaderboard(db: Session, current_user_id: uuid.UUID, limit: int = 50) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    return _period_xp_leaderboard(db, current_user_id, since, limit, "monthly", "Monthly Leaderboard")


def exam_leaderboard(db: Session, exam_id: uuid.UUID, current_user_id: uuid.UUID, limit: int = 50) -> dict:
    avg_pct = func.avg(100 * TestAttempt.score / func.nullif(Test.total_marks, 0)).label("avg_pct")
    q = (
        select(User, avg_pct, func.count(TestAttempt.id))
        .join(TestAttempt, TestAttempt.user_id == User.id)
        .join(Test, Test.id == TestAttempt.test_id)
        .where(Test.exam_id == exam_id, TestAttempt.status == "submitted", User.is_active.is_(True))
        .group_by(User.id)
        .order_by(avg_pct.desc())
        .limit(limit)
    )
    rows = db.execute(q).all()
    entries = [
        _entry(u, float(pct or 0), round(float(pct or 0), 1), count, i + 1, current_user_id)
        for i, (u, pct, count) in enumerate(rows)
    ]
    current_rank = next((e["rank"] for e in entries if e["is_current_user"]), None)
    current_entry = next((e for e in entries if e["is_current_user"]), None)
    return {
        "scope": "exam",
        "scope_label": "Exam Leaderboard",
        "entries": entries,
        "current_user_rank": current_rank,
        "current_user_entry": current_entry,
    }


def subject_leaderboard(db: Session, subject_id: uuid.UUID, current_user_id: uuid.UUID, limit: int = 50) -> dict:
    min_attempts = int(get_setting(db, "leaderboard.min_attempts") or 10)
    answered = func.count(Attempt.selected_option).label("answered")
    correct = func.coalesce(func.sum(case((Attempt.is_correct.is_(True), 1), else_=0)), 0).label("correct")
    q = (
        select(User, answered, correct)
        .join(Attempt, Attempt.user_id == User.id)
        .where(Attempt.subject_id == subject_id, User.is_active.is_(True))
        .group_by(User.id)
        .having(answered >= min_attempts)
    )
    rows = db.execute(q).all()
    scored = [
        (u, round(100 * c / a, 1) if a else 0.0, a) for u, a, c in rows
    ]
    scored.sort(key=lambda r: -r[1])
    scored = scored[:limit]
    entries = [_entry(u, acc, acc, a, i + 1, current_user_id) for i, (u, acc, a) in enumerate(scored)]
    current_rank = next((e["rank"] for e in entries if e["is_current_user"]), None)
    current_entry = next((e for e in entries if e["is_current_user"]), None)
    return {
        "scope": "subject",
        "scope_label": "Subject Leaderboard",
        "entries": entries,
        "current_user_rank": current_rank,
        "current_user_entry": current_entry,
    }
