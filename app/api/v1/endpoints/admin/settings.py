"""Admin-tunable platform settings (XP weights, streak bonuses, analytics
thresholds, leaderboard minimums...). See services/settings_service.py."""
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_super_admin
from app.db.session import get_db
from app.models.user import User
from app.services import settings_service
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/settings", tags=["admin:settings"])


class SettingItem(BaseModel):
    key: str
    value: Any
    is_default: bool
    description: str | None = None


class SettingUpdate(BaseModel):
    value: Any
    description: str | None = None


@router.get("", response_model=list[SettingItem])
def list_settings(admin: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    from app.models.admin import PlatformSetting

    overrides = {row.key: row for row in db.query(PlatformSetting).all()}
    return [
        SettingItem(
            key=key,
            value=overrides[key].value.get("v") if key in overrides else default,
            is_default=key not in overrides,
            description=overrides[key].description if key in overrides else None,
        )
        for key, default in settings_service.DEFAULTS.items()
    ]


@router.put("/{key}", response_model=SettingItem)
def update_setting(key: str, payload: SettingUpdate, admin: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    row = settings_service.set_setting(db, key, payload.value, payload.description)
    return SettingItem(key=key, value=payload.value, is_default=False, description=row.description)
