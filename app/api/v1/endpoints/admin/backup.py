"""Super-admin content backup download - see services/backup_service.py."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_super_admin
from app.db.session import get_db
from app.models.user import User
from app.services import backup_service
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/backup", tags=["admin:backup"])


@router.get("/export")
def export_backup(admin: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    data = backup_service.export_content(db)
    log_action(db, admin.id, "backup_export", "backup", extra={"counts": data["counts"]})
    return data
