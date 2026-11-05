from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AgentAction(str, Enum):
    """
    Actions the interview agent is allowed to choose.
    """

    ASK_FOLLOWUP = "ask_followup"
    ASK_NEXT_QUESTION = "ask_next_question"
    FINISH = "finish"


@dataclass
class AgentDecision:
    """
    Structured decision returned by the interview agent.

    The application layer is responsible for executing this decision.
    """

    action: AgentAction

    reason: str

    confidence: float | None = None

    followup_instruction: str | None = None