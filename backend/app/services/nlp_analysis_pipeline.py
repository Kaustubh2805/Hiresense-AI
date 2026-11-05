from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.session_question import SessionQuestion
from app.services.grammar_analysis import (
    GrammarAnalysisError,
    analyze_grammar,
)
from app.services.nlp_features import extract_nlp_features
from app.services.nlp_persistence import save_nlp_evaluation
from app.services.nlp_scoring import score_nlp_features
from app.services.nlp_quality import assess_transcript_quality
from app.services.transcription import select_transcript

class NLPAnalysisPipelineError(Exception):
    """Raised when NLP analysis cannot be completed."""


def analyze_session_question_nlp(
    db: Session,
    session_question_id: UUID,
):
    """
    Run the complete NLP analysis pipeline for one answered question.

    Pipeline:

        1. Load SessionQuestion.
        2. Read its transcript.
        3. Extract deterministic NLP features.
        4. Calculate deterministic NLP scores.
        5. Run contextual grammar analysis with Ollama.
        6. Persist the final NLP evaluation.
    """

    session_question = (
        db.query(SessionQuestion)
        .filter(
            SessionQuestion.id == session_question_id
        )
        .first()
    )

    if session_question is None:
        raise NLPAnalysisPipelineError(
            f"Session question not found: "
            f"{session_question_id}"
        )

    transcript_text, _ = select_transcript(
        session_question.transcript_text,
        session_question.transcript_whisper,
        session_question.transcript_source,
        session_question.transcript_confidence,
    )

    quality = assess_transcript_quality(
        transcript_text
    )

    

    if quality["quality"] == "insufficient":
        raise NLPAnalysisPipelineError(
            "Transcript is too short for reliable NLP analysis: "
            f"{quality['word_count']} words."
        )   


    if not transcript_text:
        raise NLPAnalysisPipelineError(
            f"Session question has no transcript: "
            f"{session_question_id}"
        )

    try:
        # -----------------------------------------
        # 1. Deterministic NLP feature extraction
        # -----------------------------------------

        features = extract_nlp_features(
            transcript_text
        )
        features["transcript_quality"] = quality
        # -----------------------------------------
        # 2. Deterministic NLP scoring
        # -----------------------------------------

        scores = score_nlp_features(
            features
        )

        # -----------------------------------------
        # 3. Contextual grammar analysis
        # -----------------------------------------

        grammar_result = None

        try:
            grammar_result = analyze_grammar(
                transcript_text,
                deterministic_score=scores.get("grammar_score"),
            )

        except GrammarAnalysisError as exc:
            # Grammar analysis is an enhancement.
            # We keep the deterministic NLP results
            # even if Ollama grammar analysis fails.
            grammar_result = {
                "grammar_score": scores.get(
                    "grammar_score"
                ),
                "error_count": 0,
                "errors": [],
                "summary": (
                    "Grammar analysis was unavailable "
                    "for this answer."
                ),
            }

        # -----------------------------------------
        # 4. Persist NLP evaluation
        # -----------------------------------------

        evaluation = save_nlp_evaluation(
            db=db,
            session_question_id=session_question_id,
            features=features,
            scores=scores,
            grammar_result=grammar_result,
        )

        return evaluation

    except NLPAnalysisPipelineError:
        raise

    except Exception as exc:
        raise NLPAnalysisPipelineError(
            "NLP analysis pipeline failed for "
            f"session question {session_question_id}: "
            f"{exc}"
        ) from exc