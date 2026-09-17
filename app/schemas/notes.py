import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class NoteCategoryIn(ORMModel):
    id: uuid.UUID | None = None
    name: str
    color: str = "#6366f1"


class NoteCategoryOut(ORMModel):
    id: uuid.UUID
    name: str
    color: str
    updated_at: datetime


class NotePageMetaOut(ORMModel):
    """List-view shape - deliberately excludes `canvas_json` (can be large)
    so the page grid loads cheaply; fetch NotePageOut for one page to edit."""
    id: uuid.UUID
    category_id: uuid.UUID | None
    title: str
    background: str
    updated_at: datetime


class NotePageOut(NotePageMetaOut):
    canvas_json: str


class NotePageIn(ORMModel):
    """Upsert payload for PUT /notes/pages/{id} - `id` in the URL is
    client-generated (see models/notes.py NotePage docstring)."""
    category_id: uuid.UUID | None = None
    title: str = "Untitled"
    background: str = "grid-dark"
    canvas_json: str = "{}"
