"""
PYQ browsing hierarchy: Exam -> Year -> Paper. Papers themselves are `Test`
rows with `test_type='pyq'` (see models/test.py) - starting/submitting a PYQ
paper reuses the exact same endpoints as mock tests (`/tests/{id}/start`,
`/tests/{id}/attempts/{id}/submit`).
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ContentStatus, TestType
from app.models.exam import Exam
from app.models.test import Test
from app.models.user import User
from app.schemas.exam import ExamOut

router = APIRouter(prefix="/pyq", tags=["pyq"])


@router.get("/exams", response_model=list[ExamOut])
def list_pyq_exams(db: Session = Depends(get_db)):
    exam_ids = db.execute(
        select(distinct(Test.exam_id)).where(
            Test.test_type == TestType.PYQ, Test.status == ContentStatus.PUBLISHED, Test.exam_id.is_not(None)
        )
    ).scalars().all()
    if not exam_ids:
        return []
    return db.execute(select(Exam).where(Exam.id.in_(exam_ids), Exam.is_published.is_(True)).order_by(Exam.name)).scalars().all()


@router.get("/exams/{exam_id}/years", response_model=list[int])
def list_pyq_years(exam_id: uuid.UUID, db: Session = Depends(get_db)):
    years = db.execute(
        select(distinct(Test.pyq_year))
        .where(Test.exam_id == exam_id, Test.test_type == TestType.PYQ, Test.status == ContentStatus.PUBLISHED)
        .order_by(Test.pyq_year.desc())
    ).scalars().all()
    return [y for y in years if y is not None]


@router.get("/exams/{exam_id}/years/{year}/papers")
def list_pyq_papers(exam_id: uuid.UUID, year: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.api.v1.endpoints.tests import _to_list_item

    papers = db.execute(
        select(Test).where(
            Test.exam_id == exam_id,
            Test.pyq_year == year,
            Test.test_type == TestType.PYQ,
            Test.status == ContentStatus.PUBLISHED,
        ).order_by(Test.pyq_paper_label)
    ).scalars().all()
    return [_to_list_item(db, p, user.id) for p in papers]
