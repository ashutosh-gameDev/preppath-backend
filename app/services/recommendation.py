"""
Rule-based "Recommended Practice" engine (section 12 of the brief).

Deliberately NOT AI - purely deterministic rules over accuracy, weak topics,
recency and difficulty. Each rule returns a `RecommendationOut`-shaped dict
whose `action` field the frontend uses to build the practice session request
directly (course/subject/topic/difficulty/count), so "Practice Weak Area" is
a single API round trip.

Designed to be extensible: to add a new rule, add a function below and
register it in `build_recommendations`. An AI-backed recommender could later
implement the exact same output shape and be swapped in behind
`build_recommendations` without touching callers.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.course import Subject, Topic
from app.services.analytics import strong_weak_areas
from app.services.settings_service import get_setting


def _stale_topics(db: Session, user_id: uuid.UUID, stale_days: int) -> list[dict]:
    """Topics the student has practiced before but not recently."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
    rows = db.execute(
        select(
            Attempt.topic_id,
            Topic.name,
            Attempt.subject_id,
            Attempt.course_id,
            func.max(Attempt.attempted_at),
            func.count(Attempt.id),
        )
        .join(Topic, Topic.id == Attempt.topic_id)
        .where(Attempt.user_id == user_id, Attempt.topic_id.is_not(None))
        .group_by(Attempt.topic_id, Topic.name, Attempt.subject_id, Attempt.course_id)
        .having(func.max(Attempt.attempted_at) < cutoff)
        .order_by(func.max(Attempt.attempted_at).asc())
        .limit(5)
    ).all()
    return [
        {
            "topic_id": r[0],
            "topic_name": r[1],
            "subject_id": r[2],
            "course_id": r[3],
            "last_attempted": r[4],
            "attempts": r[5],
        }
        for r in rows
    ]


def build_recommendations(db: Session, user_id: uuid.UUID) -> list[dict]:
    recs: list[dict] = []

    weak_count = int(get_setting(db, "recommendation.weak_practice_count") or 20)
    stale_count = int(get_setting(db, "recommendation.stale_practice_count") or 10)
    challenge_count = int(get_setting(db, "recommendation.challenge_count") or 15)
    challenge_threshold = float(get_setting(db, "recommendation.challenge_accuracy_threshold") or 85)
    stale_days = int(get_setting(db, "recommendation.stale_days") or 14)
    seconds_per_q = int(get_setting(db, "daily_challenge.seconds_per_question") or 45)

    strong, weak = strong_weak_areas(db, user_id)

    # Rule 1: weakest area first.
    if weak:
        w = weak[0]
        recs.append(
            {
                "id": f"weak-{w['scope']}-{w.get('topic_id') or w.get('subject_id')}",
                "title": f"You struggle with {w['name']}.",
                "reason": f"{w['accuracy']}% accuracy over your last {w['attempts']} attempts.",
                "action": "practice_weak",
                "course_id": None,
                "subject_id": w["subject_id"],
                "topic_id": w["topic_id"],
                "difficulty": None,
                "question_count": weak_count,
                "estimated_minutes": round(weak_count * seconds_per_q / 60),
            }
        )

    # Rule 2: stale topic (practiced before, not recently).
    stale = _stale_topics(db, user_id, stale_days)
    if stale:
        s = stale[0]
        days_ago = (datetime.now(timezone.utc) - s["last_attempted"]).days
        recs.append(
            {
                "id": f"stale-{s['topic_id']}",
                "title": f"You haven't practiced {s['topic_name']} recently.",
                "reason": f"Last practiced {days_ago} days ago.",
                "action": "practice_stale",
                "course_id": s["course_id"],
                "subject_id": s["subject_id"],
                "topic_id": s["topic_id"],
                "difficulty": None,
                "question_count": stale_count,
                "estimated_minutes": round(stale_count * seconds_per_q / 60),
            }
        )

    # Rule 3: strong area -> push into hard questions.
    if strong:
        st = strong[0]
        recs.append(
            {
                "id": f"challenge-{st['scope']}-{st.get('topic_id') or st.get('subject_id')}",
                "title": f"Your {st['name']} accuracy is high. Try Hard questions.",
                "reason": f"{st['accuracy']}% accuracy - you're ready for a tougher set.",
                "action": "challenge_hard",
                "course_id": None,
                "subject_id": st["subject_id"],
                "topic_id": st["topic_id"],
                "difficulty": "hard",
                "question_count": challenge_count,
                "estimated_minutes": round(challenge_count * seconds_per_q / 60),
            }
        )

    return recs
