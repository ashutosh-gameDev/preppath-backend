import uuid

from app.schemas.common import ORMModel


class CourseNotePageIn(ORMModel):
    subject_id: uuid.UUID
    title: str = "Untitled"
    # The infinite-canvas board itself stays the dark/gray grid - the
    # "milky paper" look lives on each chapter's Frame card instead (see
    # notes-layout.ts/canvas-editor.tsx), not the whole board.
    background: str = "grid-gray"
    canvas_json: str = "{}"
    order_index: int = 0
    is_published: bool = False


class CourseNotePageUpdate(ORMModel):
    subject_id: uuid.UUID | None = None
    title: str | None = None
    background: str | None = None
    canvas_json: str | None = None
    order_index: int | None = None
    is_published: bool | None = None


class CourseNotePageAdminOut(ORMModel):
    """Full row, for the CRM list/editor."""
    id: uuid.UUID
    course_id: uuid.UUID
    subject_id: uuid.UUID
    title: str
    background: str
    canvas_json: str
    order_index: int
    is_published: bool


class CourseNotePageMetaOut(ORMModel):
    """Student-facing list view - excludes canvas_json (can be large), same
    reasoning as the personal Notes Board's NotePageMetaOut."""
    id: uuid.UUID
    subject_id: uuid.UUID
    subject_name: str
    title: str
    background: str
    order_index: int


class CourseNotePageStudentOut(ORMModel):
    """Student-facing single-page read - the full canvas."""
    id: uuid.UUID
    subject_id: uuid.UUID
    title: str
    background: str
    canvas_json: str
