import uuid

from app.schemas.common import ORMModel


class GenderCounts(ORMModel):
    male: int = 0
    female: int = 0
    other: int = 0
    unset: int = 0


class LocationCount(ORMModel):
    name: str
    count: int


class CourseDemographics(ORMModel):
    course_id: uuid.UUID
    course_name: str
    total_enrolled: int
    gender: GenderCounts
    cities: list[LocationCount]
    states: list[LocationCount]


class DemographicsOut(ORMModel):
    courses: list[CourseDemographics]
