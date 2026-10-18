import uuid

from app.schemas.common import ORMModel


class VideoItem(ORMModel):
    url: str
    title: str
    course_id: uuid.UUID
    course_name: str
    subject_name: str
    topic_name: str
    subtopic_name: str | None = None
    watched: bool


class VideoWatchedIn(ORMModel):
    video_url: str
