"""MCQ practice: fetch a batch of questions, answer one at a time, track a
'continue practice' pointer via the most recent attempt per course/subject/topic."""
import random
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_profile, get_current_user
from app.db.session import get_db
from app.models.attempt import Attempt
from app.models.course import Course, Subject, Topic
from app.models.enums import ContentStatus
from app.models.question import Question
from app.models.user import Profile, User
from app.schemas.attempt import PracticeAnswerRequest, PracticeAnswerResult, PracticeSessionRequest
from app.schemas.gamification import DailyChallengeOut
from app.schemas.question import QuestionAttemptOut
from app.services.attempt_service import record_practice_answer
from app.services.settings_service import get_setting

router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("/session", response_model=list[QuestionAttemptOut])
def start_practice_session(
    payload: PracticeSessionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    q = select(Question).where(Question.status == ContentStatus.PUBLISHED, Question.course_id == payload.course_id)
    if payload.subject_id:
        q = q.where(Question.subject_id == payload.subject_id)
    if payload.topic_id:
        q = q.where(Question.topic_id == payload.topic_id)
    if payload.difficulty:
        q = q.where(Question.difficulty == payload.difficulty)
    if payload.question_type:
        q = q.where(Question.question_type == payload.question_type)

    if payload.exclude_attempted:
        attempted_ids = select(Attempt.question_id).where(Attempt.user_id == user.id)
        q = q.where(Question.id.not_in(attempted_ids))

    candidates = db.execute(q).scalars().all()
    random.shuffle(candidates)
    selected = candidates[: payload.count]

    if not selected and payload.exclude_attempted:
        # Ran out of fresh questions - fall back to allowing repeats rather
        # than returning an empty session.
        q2 = select(Question).where(
            Question.status == ContentStatus.PUBLISHED, Question.course_id == payload.course_id
        )
        if payload.subject_id:
            q2 = q2.where(Question.subject_id == payload.subject_id)
        if payload.topic_id:
            q2 = q2.where(Question.topic_id == payload.topic_id)
        candidates = db.execute(q2).scalars().all()
        random.shuffle(candidates)
        selected = candidates[: payload.count]

    return selected


@router.post("/answer", response_model=PracticeAnswerResult)
def submit_practice_answer(
    payload: PracticeAnswerRequest,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    question = db.get(Question, payload.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    xp_before = profile.xp_total
    attempt = record_practice_answer(
        db, profile, question, payload.selected_option, payload.time_taken_seconds
    )

    return PracticeAnswerResult(
        is_correct=attempt.is_correct,
        correct_option=question.correct_option,
        explanation=question.explanation,
        xp_earned=profile.xp_total - xp_before,
        question=question,
        streak_current=profile.current_streak,
        xp_total=profile.xp_total,
    )


@router.get("/continue")
def get_continue_practice(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Where the student left off: most recent standalone-practice attempt
    (test attempts are excluded - those have their own 'resume test' flow)."""
    last = db.execute(
        select(Attempt)
        .where(Attempt.user_id == user.id, Attempt.test_attempt_id.is_(None))
        .order_by(Attempt.attempted_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if last is None:
        return None

    course = db.get(Course, last.course_id)
    subject = db.get(Subject, last.subject_id)
    topic = db.get(Topic, last.topic_id) if last.topic_id else None

    total_in_scope = db.execute(
        select(Question).where(Question.status == ContentStatus.PUBLISHED, Question.subject_id == last.subject_id)
    ).scalars().all()
    attempted_in_scope = db.execute(
        select(Attempt.question_id).where(Attempt.user_id == user.id, Attempt.subject_id == last.subject_id)
    ).scalars().all()
    progress_pct = (
        round(100 * len(set(attempted_in_scope)) / len(total_in_scope), 1) if total_in_scope else 0.0
    )

    return {
        "course_id": course.id if course else None,
        "course_name": course.name if course else None,
        "subject_id": subject.id if subject else None,
        "subject_name": subject.name if subject else None,
        "topic_id": topic.id if topic else None,
        "topic_name": topic.name if topic else None,
        "progress_pct": progress_pct,
        "last_attempted_at": last.attempted_at,
    }


@router.get("/daily-challenge", response_model=DailyChallengeOut)
def get_daily_challenge(
    course_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    """
    A lightweight, deterministic 'daily challenge': practice `daily_goal_questions`
    (or a configured default) questions today. No separate challenge-content
    table is needed for v1 - progress is simply today's attempt count against
    the goal, and XP available is estimated from the medium-difficulty XP rate.
    """
    default_count = int(get_setting(db, "daily_challenge.question_count") or 10)
    seconds_per_q = int(get_setting(db, "daily_challenge.seconds_per_question") or 45)
    xp_per_correct = int(get_setting(db, "xp.correct.medium") or 10)
    bonus = int(get_setting(db, "xp.daily_challenge.bonus") or 0)

    question_count = profile.daily_goal_questions or default_count

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    questions_done = db.execute(
        select(func.count(Attempt.id)).where(Attempt.user_id == user.id, Attempt.attempted_at >= today_start)
    ).scalar_one()

    return DailyChallengeOut(
        date=today_start.date().isoformat(),
        course_id=course_id,
        question_count=question_count,
        estimated_minutes=round(question_count * seconds_per_q / 60),
        xp_available=question_count * xp_per_correct + bonus,
        completed=questions_done >= question_count,
        questions_done=min(questions_done, question_count),
    )
