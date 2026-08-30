"""
Mock test + PYQ paper taking (both are `Test` rows - see models/test.py).
Browsing the PYQ exam/year/paper hierarchy lives in `pyq.py`; this module
handles listing, starting, resuming, submitting and reviewing any Test.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_profile, get_current_user
from app.db.session import get_db
from app.models.attempt import Attempt
from app.models.enums import ContentStatus, TestAttemptStatus
from app.models.question import Question
from app.models.test import Test, TestAttempt, TestQuestion, TestSection
from app.models.user import Profile, User
from app.schemas.question import QuestionAttemptOut, QuestionReviewOut
from app.schemas.test import (
    TestAttemptHistoryItem,
    TestAttemptStartOut,
    TestDetailOut,
    TestListItemOut,
    TestResultOut,
    TestSubmitRequest,
)
from app.services import test_service

router = APIRouter(prefix="/tests", tags=["tests"])


def _to_list_item(db: Session, test: Test, user_id: uuid.UUID) -> TestListItemOut:
    attempts = db.execute(
        select(TestAttempt).where(
            TestAttempt.test_id == test.id, TestAttempt.user_id == user_id, TestAttempt.status == TestAttemptStatus.SUBMITTED
        )
    ).scalars().all()
    best = max((a.score for a in attempts), default=None)
    return TestListItemOut(
        id=test.id,
        title=test.title,
        test_type=test.test_type,
        course_id=test.course_id,
        exam_id=test.exam_id,
        pyq_year=test.pyq_year,
        pyq_paper_label=test.pyq_paper_label,
        duration_minutes=test.duration_minutes,
        total_questions=test.total_questions,
        total_marks=test.total_marks,
        negative_marking=test.negative_marking,
        difficulty=test.difficulty,
        status=test.status,
        attempted=len(attempts) > 0,
        best_score=best,
    )


@router.get("", response_model=list[TestListItemOut])
def list_tests(
    course_id: uuid.UUID | None = None,
    exam_id: uuid.UUID | None = None,
    test_type: str = "mock",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = select(Test).where(Test.status == ContentStatus.PUBLISHED, Test.test_type == test_type)
    if course_id:
        q = q.where(Test.course_id == course_id)
    if exam_id:
        q = q.where(Test.exam_id == exam_id)
    tests = db.execute(q.order_by(Test.created_at.desc())).scalars().all()
    return [_to_list_item(db, t, user.id) for t in tests]


@router.get("/{test_id}", response_model=TestDetailOut)
def get_test(test_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    test = db.get(Test, test_id)
    if test is None or test.status != ContentStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Test not found")
    item = _to_list_item(db, test, user.id)
    sections = db.execute(select(TestSection).where(TestSection.test_id == test.id)).scalars().all()
    return TestDetailOut(**item.model_dump(), instructions=test.instructions, sections=sections)


@router.post("/{test_id}/start", response_model=TestAttemptStartOut)
def start_test(test_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    test = db.get(Test, test_id)
    if test is None or test.status != ContentStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Test not found")

    attempt = test_service.start_or_resume_attempt(db, test, user.id)

    test_questions = db.execute(
        select(TestQuestion).where(TestQuestion.test_id == test.id).order_by(TestQuestion.order_index)
    ).scalars().all()
    section_names = {s.id: s.name for s in db.execute(select(TestSection).where(TestSection.test_id == test.id)).scalars().all()}
    questions = {
        q.id: q for q in db.execute(select(Question).where(Question.id.in_([tq.question_id for tq in test_questions]))).scalars().all()
    }

    payload_questions = [
        {
            "order_index": tq.order_index,
            "section_name": section_names.get(tq.section_id),
            "marks": tq.marks,
            "negative_marks": tq.negative_marks,
            "question": QuestionAttemptOut.model_validate(questions[tq.question_id]).model_dump(mode="json"),
        }
        for tq in test_questions
        if tq.question_id in questions
    ]

    item = _to_list_item(db, test, user.id)
    sections = db.execute(select(TestSection).where(TestSection.test_id == test.id)).scalars().all()
    detail = TestDetailOut(**item.model_dump(), instructions=test.instructions, sections=sections)

    return TestAttemptStartOut(
        test_attempt_id=attempt.id, test=detail, started_at=attempt.started_at, questions=payload_questions
    )


@router.post("/{test_id}/attempts/{attempt_id}/submit", response_model=TestResultOut)
def submit_test(
    test_id: uuid.UUID,
    attempt_id: uuid.UUID,
    payload: TestSubmitRequest,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    test = db.get(Test, test_id)
    attempt = db.get(TestAttempt, attempt_id)
    if test is None or attempt is None or attempt.test_id != test_id or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Test attempt not found")
    if attempt.status != TestAttemptStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="This attempt was already submitted")

    total_time = int((datetime.now(timezone.utc) - attempt.started_at).total_seconds())
    result = test_service.submit_attempt(db, test, attempt, profile, payload.answers, total_time)
    return TestResultOut(**result)


@router.get("/attempts/{attempt_id}/result", response_model=TestResultOut)
def get_test_result(attempt_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempt = db.get(TestAttempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Test attempt not found")
    if attempt.status != TestAttemptStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="This attempt has not been submitted yet")
    test = db.get(Test, attempt.test_id)
    result = test_service.get_result(db, test, attempt)
    return TestResultOut(**result)


@router.get("/attempts/history", response_model=list[TestAttemptHistoryItem])
def test_attempt_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(TestAttempt, Test)
        .join(Test, Test.id == TestAttempt.test_id)
        .where(TestAttempt.user_id == user.id, TestAttempt.status == TestAttemptStatus.SUBMITTED)
        .order_by(TestAttempt.submitted_at.desc())
    ).all()
    return [
        TestAttemptHistoryItem(
            test_attempt_id=a.id,
            test_id=t.id,
            test_title=t.title,
            test_type=t.test_type,
            status=a.status,
            score=a.score,
            total_marks=t.total_marks,
            accuracy=a.accuracy,
            submitted_at=a.submitted_at,
        )
        for a, t in rows
    ]


@router.get("/attempts/{attempt_id}/review", response_model=list[QuestionReviewOut])
def review_test_attempt(attempt_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempt = db.get(TestAttempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Test attempt not found")

    test_questions = db.execute(
        select(TestQuestion).where(TestQuestion.test_id == attempt.test_id).order_by(TestQuestion.order_index)
    ).scalars().all()
    questions_by_id = {
        q.id: q
        for q in db.execute(select(Question).where(Question.id.in_([tq.question_id for tq in test_questions]))).scalars().all()
    }
    return [questions_by_id[tq.question_id] for tq in test_questions if tq.question_id in questions_by_id]
