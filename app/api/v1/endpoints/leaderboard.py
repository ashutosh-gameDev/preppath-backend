import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.statistics import LeaderboardOut
from app.services import leaderboard_service

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/global", response_model=LeaderboardOut)
def get_global_leaderboard(limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return leaderboard_service.global_leaderboard(db, user.id, limit)


@router.get("/weekly", response_model=LeaderboardOut)
def get_weekly_leaderboard(limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return leaderboard_service.weekly_leaderboard(db, user.id, limit)


@router.get("/monthly", response_model=LeaderboardOut)
def get_monthly_leaderboard(limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return leaderboard_service.monthly_leaderboard(db, user.id, limit)


@router.get("/exam/{exam_id}", response_model=LeaderboardOut)
def get_exam_leaderboard(exam_id: uuid.UUID, limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return leaderboard_service.exam_leaderboard(db, exam_id, user.id, limit)


@router.get("/subject/{subject_id}", response_model=LeaderboardOut)
def get_subject_leaderboard(subject_id: uuid.UUID, limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return leaderboard_service.subject_leaderboard(db, subject_id, user.id, limit)
