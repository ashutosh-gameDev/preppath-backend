"""
Shapes for "Study Bite" decks - AI-generated interactive flashcard content
pasted into the admin CRM. See the deck-generation prompt (admin-web's
decks/import page) for the full spec this mirrors.

Block types with a concrete JSON example in that prompt (formula, steps,
reorder, match, mcq, memory_hook, exam_tip) get a real typed shape below.
Block types the prompt only names in its "SUPPORTED BLOCK TYPES" list, with
no example of their exact fields (text, heading, highlight, image,
true_false, fill_blank, slider, hotspot, timeline, compare, pyq, counter,
divider, current_affair), get a minimal shape (just `type` + a couple of
obviously-implied optional fields) with `extra="allow"` - deliberately not
guessing a rigid field layout the AI was never actually told to produce.
Tighten these once real generated decks show what field names the model
actually uses.
"""
import uuid
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ORMModel

CARD_TYPES = {
    "concept", "theory", "formula", "shortcut", "interactive",
    "challenge", "pyq", "revision", "current_affair",
}
BACKGROUND_TYPES = {
    "gradient", "grid", "particles", "waves", "molecules", "geometry",
    "stars", "map", "timeline", "paper", "topography", "none",
}


class LenientBlock(BaseModel):
    """Base for block types with no concrete example in the prompt - only
    `type` is required, everything else is accepted as-is."""
    model_config = ConfigDict(extra="allow")


class StrictBlock(BaseModel):
    """Base for block types the prompt gives a concrete JSON example for -
    still tolerant of extra fields, but the fields the example shows are
    real and required."""
    model_config = ConfigDict(extra="allow")


# --- Block types with a concrete spec (typed) --------------------------------

class FormulaVariable(BaseModel):
    model_config = ConfigDict(extra="allow")
    symbol: str
    meaning: str


class FormulaBlock(StrictBlock):
    type: Literal["formula"]
    formula: str
    label: str | None = None
    variables: list[FormulaVariable] = []
    units: str | None = None
    conditions: str | None = None
    shortcut: str | None = None
    application: str | None = None


class StepsBlock(StrictBlock):
    type: Literal["steps"]
    title: str | None = None
    reveal_mode: Literal["tap", "all"] = "tap"
    steps: list[str] = Field(min_length=1)


class ReorderBlock(StrictBlock):
    type: Literal["reorder"]
    question: str
    items: list[str] = Field(min_length=2)
    correct_order: list[str] = Field(min_length=2)


class MatchPair(BaseModel):
    model_config = ConfigDict(extra="allow")
    left: str
    right: str


class MatchBlock(StrictBlock):
    type: Literal["match"]
    question: str
    pairs: list[MatchPair] = Field(min_length=1)


class McqOption(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    text: str


class McqBlock(StrictBlock):
    type: Literal["mcq"]
    question: str
    options: list[McqOption] = Field(min_length=2)
    correct: str
    explanation: str | None = None


class MemoryHookBlock(StrictBlock):
    type: Literal["memory_hook"]
    title: str | None = None
    content: str
    mnemonic: str | None = None


class ExamTipBlock(StrictBlock):
    type: Literal["exam_tip"]
    title: str | None = None
    content: str


# --- Block types with no example in the prompt (lenient) --------------------

class TextBlock(LenientBlock):
    type: Literal["text"]
    content: str | None = None


class HeadingBlock(LenientBlock):
    type: Literal["heading"]
    text: str | None = None


class HighlightBlock(LenientBlock):
    type: Literal["highlight"]
    content: str | None = None


class ImageBlock(LenientBlock):
    type: Literal["image"]
    url: str | None = None
    caption: str | None = None


class RevealBlock(LenientBlock):
    type: Literal["reveal"]
    prompt: str | None = None
    content: str | None = None


class TrueFalseBlock(LenientBlock):
    type: Literal["true_false"]
    question: str | None = None
    correct: bool | None = None
    explanation: str | None = None


class FillBlankBlock(LenientBlock):
    type: Literal["fill_blank"]
    question: str | None = None
    answer: str | None = None
    explanation: str | None = None


class SliderBlock(LenientBlock):
    type: Literal["slider"]
    question: str | None = None


class HotspotBlock(LenientBlock):
    type: Literal["hotspot"]
    image: str | None = None


class TimelineBlock(LenientBlock):
    type: Literal["timeline"]
    title: str | None = None


class CompareBlock(LenientBlock):
    type: Literal["compare"]
    title: str | None = None


class PyqBlock(LenientBlock):
    type: Literal["pyq"]
    label: str | None = None
    content: str | None = None


class CounterBlock(LenientBlock):
    type: Literal["counter"]
    value: float | int | None = None
    label: str | None = None


class DividerBlock(LenientBlock):
    type: Literal["divider"]


class CurrentAffairBlock(LenientBlock):
    type: Literal["current_affair"]
    content: str | None = None


Block = Annotated[
    Union[
        TextBlock, HeadingBlock, FormulaBlock, HighlightBlock, ImageBlock, RevealBlock,
        StepsBlock, McqBlock, TrueFalseBlock, FillBlankBlock, ReorderBlock, MatchBlock,
        SliderBlock, HotspotBlock, TimelineBlock, CompareBlock, MemoryHookBlock,
        ExamTipBlock, PyqBlock, CounterBlock, DividerBlock, CurrentAffairBlock,
    ],
    Field(discriminator="type"),
]


class CardBackground(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    intensity: str | None = None


class DeckCard(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    type: str
    background: CardBackground | None = None
    blocks: list[Block] = Field(min_length=1)


class DeckMeta(BaseModel):
    """The pasted `deck` object - course/subject/topic/subtopic stay as plain
    AI-written strings here; deck_import_service resolves them against a real
    course tree into FK ids before anything is stored."""
    model_config = ConfigDict(extra="allow")
    id: str
    title: str
    description: str | None = None
    course: str | None = None
    subject: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    difficulty: str = "medium"
    theme: str | None = None
    estimated_minutes: int = 0
    tags: list[str] = []
    cards: list[DeckCard] = Field(min_length=1)


class DeckPayload(BaseModel):
    """The exact top-level shape the AI is asked to return."""
    model_config = ConfigDict(extra="allow")
    schema_version: int = 1
    deck: DeckMeta


# --- API request/response shapes --------------------------------------------

class DeckPreviewRequest(ORMModel):
    course_id: uuid.UUID
    raw: dict


class DeckCreateRequest(ORMModel):
    course_id: uuid.UUID
    raw: dict


class DeckOut(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None
    course_id: uuid.UUID
    subject_id: uuid.UUID
    topic_id: uuid.UUID | None
    subtopic_id: uuid.UUID | None
    difficulty: str
    theme: str | None
    estimated_minutes: int
    tags: list[str]
    schema_version: int
    card_count: int
    cards: list[dict]
    status: str
    created_by: uuid.UUID | None


class DeckPreviewSummary(ORMModel):
    """What a still-unsaved, just-validated deck looks like - no id/status/
    created_by yet since preview never writes to the DB."""
    title: str
    description: str | None
    course_id: uuid.UUID
    subject_id: uuid.UUID
    topic_id: uuid.UUID | None
    subtopic_id: uuid.UUID | None
    difficulty: str
    theme: str | None
    estimated_minutes: int
    tags: list[str]
    schema_version: int
    card_count: int
    block_count: int


class DeckPreviewResponse(ORMModel):
    valid: bool
    errors: list[str]
    deck: DeckPreviewSummary | None = None


class DeckUpdate(ORMModel):
    status: str | None = None
