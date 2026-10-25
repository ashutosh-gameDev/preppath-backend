import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import Message
from app.schemas.notification import DeviceTokenIn, NotificationOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def get_notifications(limit: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return notification_service.get_feed(db, user.id, limit)


@router.post("/register-device", response_model=Message)
def register_device(payload: DeviceTokenIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Called by the Android app once it has a real FCM registration token
    (see student-web's lib/push-notifications.ts) - safe to call on every
    app launch, re-registering the same token is a cheap no-op update."""
    notification_service.register_device_token(db, user.id, payload.token, payload.platform)
    return Message(detail="Registered")


@router.post("/{notification_id}/read", response_model=Message)
def mark_read(notification_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.flush()
    return Message(detail="Marked as read")
