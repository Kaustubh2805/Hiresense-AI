from uuid import UUID

from app.db.database import SessionLocal
from app.models.audio_evaluation import AudioEvaluation
from app.services.audio_analysis_pipeline import (
    analyze_session_question_audio,
)


SESSION_QUESTION_ID = UUID(
    "e534c4bf-ea30-484d-94fc-24673d4fc5f3"
)


def test_real_audio_analysis_pipeline():
    db = SessionLocal()

    try:
        evaluation = analyze_session_question_audio(
            db=db,
            session_question_id=SESSION_QUESTION_ID,
        )

        print("\n")
        print("=" * 70)
        print("REAL AUDIO ANALYSIS PIPELINE")
        print("=" * 70)

        print(f"Evaluation ID:       {evaluation.id}")
        print(f"Overall score:       {evaluation.overall_score}/10")
        print(f"Pace:                {evaluation.pace}/10")
        print(f"Fluency:             {evaluation.fluency}/10")
        print(f"Volume:              {evaluation.volume}/10")
        print(
            f"Filler word score:   "
            f"{evaluation.filler_word_score}/10"
        )
        print(
            f"Hesitation score:    "
            f"{evaluation.hesitation_score}/10"
        )

        print("\nRAW AUDIO FEATURES")
        print("-" * 70)
        print(
            f"Words per minute:    "
            f"{evaluation.words_per_minute}"
        )
        print(
            f"Filler word count:   "
            f"{evaluation.filler_word_count}"
        )
        print(
            f"Hesitation count:    "
            f"{evaluation.hesitation_count}"
        )
        print(
            f"Pause count:         "
            f"{evaluation.pause_count}"
        )
        print(
            f"Total pause seconds: "
            f"{evaluation.total_pause_seconds}"
        )

        print("\nSTATUS")
        print("-" * 70)
        print(
            f"Analysis status:     "
            f"{evaluation.analysis_status}"
        )

        print("=" * 70)

        assert isinstance(evaluation, AudioEvaluation)
        assert evaluation.overall_score >= 1
        assert evaluation.overall_score <= 10
        assert evaluation.analysis_status == "completed"

        assert evaluation.pace is not None
        assert evaluation.fluency is not None
        assert evaluation.volume is not None

        assert evaluation.words_per_minute is not None
        assert evaluation.pause_count is not None
        assert evaluation.total_pause_seconds is not None

        assert evaluation.hesitation_score is not None
        assert evaluation.filler_word_score is not None

        print("REAL AUDIO PIPELINE SUCCESS")

    finally:
        db.close()