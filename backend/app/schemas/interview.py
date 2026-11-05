from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    job_profile_id: UUID


class SessionQuestionResponse(BaseModel):
    id: UUID
    question_order: int
    question_text: str
    source: str


class SessionCreateResponse(BaseModel):
    session_id: UUID
    job_profile_id: UUID
    status: str
    target_question_count: int
    questions: list[SessionQuestionResponse]


class QuestionAnswerRequest(BaseModel):
    transcript_text: str = Field(min_length=1)
    time_taken_seconds: int | None = Field(
        default=None,
        ge=0,
    )


class QuestionAnswerResponse(BaseModel):
    session_id: UUID
    answered_question_id: UUID
    status: str
    next_question: SessionQuestionResponse | None