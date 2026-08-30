"""
Mock test / PYQ paper building, attempting, and scoring.

A `Test` (see models/test.py) serves both mock tests and PYQ papers. Building
supports two modes, both usable together in one request:
  * manual: explicit `questions` list (each optionally tagged to a section)
  * automatic: `auto_rules`, e.g. "25 questions from Quant, medium, marks=1"
    - the builder randomly samples published questions matching each rule.
"""
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import ContentStatus, TestAttemptStatus, TestType, XPReason
from app.models.question import Question
from app.models.test import Test, TestAttempt, TestQuestion, TestSection
from app.models.user import Profile
from app.schemas.test import SubmittedAnswer, TestCreate
from app.services import xp_service
from app.services.achievements_service import check_and_award
from app.services.attempt_service import record_practice_answer


def build_test(db: Session, payload: TestCreate, created_by: uuid.UUID) -> Test:
    test = Test(
        title=payload.title,
        test_type=payload.test_type,
        course_id=payload.course_id,
        exam_id=payload.exam_id,
        pyq_year=payload.pyq_year,
        pyq_paper_label=payload.pyq_paper_label,
        duration_minutes=payload.duration_minutes,
        negative_marking=payload.negative_marking,
        difficulty=payload.difficulty,
        instructions=payload.instructions,
        status=payload.status,
        created_by=created_by,
    )
    db.add(test)
    db.flush()

    section_by_name: dict[str, TestSection] = {}
    for i, s in enumerate(payload.sections):
        section = TestSection(test_id=test.id, name=s.name, order_index=s.order_index or i, num_questions=s.num_questions)
        db.add(section)
        section_by_name[s.name] = section
    db.flush()

    order_counter = 0
    for tq in payload.questions:
        section = None
        if tq.section_name:
            section = section_by_name.get(tq.section_name)
            if section is None:
                section = TestSection(test_id=test.id, name=tq.section_name, order_index=len(section_by_name))
                db.add(section)
                db.flush()
                section_by_name[tq.section_name] = section
        db.add(
            TestQuestion(
                test_id=test.id,
                section_id=section.id if section else None,
                question_id=tq.question_id,
                order_index=tq.order_index or order_counter,
                marks=tq.marks,
                negative_marks=tq.negative_marks,
            )
        )
        order_counter += 1

    for rule in payload.auto_rules:
        q = select(Question.id).where(Question.status == ContentStatus.PUBLISHED, Question.subject_id == rule.subject_id)
        if rule.topic_id:
            q = q.where(Question.topic_id == rule.topic_id)
        if rule.difficulty:
            q = q.where(Question.difficulty == rule.difficulty)
        candidate_ids = [row[0] for row in db.execute(q).all()]
        random.shuffle(candidate_ids)
        chosen = candidate_ids[: rule.count]

        section = section_by_name.get(rule.section_name)
        if section is None:
            section = TestSection(
                test_id=test.id, name=rule.section_name, order_index=len(section_by_name), num_questions=len(chosen)
            )
            db.add(section)
            db.flush()
            section_by_name[rule.section_name] = section
        else:
            section.num_questions += len(chosen)

        for qid in chosen:
            db.add(
                TestQuestion(
                    test_id=test.id,
                    section_id=section.id,
                    question_id=qid,
                    order_index=order_counter,
                    marks=rule.marks,
                    negative_marks=rule.negative_marks,
                )
            )
            order_counter += 1

    db.flush()

    totals = db.execute(
        select(func.count(TestQuestion.id), func.coalesce(func.sum(TestQuestion.marks), 0)).where(
            TestQuestion.test_id == test.id
        )
    ).one()
    test.total_questions = totals[0]
    test.total_marks = float(totals[1])
    if not payload.duration_minutes:
        test.duration_minutes = max(10, test.total_questions)
    db.flush()
    return test


def start_or_resume_attempt(db: Session, test: Test, user_id: uuid.UUID) -> TestAttempt:
    existing = db.execute(
        select(TestAttempt)
        .where(TestAttempt.test_id == test.id, TestAttempt.user_id == user_id, TestAttempt.status == TestAttemptStatus.IN_PROGRESS)
        .order_by(TestAttempt.started_at.desc())
    ).scalars().first()
    if existing:
        return existing

    attempt = TestAttempt(
        user_id=user_id, test_id=test.id, status=TestAttemptStatus.IN_PROGRESS, started_at=datetime.now(timezone.utc)
    )
    db.add(attempt)
    db.flush()
    return attempt


def submit_attempt(
    db: Session,
    test: Test,
    test_attempt: TestAttempt,
    profile: Profile,
    answers: list[SubmittedAnswer],
    total_time_seconds: int,
) -> dict:
    test_questions = db.execute(
        select(TestQuestion).where(TestQuestion.test_id == test.id)
    ).scalars().all()
    tq_by_question_id = {tq.question_id: tq for tq in test_questions}
    answer_by_question_id = {a.question_id: a for a in answers}

    questions = {
        q.id: q
        for q in db.execute(select(Question).where(Question.id.in_(list(tq_by_question_id.keys())))).scalars().all()
    }

    correct = incorrect = skipped = 0
    score = 0.0
    section_stats: dict[str, dict] = {}

    for question_id, tq in tq_by_question_id.items():
        question = questions.get(question_id)
        if question is None:
            continue
        ans = answer_by_question_id.get(question_id)
        selected = ans.selected_option if ans else None
        time_taken = ans.time_taken_seconds if ans else 0

        record_practice_answer(db, profile, question, selected, time_taken, test_attempt_id=test_attempt.id)

        section_name = tq.section_id and next((s.name for s in test.sections if s.id == tq.section_id), None)
        section_name = section_name or "General"
        stats = section_stats.setdefault(section_name, {"correct": 0, "incorrect": 0, "skipped": 0, "score": 0.0})

        if selected is None:
            skipped += 1
            stats["skipped"] += 1
        elif selected == question.correct_option:
            correct += 1
            score += tq.marks
            stats["correct"] += 1
            stats["score"] += tq.marks
        else:
            incorrect += 1
            score -= tq.negative_marks
            stats["incorrect"] += 1
            stats["score"] -= tq.negative_marks

    answered = correct + incorrect
    accuracy = round(100 * correct / answered, 1) if answered else 0.0

    test_attempt.status = TestAttemptStatus.SUBMITTED
    test_attempt.submitted_at = datetime.now(timezone.utc)
    test_attempt.score = score
    test_attempt.correct_count = correct
    test_attempt.incorrect_count = incorrect
    test_attempt.skipped_count = skipped
    test_attempt.accuracy = accuracy
    test_attempt.time_taken_seconds = total_time_seconds

    profile.tests_completed += 1
    if test.test_type == TestType.PYQ:
        profile.pyqs_completed += 1

    pct = round(100 * score / test.total_marks, 1) if test.total_marks else 0.0
    base = xp_service_completion_xp(db, pct)
    xp_service.award_xp(db, profile, base, XPReason.TEST_COMPLETED, "test_attempt", test_attempt.id)

    check_and_award(db, profile)
    db.flush()

    rank, total_participants = _rank_for_test(db, test.id, test_attempt.id, score)

    section_results = [
        {
            "name": name,
            "correct": s["correct"],
            "incorrect": s["incorrect"],
            "skipped": s["skipped"],
            "score": round(s["score"], 2),
            "accuracy": round(100 * s["correct"] / (s["correct"] + s["incorrect"]), 1)
            if (s["correct"] + s["incorrect"])
            else 0.0,
        }
        for name, s in section_stats.items()
    ]

    return {
        "test_attempt_id": test_attempt.id,
        "test_id": test.id,
        "test_title": test.title,
        "score": round(score, 2),
        "total_marks": test.total_marks,
        "percentage": pct,
        "correct_count": correct,
        "incorrect_count": incorrect,
        "skipped_count": skipped,
        "accuracy": accuracy,
        "time_taken_seconds": total_time_seconds,
        "rank": rank,
        "total_participants": total_participants,
        "section_results": section_results,
    }


def get_result(db: Session, test: Test, test_attempt: TestAttempt) -> dict:
    """
    Rebuild the same TestResultOut shape as `submit_attempt`'s return value,
    from already-persisted rows - used by GET /tests/attempts/{id}/result so
    a result page can be reloaded/bookmarked without re-submitting.
    """
    from app.models.attempt import Attempt

    test_questions = db.execute(select(TestQuestion).where(TestQuestion.test_id == test.id)).scalars().all()
    section_name_by_id = {s.id: s.name for s in test.sections}
    section_by_question_id = {tq.question_id: section_name_by_id.get(tq.section_id, "General") for tq in test_questions}

    attempts = db.execute(select(Attempt).where(Attempt.test_attempt_id == test_attempt.id)).scalars().all()
    section_stats: dict[str, dict] = {}
    for a in attempts:
        section_name = section_by_question_id.get(a.question_id, "General")
        stats = section_stats.setdefault(section_name, {"correct": 0, "incorrect": 0, "skipped": 0, "score": 0.0})
        if a.selected_option is None:
            stats["skipped"] += 1
        elif a.is_correct:
            stats["correct"] += 1
        else:
            stats["incorrect"] += 1

    # Marks per section aren't stored on Attempt (only correctness is), so
    # `score` per section is approximated from the test's uniform marking
    # scheme unless a question overrides it - good enough for the results
    # breakdown UI, while the authoritative total always comes from
    # `test_attempt.score`.
    tq_by_question = {tq.question_id: tq for tq in test_questions}
    for a in attempts:
        tq = tq_by_question.get(a.question_id)
        if not tq:
            continue
        section_name = section_by_question_id.get(a.question_id, "General")
        if a.selected_option is not None:
            section_stats[section_name]["score"] += tq.marks if a.is_correct else -tq.negative_marks

    section_results = [
        {
            "name": name,
            "correct": s["correct"],
            "incorrect": s["incorrect"],
            "skipped": s["skipped"],
            "score": round(s["score"], 2),
            "accuracy": round(100 * s["correct"] / (s["correct"] + s["incorrect"]), 1) if (s["correct"] + s["incorrect"]) else 0.0,
        }
        for name, s in section_stats.items()
    ]

    rank, total_participants = _rank_for_test(db, test.id, test_attempt.id, test_attempt.score)
    pct = round(100 * test_attempt.score / test.total_marks, 1) if test.total_marks else 0.0

    return {
        "test_attempt_id": test_attempt.id,
        "test_id": test.id,
        "test_title": test.title,
        "score": test_attempt.score,
        "total_marks": test.total_marks,
        "percentage": pct,
        "correct_count": test_attempt.correct_count,
        "incorrect_count": test_attempt.incorrect_count,
        "skipped_count": test_attempt.skipped_count,
        "accuracy": test_attempt.accuracy,
        "time_taken_seconds": test_attempt.time_taken_seconds,
        "rank": rank,
        "total_participants": total_participants,
        "section_results": section_results,
    }


def xp_service_completion_xp(db: Session, pct: float) -> int:
    from app.services.settings_service import get_setting

    base = int(get_setting(db, "xp.test.completion_base") or 0)
    per_pct = float(get_setting(db, "xp.test.completion_per_pct") or 0)
    return round(base + per_pct * pct)


def _rank_for_test(db: Session, test_id: uuid.UUID, this_attempt_id: uuid.UUID, score: float) -> tuple[int, int]:
    total = db.execute(
        select(func.count(TestAttempt.id)).where(TestAttempt.test_id == test_id, TestAttempt.status == TestAttemptStatus.SUBMITTED)
    ).scalar_one()
    higher = db.execute(
        select(func.count(TestAttempt.id)).where(
            TestAttempt.test_id == test_id, TestAttempt.status == TestAttemptStatus.SUBMITTED, TestAttempt.score > score
        )
    ).scalar_one()
    return higher + 1, total
