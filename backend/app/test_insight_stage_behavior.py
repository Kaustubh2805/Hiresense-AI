from app.agents.insight_agent import InsightAgent


def _question(
    question_id: str,
    source: str,
    *,
    parent_id: str | None = None,
    score: float | None = 8.0,
) -> dict:
    return {
        "question_id": question_id,
        "source": source,
        "parent_session_question_id": parent_id,
        "question_text": f"Question {question_id}",
        "answer_text": f"Answer for {question_id}",
        "technical_evaluation": {"rating": score} if score is not None else None,
        "audio_evaluation": None,
        "video_evaluation": None,
    }


def _stages(questions: list[dict]) -> list[dict]:
    return InsightAgent()._build_stage_behavior_analysis(
        question_results=questions,
        question_evaluations=[],
        factor_values={},
    )


def test_followup_stage_uses_real_middle_followup() -> None:
    questions = [
        _question("baseline", "baseline"),
        _question("bank-1", "bank"),
        _question("followup", "ai_followup", parent_id="bank-1"),
        _question("bank-2", "bank"),
        _question("bank-3", "bank"),
    ]

    followup = _stages(questions)[2]

    assert followup["question_id"] == "followup"
    assert followup["question_number"] == 3
    assert followup["question_text"] == "Question followup"
    assert followup["answer_excerpt"] == "Answer for followup"


def test_no_followup_is_unavailable_not_arbitrary_q2() -> None:
    stages = _stages([
        _question("baseline", "baseline"),
        _question("bank-1", "bank"),
        _question("bank-2", "bank"),
    ])
    followup = stages[2]

    assert followup["available"] is False
    assert followup["question_number"] is None
    assert followup["question_id"] is None
    assert followup["short_reason"] == "No follow-up question was asked in this interview."


def test_first_followup_is_used_and_counted() -> None:
    stages = _stages([
        _question("bank-1", "bank"),
        _question("followup-1", "ai_followup", parent_id="bank-1"),
        _question("followup-2", "ai_followup", parent_id="bank-1"),
    ])
    followup = stages[2]

    assert followup["question_id"] == "followup-1"
    assert followup["followup_count"] == 2


def test_followup_as_last_question_still_builds_both_stages() -> None:
    stages = _stages([
        _question("bank-1", "bank"),
        _question("followup", "ai_followup", parent_id="bank-1"),
    ])

    assert stages[2]["question_id"] == "followup"
    assert stages[3]["question_id"] == "followup"
    assert stages[2]["question_number"] == stages[3]["question_number"] == 2


def test_missing_technical_evaluation_does_not_raise() -> None:
    stages = _stages([
        _question("baseline", "baseline", score=None),
        _question("bank", "bank"),
        _question("followup", "ai_followup", parent_id="bank"),
    ])

    assert stages[0]["score"] is None
    assert stages[0]["presence_status"] == "Evaluation unavailable"
    assert stages[0]["short_reason"].startswith("Answer evaluation unavailable")
