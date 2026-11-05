from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audio_evaluation import AudioEvaluation


def save_audio_evaluation(
    db: Session,
    session_question_id: UUID,
    features: dict,
    scores: dict,
) -> AudioEvaluation:
    """
    Save the calculated audio analysis for one session question.

    If an evaluation already exists for the session question,
    update it instead of creating a duplicate.

    The function stores:
    - calculated 1-10 audio scores
    - measurable audio features
    - analysis status
    - analysis timestamp
    """

    evaluation = (
        db.query(AudioEvaluation)
        .filter(
            AudioEvaluation.session_question_id
            == session_question_id
        )
        .first()
    )

    if evaluation is None:
        evaluation = AudioEvaluation(
            session_question_id=session_question_id,
        )

        db.add(evaluation)

    overall_score = scores.get(
        "overall_score"
    )

    if overall_score is None:
        raise ValueError(
            "Cannot save audio evaluation without "
            "an overall audio score."
        )

    # ---------------------------------------------------------
    # Calculated scores
    # ---------------------------------------------------------

    evaluation.overall_score = int(
        round(overall_score)
    )

    evaluation.pace = scores.get(
        "pace"
    )

    evaluation.fluency = scores.get(
        "fluency"
    )

    evaluation.volume = scores.get(
        "vocal_energy"
    )

    # These factors are intentionally left empty until
    # we implement reliable measurements for them.
    evaluation.speaking_clarity = None
    evaluation.articulation = None
    evaluation.vocal_confidence = None

    
    # ---------------------------------------------------------
    # Raw measurable features
    # ---------------------------------------------------------

    evaluation.words_per_minute = features.get(
        "words_per_minute"
    )

    evaluation.pause_count = features.get(
        "pause_count"
    )

    evaluation.total_pause_seconds = features.get(
        "total_pause_seconds"
    )

    evaluation.filler_word_count = features.get(
        "filler_word_count"
    )

    evaluation.filler_word_score = scores.get(
        "filler_word_score"
    )
    evaluation.hesitation_count = features.get("hesitation_count")

    evaluation.hesitation_score = scores.get("hesitation_score")
    # ---------------------------------------------------------
    # Analysis state
    # ---------------------------------------------------------

    evaluation.analysis_status = "completed"

    evaluation.error_message = None

    evaluation.analyzed_at = datetime.now(
        timezone.utc
    )

    db.commit()

    db.refresh(
        evaluation
    )

    return evaluation