from pydantic import BaseModel, Field


class AnswerEvaluationResult(BaseModel):
    rating: int = Field(
        ge=1,
        le=10,
    )

    correctness: float | None = Field(
        default=None,
        ge=0,
        le=10,
    )

    relevance: float = Field(
        ge=0,
        le=10,
    )

    completeness: float = Field(
        ge=0,
        le=10,
    )

    clarity: float = Field(
        ge=0,
        le=10,
    )

    coherence: float = Field(
        ge=0,
        le=10,
    )

    technical_understanding: float = Field(
        ge=0,
        le=10,
    )

    verdict: str

    feedback: str

    needs_followup: bool = False