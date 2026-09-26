from datetime import datetime

from app.schemas.question import QuestionReviewOut


class MistakeItemOut(QuestionReviewOut):
    """A question whose most recent attempt by this student was wrong - what
    they picked and when, alongside the full question + answer key (same
    shape as a test review) so it can be read without another request."""
    selected_option: str | None = None
    attempted_at: datetime


class BookmarkedQuestionOut(QuestionReviewOut):
    """A saved question, with when it was bookmarked."""
    bookmarked_at: datetime
