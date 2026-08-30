import uuid

from sqlalchemy.orm import Session

from app.models.admin import AdminActivityLog


def log_action(
    db: Session,
    admin_user_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    extra: dict | None = None,
) -> None:
    db.add(
        AdminActivityLog(
            admin_user_id=admin_user_id, action=action, entity_type=entity_type, entity_id=entity_id, extra=extra
        )
    )
    db.flush()
