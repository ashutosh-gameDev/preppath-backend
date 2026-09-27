"""Validates a pasted AI-generated Study Bite deck (see app/schemas/deck.py)
against a real CRM course tree, the same "exact name, resolved to a real FK
id, reject an unmatched name" approach bulk_import_service/taxonomy use for
questions - so a deck can only ever be filed under taxonomy that actually
exists in the CRM."""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from app.models.course import Course
from app.schemas.deck import DeckPayload, McqBlock, MatchBlock, ReorderBlock


@dataclass
class ResolvedDeck:
    title: str
    description: str | None
    course_id: str
    subject_id: str
    topic_id: str | None
    subtopic_id: str | None
    difficulty: str
    theme: str | None
    estimated_minutes: int
    tags: list[str]
    schema_version: int
    cards: list[dict]

    @property
    def card_count(self) -> int:
        return len(self.cards)

    @property
    def block_count(self) -> int:
        return sum(len(c.get("blocks", [])) for c in self.cards)


def _loc_to_str(loc: tuple) -> str:
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out


def _find_by_name(children: list, name: str | None):
    if not name:
        return None
    name = name.strip().casefold()
    for child in children:
        if child.name.strip().casefold() == name:
            return child
    return None


def _normalize_optional(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value or value.casefold() in ("none", "n/a", "na"):
        return None
    return value


def validate_deck(raw: dict, course: Course) -> tuple[ResolvedDeck | None, list[str]]:
    try:
        payload = DeckPayload.model_validate(raw)
    except ValidationError as exc:
        return None, [f"{_loc_to_str(e['loc'])}: {e['msg']}" for e in exc.errors()]

    deck = payload.deck
    errors: list[str] = []

    course_name = _normalize_optional(deck.course)
    if course_name and course_name.casefold() != course.name.strip().casefold():
        errors.append(f"Deck's course '{deck.course}' does not match the selected course '{course.name}'")

    subject_name = _normalize_optional(deck.subject)
    subject = _find_by_name(course.subjects, subject_name) if subject_name else None
    if not subject_name:
        errors.append("Missing subject on deck")
    elif subject is None:
        errors.append(f"Unknown subject '{deck.subject}' for course '{course.name}'")

    topic = None
    topic_name = _normalize_optional(deck.topic)
    if topic_name and subject is not None:
        topic = _find_by_name(subject.topics, topic_name)
        if topic is None:
            errors.append(f"Unknown topic '{deck.topic}' for subject '{subject.name}'")

    subtopic = None
    subtopic_name = _normalize_optional(deck.subtopic)
    if subtopic_name and topic is not None:
        subtopic = _find_by_name(topic.subtopics, subtopic_name)
        if subtopic is None:
            errors.append(f"Unknown subtopic '{deck.subtopic}' for topic '{topic.name}'")

    seen_card_ids: set[str] = set()
    for ci, card in enumerate(deck.cards):
        if card.id in seen_card_ids:
            errors.append(f"deck.cards[{ci}]: duplicate card id '{card.id}'")
        seen_card_ids.add(card.id)

        for bi, block in enumerate(card.blocks):
            where = f"deck.cards[{ci}] ('{card.id}').blocks[{bi}]"
            if isinstance(block, ReorderBlock):
                if sorted(block.items) != sorted(block.correct_order) or len(block.items) != len(block.correct_order):
                    errors.append(f"{where}: reorder correct_order is not a permutation of items")
            elif isinstance(block, MatchBlock):
                lefts = [p.left for p in block.pairs]
                if len(lefts) != len(set(lefts)):
                    errors.append(f"{where}: match has duplicate 'left' values")
            elif isinstance(block, McqBlock):
                if block.correct not in {o.id for o in block.options}:
                    errors.append(f"{where}: mcq correct '{block.correct}' is not one of its option ids")

    if errors:
        return None, errors

    resolved = ResolvedDeck(
        title=deck.title.strip(),
        description=(deck.description or "").strip() or None,
        course_id=str(course.id),
        subject_id=str(subject.id),
        topic_id=str(topic.id) if topic else None,
        subtopic_id=str(subtopic.id) if subtopic else None,
        difficulty=(deck.difficulty or "medium").strip().lower(),
        theme=_normalize_optional(deck.theme),
        estimated_minutes=max(0, deck.estimated_minutes),
        tags=[t.strip() for t in deck.tags if t and t.strip()],
        schema_version=payload.schema_version,
        cards=[c.model_dump(mode="json") for c in deck.cards],
    )
    return resolved, []
