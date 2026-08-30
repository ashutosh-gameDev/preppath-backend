"""
Recording a single practice-question attempt: writes the `Attempt` row,
awards XP, updates cached `Profile` counters/streak, and checks achievements.
Test-attempt scoring (many questions at once) lives in `test_service.py` but
also writes through `Attempt` rows so both paths feed the same analytics.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.enums import XPReason
from app.models.question import Question
from app.models.user import Profile
from app.services import xp_service
from app.services.achievements_service import check_and_award


def record_practice_answer(
    db: Session,
    profile: Profile,
    question: Question,
    selected_option: str | None,
    time_taken_seconds: int,
    test_attempt_id: uuid.UUID | None = None,
) -> Attempt:
    is_correct = None if selected_option is None else (selected_option == question.correct_option)

    attempt = Attempt(
        user_id=profile.user_id,
        question_id=question.id,
        course_id=question.course_id,
        subject_id=question.subject_id,
        topic_id=question.topic_id,
        test_attempt_id=test_attempt_id,
        difficulty=question.difficulty,
        question_type=question.question_type,
        selected_option=selected_option,
        is_correct=is_correct,
        time_taken_seconds=time_taken_seconds,
        attempted_at=datetime.now(timezone.utc),
    )
    db.add(attempt)

    profile.questions_attempted += 1
    if is_correct:
        profile.questions_correct += 1

    xp_service.touch_daily_activity(db, profile)

    if selected_option is not None:
        if is_correct:
            xp_amount = xp_service.xp_for_correct_answer(db, question.difficulty)
            xp_service.award_xp(db, profile, xp_amount, XPReason.QUESTION_CORRECT, "question", question.id)
        else:
            from app.services.settings_service import get_setting

            participation = int(get_setting(db, "xp.attempt.participation") or 0)
            if participation:
                xp_service.award_xp(db, profile, participation, XPReason.QUESTION_ATTEMPT, "question", question.id)

    db.flush()
    check_and_award(db, profile)
    return attempt
