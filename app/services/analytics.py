"""
Deterministic (non-AI) analytics engine.

Every number here is computed straight from `attempts` (+ `test_attempts` for
test-level scores). No AI, no heuristics beyond simple, documented rules -
this is intentional per the product brief so an AI layer can be swapped in
later behind the same function signatures without the rest of the app
changing.

Conventions used throughout:
  * "attempted" = a row exists in `attempts` (includes skipped questions).
  * "answered"  = attempted AND `selected_option IS NOT NULL`.
  * accuracy    = correct / answered (skips are excluded from the
                  denominator - a skip isn't a wrong guess, it's a pass).
"""
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Date, case, func, select
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.course import Subject, Topic
from app.models.gamification import XPTransaction
from app.models.test import Test, TestAttempt
from app.services.settings_service import get_setting

_XP_TABLE = XPTransaction.__table__
_XP_AMOUNT_COL = XPTransaction.amount
_XP_USER_COL = XPTransaction.user_id
_XP_CREATED_COL = XPTransaction.created_at


def _period_bounds(period_days: int) -> tuple[datetime, datetime, datetime]:
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=period_days)
    previous_start = now - timedelta(days=period_days * 2)
    return previous_start, current_start, now


def _pct_change(current: float, previous: float) -> tuple[float | None, str]:
    if previous == 0:
        if current == 0:
            return 0.0, "flat"
        return None, "up"
    change = round(100 * (current - previous) / previous, 1)
    direction = "up" if change > 0 else "down" if change < 0 else "flat"
    return change, direction


@dataclass
class _AttemptAgg:
    attempted: int
    answered: int
    correct: int
    total_time: int

    @property
    def accuracy(self) -> float:
        return round(100 * self.correct / self.answered, 1) if self.answered else 0.0

    @property
    def avg_time(self) -> float:
        return round(self.total_time / self.answered, 1) if self.answered else 0.0


def _attempt_agg(db: Session, user_id: uuid.UUID, start: datetime, end: datetime) -> _AttemptAgg:
    row = db.execute(
        select(
            func.count(Attempt.id),
            func.count(Attempt.selected_option),
            func.coalesce(func.sum(case((Attempt.is_correct.is_(True), 1), else_=0)), 0),
            func.coalesce(func.sum(Attempt.time_taken_seconds), 0),
        ).where(Attempt.user_id == user_id, Attempt.attempted_at >= start, Attempt.attempted_at < end)
    ).one()
    return _AttemptAgg(attempted=row[0], answered=row[1], correct=row[2], total_time=row[3])


def _test_agg(db: Session, user_id: uuid.UUID, start: datetime, end: datetime) -> tuple[int, float]:
    """Returns (tests_completed, average_percentage_score)."""
    rows = db.execute(
        select(TestAttempt.score, Test.total_marks)
        .join(Test, Test.id == TestAttempt.test_id)
        .where(
            TestAttempt.user_id == user_id,
            TestAttempt.status == "submitted",
            TestAttempt.submitted_at >= start,
            TestAttempt.submitted_at < end,
        )
    ).all()
    if not rows:
        return 0, 0.0
    pcts = [100 * s / m for s, m in rows if m]
    return len(rows), round(sum(pcts) / len(pcts), 1) if pcts else 0.0


def performance_overview(db: Session, user_id: uuid.UUID, period_days: int = 30) -> dict:
    previous_start, current_start, now = _period_bounds(period_days)

    cur = _attempt_agg(db, user_id, current_start, now)
    prev = _attempt_agg(db, user_id, previous_start, current_start)
    cur_tests, cur_avg_score = _test_agg(db, user_id, current_start, now)
    prev_tests, prev_avg_score = _test_agg(db, user_id, previous_start, current_start)

    def metric(cur_v: float, prev_v: float) -> dict:
        change, direction = _pct_change(cur_v, prev_v)
        return {"value": cur_v, "previous_value": prev_v, "change_pct": change, "direction": direction}

    cur_xp_row = db.execute(
        select(func.coalesce(func.sum(_XP_AMOUNT_COL), 0)).select_from(_XP_TABLE).where(
            _XP_USER_COL == user_id, _XP_CREATED_COL >= current_start, _XP_CREATED_COL < now
        )
    ).scalar_one()
    prev_xp_row = db.execute(
        select(func.coalesce(func.sum(_XP_AMOUNT_COL), 0)).select_from(_XP_TABLE).where(
            _XP_USER_COL == user_id, _XP_CREATED_COL >= previous_start, _XP_CREATED_COL < current_start
        )
    ).scalar_one()

    return {
        "questions_attempted": metric(cur.attempted, prev.attempted),
        "accuracy": metric(cur.accuracy, prev.accuracy),
        "tests_completed": metric(cur_tests, prev_tests),
        "average_score_pct": metric(cur_avg_score, prev_avg_score),
        "avg_time_per_question_seconds": metric(cur.avg_time, prev.avg_time),
        "xp_earned": metric(float(cur_xp_row), float(prev_xp_row)),
        "current_rank": None,  # filled in by the router (needs leaderboard_service)
        "period_days": period_days,
    }


def progress_series(db: Session, user_id: uuid.UUID, days: int) -> list[dict]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    day_col = func.cast(Attempt.attempted_at, Date)

    attempt_rows = db.execute(
        select(
            day_col.label("d"),
            func.count(Attempt.id),
            func.count(Attempt.selected_option),
            func.coalesce(func.sum(case((Attempt.is_correct.is_(True), 1), else_=0)), 0),
            func.coalesce(func.sum(Attempt.time_taken_seconds), 0),
        )
        .where(Attempt.user_id == user_id, Attempt.attempted_at >= start)
        .group_by(day_col)
    ).all()

    xp_day_col = func.cast(_XP_CREATED_COL, Date)
    xp_rows = db.execute(
        select(xp_day_col.label("d"), func.coalesce(func.sum(_XP_AMOUNT_COL), 0))
        .select_from(_XP_TABLE)
        .where(_XP_USER_COL == user_id, _XP_CREATED_COL >= start)
        .group_by(xp_day_col)
    ).all()
    xp_by_day = {r[0]: r[1] for r in xp_rows}

    test_day_col = func.cast(TestAttempt.submitted_at, Date)
    test_rows = db.execute(
        select(test_day_col.label("d"), func.avg(100 * TestAttempt.score / func.nullif(Test.total_marks, 0)))
        .join(Test, Test.id == TestAttempt.test_id)
        .where(
            TestAttempt.user_id == user_id,
            TestAttempt.status == "submitted",
            TestAttempt.submitted_at >= start,
        )
        .group_by(test_day_col)
    ).all()
    test_score_by_day = {r[0]: round(float(r[1]), 1) if r[1] is not None else None for r in test_rows}

    points = []
    for d, attempted, answered, correct, time_sum in attempt_rows:
        accuracy = round(100 * correct / answered, 1) if answered else None
        points.append(
            {
                "date": d,
                "accuracy": accuracy,
                "questions_solved": attempted,
                "avg_test_score": test_score_by_day.get(d),
                "xp": xp_by_day.get(d, 0),
                "study_time_minutes": round(time_sum / 60, 1),
            }
        )
    points.sort(key=lambda p: p["date"])
    return points


def subject_performance(db: Session, user_id: uuid.UUID, course_id: uuid.UUID | None = None) -> list[dict]:
    min_attempts = int(get_setting(db, "analytics.min_attempts_for_signal") or 5)
    strong_th = float(get_setting(db, "analytics.strong_threshold_pct") or 80)
    weak_th = float(get_setting(db, "analytics.weak_threshold_pct") or 70)

    subj_q = select(
        Attempt.subject_id,
        Subject.name,
        func.count(Attempt.id),
        func.count(Attempt.selected_option),
        func.coalesce(func.sum(case((Attempt.is_correct.is_(True), 1), else_=0)), 0),
    ).join(Subject, Subject.id == Attempt.subject_id).where(Attempt.user_id == user_id)
    if course_id:
        subj_q = subj_q.where(Attempt.course_id == course_id)
    subj_q = subj_q.group_by(Attempt.subject_id, Subject.name)

    subjects = []
    for subject_id, name, attempted, answered, correct in db.execute(subj_q).all():
        accuracy = round(100 * correct / answered, 1) if answered else 0.0

        topic_q = (
            select(
                Attempt.topic_id,
                Topic.name,
                func.count(Attempt.id),
                func.count(Attempt.selected_option),
                func.coalesce(func.sum(case((Attempt.is_correct.is_(True), 1), else_=0)), 0),
                func.max(Attempt.attempted_at),
            )
            .join(Topic, Topic.id == Attempt.topic_id)
            .where(Attempt.user_id == user_id, Attempt.subject_id == subject_id, Attempt.topic_id.is_not(None))
            .group_by(Attempt.topic_id, Topic.name)
        )
        topics = []
        for topic_id, tname, t_attempted, t_answered, t_correct, last_at in db.execute(topic_q).all():
            t_accuracy = round(100 * t_correct / t_answered, 1) if t_answered else 0.0
            has_signal = t_answered >= min_attempts
            topics.append(
                {
                    "topic_id": topic_id,
                    "topic_name": tname,
                    "attempts": t_attempted,
                    "accuracy": t_accuracy,
                    "is_strong": has_signal and t_accuracy >= strong_th,
                    "is_weak": has_signal and t_accuracy < weak_th,
                    "last_attempted": last_at.isoformat() if last_at else None,
                }
            )
        topics.sort(key=lambda t: -t["accuracy"])

        subjects.append(
            {
                "subject_id": subject_id,
                "subject_name": name,
                "attempts": attempted,
                "accuracy": accuracy,
                "topics": topics,
            }
        )
    subjects.sort(key=lambda s: -s["accuracy"])
    return subjects


def strong_weak_areas(db: Session, user_id: uuid.UUID) -> tuple[list[dict], list[dict]]:
    """
    Strengths/weaknesses at both subject and topic granularity, filtered to
    items with enough attempts to be statistically meaningful (never call a
    topic a strength off 2 questions).
    """
    subjects = subject_performance(db, user_id)
    min_attempts = int(get_setting(db, "analytics.min_attempts_for_signal") or 5)
    strong_th = float(get_setting(db, "analytics.strong_threshold_pct") or 80)
    weak_th = float(get_setting(db, "analytics.weak_threshold_pct") or 70)

    strong: list[dict] = []
    weak: list[dict] = []

    for s in subjects:
        if s["attempts"] >= min_attempts:
            item = {
                "subject_id": s["subject_id"],
                "topic_id": None,
                "name": s["subject_name"],
                "scope": "subject",
                "accuracy": s["accuracy"],
                "attempts": s["attempts"],
            }
            if s["accuracy"] >= strong_th:
                strong.append(item)
            elif s["accuracy"] < weak_th:
                weak.append(item)
        for t in s["topics"]:
            if t["attempts"] < min_attempts:
                continue
            item = {
                "subject_id": s["subject_id"],
                "topic_id": t["topic_id"],
                "name": t["topic_name"],
                "scope": "topic",
                "accuracy": t["accuracy"],
                "attempts": t["attempts"],
            }
            if t["is_strong"]:
                strong.append(item)
            elif t["is_weak"]:
                weak.append(item)

    strong.sort(key=lambda x: -x["accuracy"])
    weak.sort(key=lambda x: x["accuracy"])
    return strong, weak


def improvement_analysis(db: Session, user_id: uuid.UUID, period_days: int = 30) -> list[dict]:
    """Per-subject accuracy comparison: current N days vs the previous N days."""
    previous_start, current_start, now = _period_bounds(period_days)
    min_attempts = int(get_setting(db, "analytics.min_attempts_for_signal") or 5)

    def agg_by_subject(start: datetime, end: datetime) -> dict[uuid.UUID, dict]:
        rows = db.execute(
            select(
                Attempt.subject_id,
                Subject.name,
                func.count(Attempt.selected_option),
                func.coalesce(func.sum(case((Attempt.is_correct.is_(True), 1), else_=0)), 0),
            )
            .join(Subject, Subject.id == Attempt.subject_id)
            .where(Attempt.user_id == user_id, Attempt.attempted_at >= start, Attempt.attempted_at < end)
            .group_by(Attempt.subject_id, Subject.name)
        ).all()
        return {
            r[0]: {"name": r[1], "answered": r[2], "correct": r[3]}
            for r in rows
        }

    cur = agg_by_subject(current_start, now)
    prev = agg_by_subject(previous_start, current_start)

    results = []
    for subject_id, cur_data in cur.items():
        prev_data = prev.get(subject_id, {"answered": 0, "correct": 0})
        if cur_data["answered"] < min_attempts:
            continue
        cur_acc = round(100 * cur_data["correct"] / cur_data["answered"], 1) if cur_data["answered"] else 0.0
        prev_acc = (
            round(100 * prev_data["correct"] / prev_data["answered"], 1) if prev_data["answered"] else 0.0
        )
        results.append(
            {
                "subject_id": subject_id,
                "subject_name": cur_data["name"],
                "previous_accuracy": prev_acc,
                "current_accuracy": cur_acc,
                "change_pct": round(cur_acc - prev_acc, 1),
                "previous_attempts": prev_data["answered"],
                "current_attempts": cur_data["answered"],
            }
        )
    results.sort(key=lambda r: -r["change_pct"])
    return results
