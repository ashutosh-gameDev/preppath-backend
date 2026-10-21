import uuid
from datetime import date

from app.schemas.common import ORMModel
from app.schemas.course import CourseOut


class EnrollRequest(ORMModel):
    course_id: uuid.UUID


class EnrollmentUpdate(ORMModel):
    # Null clears it. Purely informational (Home page countdown) - never
    # validated against anything else.
    target_exam_date: date | None = None


class EnrolledCourseOut(ORMModel):
    course: CourseOut
    enrolled_at: str
    questions_attempted: int
    accuracy: float
    # Question coverage - distinct questions attempted / total published
    # questions. Despite the name, NOT syllabus completion - see
    # syllabus_completion_pct for that.
    progress_pct: float
    # Topics + subtopics marked complete / total published topics +
    # subtopics - what the student has actually ticked off, independent of
    # question practice.
    syllabus_completion_pct: float
    target_exam_date: date | None = None
