"""
Student PYQ browsing: Course -> published PYQ Question Papers (grouped by year
in the app) -> the paper's questions.

A paper here is the `PYQPaper` a question is tagged to (models/pyq_paper.py) -
there is no separate PYQ "test" any more. A paper is visible to students only
once a super admin has published it, and only to students enrolled in its
course. Its questions are answered through the ordinary practice endpoint
(`POST /practice/answer`), which returns the correct option + explanation
right away and records the attempt for the student's stats.
"""
import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.attempt import Attempt
from app.models.enrollment import CourseEnrollment
from app.models.enums import ContentStatus
from app.models.pyq_paper import PYQPaper
from app.models.question import Question
from app.models.user import User
from app.schemas.pyq_paper import PYQPaperProgressOut, PYQPaperStudentOut
from app.schemas.question import QuestionAttemptOut

router = APIRouter(prefix="/pyq", tags=["pyq"])

# Draft questions are shown too (publishing the paper is the approval step);
# only archived ones are hidden.
_VISIBLE = Question.status != ContentStatus.ARCHIVED


def _is_enrolled(db: Session, user: User, course_id: uuid.UUID) -> bool:
    return (
        db.execute(
            select(CourseEnrollment.id).where(CourseEnrollment.user_id == user.id, CourseEnrollment.course_id == course_id)
        ).first()
        is not None
    )


def _effective_courses(db: Session, papers: list[PYQPaper]) -> dict[uuid.UUID, uuid.UUID]:
    """paper id -> its course. The paper's own course when set, otherwise the
    course most of its questions belong to (papers are often created without
    one - the questions always have a course)."""
    result = {p.id: p.course_id for p in papers if p.course_id}
    missing = [p.id for p in papers if not p.course_id]
    if missing:
        rows = db.execute(
            select(Question.pyq_paper_id, Question.course_id, func.count(Question.id))
            .where(Question.pyq_paper_id.in_(missing), _VISIBLE)
            .group_by(Question.pyq_paper_id, Question.course_id)
        ).all()
        votes: dict[uuid.UUID, Counter] = {}
        for paper_id, course_id, n in rows:
            votes.setdefault(paper_id, Counter())[course_id] += n
        for paper_id, counter in votes.items():
            result[paper_id] = counter.most_common(1)[0][0]
    return result


def _get_visible_paper(db: Session, user: User, paper_id: uuid.UUID) -> tuple[PYQPaper, uuid.UUID]:
    paper = db.get(PYQPaper, paper_id)
    if paper is None or not paper.is_published:
        raise HTTPException(status_code=404, detail="Paper not found")
    course_id = _effective_courses(db, [paper]).get(paper.id)
    if course_id is None or not _is_enrolled(db, user, course_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper, course_id


@router.get("/courses/{course_id}/papers", response_model=list[PYQPaperStudentOut])
def list_course_papers(course_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _is_enrolled(db, user, course_id):
        return []

    candidates = db.execute(
        select(PYQPaper).where(
            PYQPaper.is_published.is_(True), or_(PYQPaper.course_id == course_id, PYQPaper.course_id.is_(None))
        )
    ).scalars().all()
    courses = _effective_courses(db, candidates)
    papers = [p for p in candidates if courses.get(p.id) == course_id]
    if not papers:
        return []
    ids = [p.id for p in papers]

    totals = dict(
        db.execute(
            select(Question.pyq_paper_id, func.count(Question.id)).where(Question.pyq_paper_id.in_(ids), _VISIBLE).group_by(Question.pyq_paper_id)
        ).all()
    )
    done = dict(
        db.execute(
            select(Question.pyq_paper_id, func.count(distinct(Attempt.question_id)))
            .join(Attempt, Attempt.question_id == Question.id)
            .where(Attempt.user_id == user.id, Question.pyq_paper_id.in_(ids), _VISIBLE)
            .group_by(Question.pyq_paper_id)
        ).all()
    )

    papers.sort(key=lambda p: (-(p.year or 0), p.display_name))
    return [
        PYQPaperStudentOut(
            id=p.id,
            name=p.display_name,
            exam_name=p.exam_name,
            year=p.year,
            label=p.label,
            language=p.language,
            course_id=course_id,
            question_count=totals.get(p.id, 0),
            attempted_count=done.get(p.id, 0),
        )
        for p in papers
        if totals.get(p.id, 0) > 0
    ]


@router.get("/papers/{paper_id}/questions", response_model=list[QuestionAttemptOut])
def get_paper_questions(paper_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The paper's questions in upload order, without answers - those come back
    per question from POST /practice/answer."""
    paper, _ = _get_visible_paper(db, user, paper_id)
    return db.execute(
        select(Question).where(Question.pyq_paper_id == paper.id, _VISIBLE).order_by(Question.display_number)
    ).scalars().all()


@router.get("/papers/{paper_id}/progress", response_model=PYQPaperProgressOut)
def get_paper_progress(paper_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Which of the paper's questions this student has answered - lets the app
    resume where they stopped."""
    paper, _ = _get_visible_paper(db, user, paper_id)
    ids = db.execute(
        select(distinct(Attempt.question_id))
        .join(Question, Question.id == Attempt.question_id)
        .where(Attempt.user_id == user.id, Question.pyq_paper_id == paper.id)
    ).scalars().all()
    return PYQPaperProgressOut(attempted_ids=list(ids))
