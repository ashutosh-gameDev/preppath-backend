"""
Super-admin-only read model: how many students are enrolled in each course,
broken down by gender and by where they're self-reported to be from (city/
state - the same Profile fields used for Jobs eligibility and CRM ad
targeting). Purely descriptive, no write endpoints here.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_super_admin
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import CourseEnrollment
from app.models.user import Profile, User
from app.schemas.demographics import CourseDemographics, DemographicsOut, GenderCounts, LocationCount

router = APIRouter(prefix="/admin/demographics", tags=["admin:demographics"])

# How many of each location's top entries to return per course - enough for
# a CRM table/chart without shipping a long tail of one-off cities.
_TOP_LOCATIONS = 15


@router.get("", response_model=DemographicsOut)
def get_demographics(admin: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    courses = db.execute(select(Course).order_by(Course.name)).scalars().all()

    out: list[CourseDemographics] = []
    for course in courses:
        total = db.execute(
            select(func.count(CourseEnrollment.id)).where(CourseEnrollment.course_id == course.id)
        ).scalar_one()
        if total == 0:
            continue

        gender_counts = GenderCounts()
        for gender, count in db.execute(
            select(Profile.gender, func.count())
            .join(CourseEnrollment, CourseEnrollment.user_id == Profile.user_id)
            .where(CourseEnrollment.course_id == course.id)
            .group_by(Profile.gender)
        ).all():
            if gender == "male":
                gender_counts.male = count
            elif gender == "female":
                gender_counts.female = count
            elif gender == "other":
                gender_counts.other = count
            else:
                gender_counts.unset += count

        cities = [
            LocationCount(name=city, count=count)
            for city, count in db.execute(
                select(Profile.city, func.count())
                .join(CourseEnrollment, CourseEnrollment.user_id == Profile.user_id)
                .where(CourseEnrollment.course_id == course.id, Profile.city.is_not(None))
                .group_by(Profile.city)
                .order_by(func.count().desc())
                .limit(_TOP_LOCATIONS)
            ).all()
        ]
        states = [
            LocationCount(name=state, count=count)
            for state, count in db.execute(
                select(Profile.state, func.count())
                .join(CourseEnrollment, CourseEnrollment.user_id == Profile.user_id)
                .where(CourseEnrollment.course_id == course.id, Profile.state.is_not(None))
                .group_by(Profile.state)
                .order_by(func.count().desc())
                .limit(_TOP_LOCATIONS)
            ).all()
        ]

        out.append(
            CourseDemographics(
                course_id=course.id,
                course_name=course.name,
                total_enrolled=total,
                gender=gender_counts,
                cities=cities,
                states=states,
            )
        )

    out.sort(key=lambda c: -c.total_enrolled)
    return DemographicsOut(courses=out)
