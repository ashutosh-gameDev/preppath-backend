"""Deterministic student analytics: performance overview, progress graphs,
subject/topic breakdown, strengths/weaknesses, improvement, recommendations."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.statistics import (
    ImprovementItem,
    PerformanceOverview,
    ProgressPoint,
    RecommendationOut,
    StrengthWeaknessItem,
    SubjectPerformance,
)
from app.services import analytics, leaderboard_service, recommendation
from app.services.settings_service import get_setting

router = APIRouter(prefix="/statistics", tags=["statistics"])

RANGE_TO_DAYS = {"7d": 7, "30d": 30, "3m": 90, "all": 3650}


@router.get("/overview", response_model=PerformanceOverview)
def get_overview(period_days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = analytics.performance_overview(db, user.id, period_days)
    min_attempts = int(get_setting(db, "leaderboard.min_attempts") or 10)
    data["current_rank"] = leaderboard_service.global_rank(db, user.id, min_attempts)
    return data


@router.get("/progress", response_model=list[ProgressPoint])
def get_progress(range: str = Query("30d", pattern="^(7d|30d|3m|all)$"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    days = RANGE_TO_DAYS.get(range, 30)
    return analytics.progress_series(db, user.id, days)


@router.get("/subjects", response_model=list[SubjectPerformance])
def get_subject_performance(course_id: uuid.UUID | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analytics.subject_performance(db, user.id, course_id)


@router.get("/strengths-weaknesses")
def get_strengths_weaknesses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    strong, weak = analytics.strong_weak_areas(db, user.id)
    return {
        "strong": [StrengthWeaknessItem(**s) for s in strong],
        "weak": [StrengthWeaknessItem(**w) for w in weak],
    }


@router.get("/improvement", response_model=list[ImprovementItem])
def get_improvement(period_days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analytics.improvement_analysis(db, user.id, period_days)


@router.get("/recommendations", response_model=list[RecommendationOut])
def get_recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return recommendation.build_recommendations(db, user.id)
