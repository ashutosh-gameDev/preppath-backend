"""
PYQ browsing hierarchy: Course -> Year -> Paper. Papers themselves are `Test`
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
from app.models.course import Course
from app.models.enums import ContentStatus, TestType
from app.models.test import Test
from app.models.user import User
from app.schemas.course import CourseOut

router = APIRouter(prefix="/pyq", tags=["pyq"])


@router.get("/courses", response_model=list[CourseOut])
def list_pyq_courses(db: Session = Depends(get_db)):
    """Every published course that has at least one published PYQ paper -
    the top level of the browsing hierarchy (student-web scopes this further
    to the caller's own enrolled courses client-side)."""
    course_ids = db.execute(
        select(distinct(Test.course_id)).where(
            Test.test_type == TestType.PYQ, Test.status == ContentStatus.PUBLISHED, Test.course_id.is_not(None)
        )
    ).scalars().all()
    if not course_ids:
        return []
    return db.execute(
        select(Course).where(Course.id.in_(course_ids), Course.is_published.is_(True)).order_by(Course.name)
    ).scalars().all()


@router.get("/courses/{course_id}/years", response_model=list[int])
def list_pyq_years(course_id: uuid.UUID, db: Session = Depends(get_db)):
    years = db.execute(
        select(distinct(Test.pyq_year))
        .where(Test.course_id == course_id, Test.test_type == TestType.PYQ, Test.status == ContentStatus.PUBLISHED)
        .order_by(Test.pyq_year.desc())
    ).scalars().all()
    return [y for y in years if y is not None]


@router.get("/courses/{course_id}/years/{year}/papers")
def list_pyq_papers(course_id: uuid.UUID, year: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.api.v1.endpoints.tests import _to_list_item

    papers = db.execute(
        select(Test).where(
            Test.course_id == course_id,
            Test.pyq_year == year,
            Test.test_type == TestType.PYQ,
            Test.status == ContentStatus.PUBLISHED,
        ).order_by(Test.pyq_paper_label)
    ).scalars().all()
    return [_to_list_item(db, p, user.id) for p in papers]
