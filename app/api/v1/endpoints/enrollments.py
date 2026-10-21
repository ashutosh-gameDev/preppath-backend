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
from app.models.course import Course, Subject, Subtopic, SubtopicProgress, Topic, TopicProgress
from app.models.enrollment import CourseEnrollment
from app.models.enums import ContentStatus
from app.models.question import Question
from app.models.user import Profile, User
from app.schemas.common import Message
from app.schemas.enrollment import EnrolledCourseOut, EnrollmentUpdate, EnrollRequest
from app.services.premium_service import is_premium

# Normal tier: one course at a time. Pro/Premium: unlimited courses - see
# services/premium_service.is_premium (true for either paid tier).
FREE_COURSE_LIMIT = 1

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

        total_topics = db.execute(
            select(func.count(Topic.id))
            .join(Subject, Subject.id == Topic.subject_id)
            .where(Subject.course_id == course.id, Topic.is_published.is_(True))
        ).scalar_one()
        total_subtopics = db.execute(
            select(func.count(Subtopic.id))
            .join(Topic, Topic.id == Subtopic.topic_id)
            .join(Subject, Subject.id == Topic.subject_id)
            .where(Subject.course_id == course.id, Subtopic.is_published.is_(True))
        ).scalar_one()
        completed_topics = db.execute(
            select(func.count(TopicProgress.id))
            .join(Topic, Topic.id == TopicProgress.topic_id)
            .join(Subject, Subject.id == Topic.subject_id)
            .where(TopicProgress.user_id == user.id, TopicProgress.is_completed.is_(True), Subject.course_id == course.id)
        ).scalar_one()
        completed_subtopics = db.execute(
            select(func.count(SubtopicProgress.id))
            .join(Subtopic, Subtopic.id == SubtopicProgress.subtopic_id)
            .join(Topic, Topic.id == Subtopic.topic_id)
            .join(Subject, Subject.id == Topic.subject_id)
            .where(
                SubtopicProgress.user_id == user.id,
                SubtopicProgress.is_completed.is_(True),
                Subject.course_id == course.id,
            )
        ).scalar_one()
        total_syllabus_items = total_topics + total_subtopics
        completed_syllabus_items = completed_topics + completed_subtopics
        syllabus_completion_pct = (
            round(100 * completed_syllabus_items / total_syllabus_items, 1) if total_syllabus_items else 0.0
        )

        out.append(
            EnrolledCourseOut(
                course=course,
                enrolled_at=e.created_at.isoformat(),
                questions_attempted=answered_row,
                accuracy=accuracy,
                progress_pct=min(100.0, progress_pct),
                syllabus_completion_pct=min(100.0, syllabus_completion_pct),
                target_exam_date=e.target_exam_date,
            )
        )
    return out


@router.patch("/{course_id}", response_model=Message)
def update_enrollment(
    course_id: uuid.UUID, payload: EnrollmentUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Currently just the exam-countdown date shown on Home."""
    enrollment = db.execute(
        select(CourseEnrollment).where(CourseEnrollment.user_id == user.id, CourseEnrollment.course_id == course_id)
    ).scalar_one_or_none()
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(enrollment, field, value)
    db.flush()
    return Message(detail="Updated")


@router.post("", response_model=Message)
def enroll(payload: EnrollRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = db.get(Course, payload.course_id)
    if course is None or not course.is_published:
        raise HTTPException(status_code=404, detail="Course not found")
    existing = db.execute(
        select(CourseEnrollment).where(CourseEnrollment.user_id == user.id, CourseEnrollment.course_id == payload.course_id)
    ).scalar_one_or_none()
    if existing is None:
        profile = db.get(Profile, user.id)
        if not (profile and is_premium(profile)):
            current_count = db.execute(
                select(func.count(CourseEnrollment.id)).where(CourseEnrollment.user_id == user.id)
            ).scalar_one()
            if current_count >= FREE_COURSE_LIMIT:
                raise HTTPException(
                    status_code=403,
                    detail="Free plan allows only 1 course at a time - upgrade to Premium to select more.",
                )
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
