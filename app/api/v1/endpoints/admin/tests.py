"""
Admin test builder - creates mock `Test` rows, manually and/or via automatic
subject/topic/difficulty selection rules. See services/test_service.py.
PYQ papers are no longer built as tests: students open the PYQ Question Paper
itself (see admin/pyq_papers.py and the student /pyq endpoints).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_content_access
from app.db.session import get_db
from app.models.test import Test, TestSection
from app.models.user import User
from app.schemas.common import Message
from app.schemas.test import (
    BulkTestUpdateRequest,
    BulkTestUpdateResult,
    TestCreate,
    TestDetailOut,
    TestListItemOut,
    TestUpdate,
)
from app.services import test_service
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/tests", tags=["admin:tests"])


def _to_detail(db: Session, test: Test) -> TestDetailOut:
    sections = db.execute(select(TestSection).where(TestSection.test_id == test.id)).scalars().all()
    return TestDetailOut(
        id=test.id,
        title=test.title,
        test_type=test.test_type,
        course_id=test.course_id,
        pyq_year=test.pyq_year,
        pyq_paper_label=test.pyq_paper_label,
        is_live=test.is_live,
        live_starts_at=test.live_starts_at,
        live_ends_at=test.live_ends_at,
        course_content_version=test.course.content_version if test.course else None,
        duration_minutes=test.duration_minutes,
        total_questions=test.total_questions,
        total_marks=test.total_marks,
        negative_marking=test.negative_marking,
        difficulty=test.difficulty,
        status=test.status,
        instructions=test.instructions,
        sections=sections,
    )


@router.get("", response_model=list[TestListItemOut])
def list_tests(test_type: str | None = None, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    q = select(Test)
    if test_type:
        q = q.where(Test.test_type == test_type)
    tests = db.execute(q.order_by(Test.created_at.desc())).scalars().all()
    return [_to_detail(db, t) for t in tests]


@router.get("/{test_id}", response_model=TestDetailOut)
def get_test(test_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    test = db.get(Test, test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    return _to_detail(db, test)


@router.post("", response_model=TestDetailOut)
def create_test(payload: TestCreate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    if payload.test_type != "mock":
        raise HTTPException(
            status_code=400,
            detail="PYQ papers are managed under Question Papers - only mock tests are built here.",
        )
    test = test_service.build_test(db, payload, admin.id)
    log_action(db, admin.id, "create", "test", test.id, {"test_type": test.test_type})
    return _to_detail(db, test)


@router.patch("/{test_id}", response_model=TestDetailOut)
def update_test(test_id: uuid.UUID, payload: TestUpdate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    test = db.get(Test, test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(test, field, value)
    db.flush()
    log_action(db, admin.id, "update", "test", test.id)
    return _to_detail(db, test)


@router.delete("/{test_id}", response_model=Message)
def delete_test(test_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    test = db.get(Test, test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    db.delete(test)
    db.flush()
    log_action(db, admin.id, "delete", "test", test_id)
    return Message(detail="Test deleted")


@router.post("/bulk-update", response_model=BulkTestUpdateResult)
def bulk_update_tests(
    payload: BulkTestUpdateRequest, admin: User = Depends(require_content_access), db: Session = Depends(get_db)
):
    """Apply one patch (publish/unpublish/archive, or fix year/course
    tagging) to every test in `test_ids` at once - the Tests/PYQ admin
    list's bulk-select action bar."""
    data = payload.patch.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No field to update was provided")

    tests = db.execute(select(Test).where(Test.id.in_(payload.test_ids))).scalars().all()
    for test in tests:
        for field, value in data.items():
            setattr(test, field, value)
    db.flush()
    log_action(
        db, admin.id, "bulk_update", "test",
        extra={"test_ids": [str(tid) for tid in payload.test_ids], "fields": list(data.keys())},
    )
    return BulkTestUpdateResult(updated=len(tests))
