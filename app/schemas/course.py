import uuid

from pydantic import Field

from app.schemas.common import ORMModel


class TopicBase(ORMModel):
    name: str
    order_index: int = 0
    is_published: bool = False
    video_url: str | None = None


class TopicCreate(TopicBase):
    pass


class TopicUpdate(ORMModel):
    name: str | None = None
    order_index: int | None = None
    is_published: bool | None = None
    video_url: str | None = None


class TopicOut(TopicBase):
    id: uuid.UUID
    subject_id: uuid.UUID
    slug: str


class TopicProgressIn(ORMModel):
    is_completed: bool = True


class TopicProgressOut(ORMModel):
    topic_id: uuid.UUID
    is_completed: bool


class SubjectBase(ORMModel):
    name: str
    order_index: int = 0
    is_published: bool = False


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(ORMModel):
    name: str | None = None
    order_index: int | None = None
    is_published: bool | None = None


class SubjectOut(SubjectBase):
    id: uuid.UUID
    course_id: uuid.UUID
    slug: str
    topics: list[TopicOut] = Field(default_factory=list)


class CourseBase(ORMModel):
    name: str
    description: str | None = None
    icon: str | None = None
    is_published: bool = False


class CourseCreate(CourseBase):
    pass


class CourseUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    is_published: bool | None = None


class CourseOut(CourseBase):
    id: uuid.UUID
    slug: str


class CourseTreeOut(CourseOut):
    subjects: list[SubjectOut] = Field(default_factory=list)
