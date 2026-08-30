"""
"My Courses" - the student's explicit course enrollments. Separate from
practice history (see models/enrollment.py docstring): a student is enrolled
the moment they pick a course, before ever answering a question in it.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.enrollment import CourseEnrollment
from app.models.enums import ContentStatus
from app.models.question import Question
from app.models.user import User
from app.schemas.common import Message
from app.schemas.enrollment import EnrolledCourseOut, EnrollRequest

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.get("", response_model=list[EnrolledCourseOut])
def list_my_enrollments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enrollments = db.execute(
        select(CourseEnrollment).where(CourseEnrollment.user_id == user.id).order_by(CourseEnrollment.created_at)
    ).scalars().all()

    out = []
    for e in enrollments:
        course = db.get(Course, e.course_id)
        if course is None:
            continue
        total_questions = db.execute(
            select(func.count(Question.id)).where(Question.course_id == course.id, Question.status == ContentStatus.PUBLISHED)
        ).scalar_one()
        answered_row = db.execute(
            select(func.count(Attempt.selected_option)).where(Attempt.user_id == user.id, Attempt.course_id == course.id)
        ).scalar_one()
        correct_row = db.execute(
            select(func.count(Attempt.id)).where(
                Attempt.user_id == user.id, Attempt.course_id == course.id, Attempt.is_correct.is_(True)
            )
        ).scalar_one()
        distinct_questions = db.execute(
            select(func.count(func.distinct(Attempt.question_id))).where(
                Attempt.user_id == user.id, Attempt.course_id == course.id
            )
        ).scalar_one()

        accuracy = round(100 * correct_row / answered_row, 1) if answered_row else 0.0
        progress_pct = round(100 * distinct_questions / total_questions, 1) if total_questions else 0.0

        out.append(
            EnrolledCourseOut(
                course=course,
                enrolled_at=e.created_at.isoformat(),
                questions_attempted=answered_row,
                accuracy=accuracy,
                progress_pct=min(100.0, progress_pct),
            )
        )
    return out


@router.post("", response_model=Message)
def enroll(payload: EnrollRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = db.get(Course, payload.course_id)
    if course is None or not course.is_published:
        raise HTTPException(status_code=404, detail="Course not found")
    existing = db.execute(
        select(CourseEnrollment).where(CourseEnrollment.user_id == user.id, CourseEnrollment.course_id == payload.course_id)
    ).scalar_one_or_none()
    if existing is None:
        db.add(CourseEnrollment(user_id=user.id, course_id=payload.course_id))
        db.flush()
    return Message(detail=f"Enrolled in {course.name}")


@router.delete("/{course_id}", response_model=Message)
def unenroll(course_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(
        select(CourseEnrollment).where(CourseEnrollment.user_id == user.id, CourseEnrollment.course_id == course_id)
    ).scalar_one_or_none()
    if existing:
        db.delete(existing)
        db.flush()
    return Message(detail="Unenrolled")
