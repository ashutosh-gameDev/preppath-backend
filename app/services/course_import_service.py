"""Bulk course/subject/topic import - lets an admin create a whole course
structure (course -> subjects -> topics) from one JSON document instead of
the one-at-a-time admin UI, matching how AI-generated syllabus data
naturally comes as one nested document.

Idempotent by name (case-insensitive): re-running the same document, or an
extended one with more subjects/topics added, only creates what's missing -
safe to generate more content over time and re-upload the whole thing rather
than tracking what was already imported.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.course import Course, Subject, Subtopic, Topic
from app.schemas.course import BulkCourseImportRequest, BulkCourseImportResult
from app.services.course_service import unique_slug


def _find_by_name_ci(db: Session, model, name: str, **scope):
    q = select(model).where(func.lower(model.name) == name.strip().lower())
    for column, value in scope.items():
        q = q.where(getattr(model, column) == value)
    return db.execute(q).scalar_one_or_none()


def import_courses(db: Session, payload: BulkCourseImportRequest) -> BulkCourseImportResult:
    courses_created = subjects_created = topics_created = subtopics_created = 0
    courses_skipped: list[str] = []

    for course_in in payload.courses:
        course = _find_by_name_ci(db, Course, course_in.name)
        if course is None:
            course = Course(
                name=course_in.name.strip(),
                description=course_in.description,
                icon=course_in.icon,
                is_published=course_in.is_published,
                slug=unique_slug(db, Course, course_in.name),
            )
            db.add(course)
            db.flush()
            courses_created += 1
        else:
            courses_skipped.append(course_in.name)

        # Whatever gets created under a published course goes live with it -
        # students only see published syllabus items, so a published course
        # whose new subjects/chapters stayed drafts would look like the
        # upload "didn't update". (Publishing a draft course later publishes
        # everything under it, see course_service.publish_course_tree.)
        publish_children = course.is_published

        for subject_in in course_in.subjects:
            subject = _find_by_name_ci(db, Subject, subject_in.name, course_id=course.id)
            if subject is None:
                subject = Subject(
                    name=subject_in.name.strip(),
                    order_index=subject_in.order_index,
                    is_published=subject_in.is_published or publish_children,
                    course_id=course.id,
                    slug=unique_slug(db, Subject, subject_in.name, scope_filter=Subject.course_id == course.id),
                )
                db.add(subject)
                db.flush()
                subjects_created += 1

            for topic_in in subject_in.topics:
                topic = _find_by_name_ci(db, Topic, topic_in.name, subject_id=subject.id)
                if topic is None:
                    topic = Topic(
                        name=topic_in.name.strip(),
                        order_index=topic_in.order_index,
                        is_published=topic_in.is_published or publish_children,
                        video_url=topic_in.video_url,
                        subject_id=subject.id,
                        slug=unique_slug(db, Topic, topic_in.name, scope_filter=Topic.subject_id == subject.id),
                    )
                    db.add(topic)
                    db.flush()
                    topics_created += 1

                for subtopic_in in topic_in.subtopics:
                    subtopic = _find_by_name_ci(db, Subtopic, subtopic_in.name, topic_id=topic.id)
                    if subtopic is None:
                        subtopic = Subtopic(
                            name=subtopic_in.name.strip(),
                            order_index=subtopic_in.order_index,
                            is_published=subtopic_in.is_published or publish_children,
                            youtube_videos=subtopic_in.youtube_videos,
                            topic_id=topic.id,
                            slug=unique_slug(db, Subtopic, subtopic_in.name, scope_filter=Subtopic.topic_id == topic.id),
                        )
                        db.add(subtopic)
                        db.flush()
                        subtopics_created += 1
                    elif subtopic_in.youtube_videos and not subtopic.youtube_videos:
                        # A re-import that adds videos to a subtopic created
                        # earlier without any (e.g. a first pass that only
                        # had names) - fill them in rather than requiring a
                        # one-at-a-time edit for something bulk import itself
                        # could just as well backfill.
                        subtopic.youtube_videos = subtopic_in.youtube_videos

    return BulkCourseImportResult(
        courses_created=courses_created,
        subjects_created=subjects_created,
        topics_created=topics_created,
        subtopics_created=subtopics_created,
        courses_skipped=courses_skipped,
    )
