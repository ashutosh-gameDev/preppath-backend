import uuid

from app.schemas.common import ORMModel
from app.schemas.course import CourseOut


class EnrollRequest(ORMModel):
    course_id: uuid.UUID


class EnrolledCourseOut(ORMModel):
    course: CourseOut
    enrolled_at: str
    questions_attempted: int
    accuracy: float
    progress_pct: float
