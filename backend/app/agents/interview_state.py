from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InterviewState:
    """
    State provided to the interview agent when deciding what to do next.

    The agent uses this state to interpret the current interview context.
    It does not directly modify the state or the database.
    """

    role: str
    difficulty: str

    current_question: str
    current_answer: str

    technical_score: float | None = None
    needs_followup: bool = False

    questions_asked: int = 0
    followups_used: int = 0

    topics_covered: list[str] = field(default_factory=list)

    # Recent interview history.
    # Each item can contain structured information about a previous
    # question, answer, score, and whether a follow-up was required.
    question_history: list[dict[str, Any]] = field(default_factory=list)

    # Technical scores from previous evaluated answers.
    technical_scores: list[float] = field(default_factory=list)

    # Patterns observed across the interview.
    recent_strengths: list[str] = field(default_factory=list)
    recent_weaknesses: list[str] = field(default_factory=list)

    # Maximum number of interview questions allowed.
    # None means no explicit limit has been provided.
    question_budget: int | None = None

    metadata: dict[str, Any] = field(default_factory=dict)