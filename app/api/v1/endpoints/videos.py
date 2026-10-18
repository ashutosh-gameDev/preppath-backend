"""Student-facing video list - built from Topic.video_url / Subtopic.
youtube_videos across the student's enrolled courses (no dedicated Video
table, see models/video_watch.py), plus marking a video watched/unwatched.
Backs the Dashboard's Videos card (replaces the old Continue Practice card)."""
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course, Subject, Topic
from app.models.enrollment import CourseEnrollment
from app.models.user import User
from app.models.video_watch import VideoWatch
from app.schemas.common import Message
from app.schemas.video import VideoItem, VideoWatchedIn

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=list[VideoItem])
def list_videos(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course_ids = db.execute(
        select(CourseEnrollment.course_id).where(CourseEnrollment.user_id == user.id)
    ).scalars().all()
    if not course_ids:
        return []

    courses = db.execute(
        select(Course)
        .options(selectinload(Course.subjects).selectinload(Subject.topics).selectinload(Topic.subtopics))
        .where(Course.id.in_(course_ids))
    ).scalars().all()

    watched = set(db.execute(select(VideoWatch.video_url).where(VideoWatch.user_id == user.id)).scalars().all())

    items: list[VideoItem] = []
    for course in courses:
        for subject in course.subjects:
            if not subject.is_published:
                continue
            for topic in subject.topics:
                if not topic.is_published:
                    continue
                if topic.video_url:
                    items.append(VideoItem(
                        url=topic.video_url, title=topic.name, course_id=course.id, course_name=course.name,
                        subject_name=subject.name, topic_name=topic.name, subtopic_name=None,
                        watched=topic.video_url in watched,
                    ))
                for subtopic in topic.subtopics:
                    if not subtopic.is_published:
                        continue
                    for url in subtopic.youtube_videos:
                        items.append(VideoItem(
                            url=url, title=subtopic.name, course_id=course.id, course_name=course.name,
                            subject_name=subject.name, topic_name=topic.name, subtopic_name=subtopic.name,
                            watched=url in watched,
                        ))
    # Unwatched first, so "what's next" surfaces naturally on the dashboard card.
    items.sort(key=lambda v: v.watched)
    return items


@router.post("/watched", response_model=Message)
def mark_video_watched(payload: VideoWatchedIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(
        select(VideoWatch).where(VideoWatch.user_id == user.id, VideoWatch.video_url == payload.video_url)
    ).scalar_one_or_none()
    if existing is None:
        db.add(VideoWatch(user_id=user.id, video_url=payload.video_url))
        db.flush()
    return Message(detail="Marked watched")


@router.delete("/watched", response_model=Message)
def unmark_video_watched(video_url: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(delete(VideoWatch).where(VideoWatch.user_id == user.id, VideoWatch.video_url == video_url))
    db.flush()
    return Message(detail="Unmarked")
