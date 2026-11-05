from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.nlp_evaluation import NLPEvaluation


def save_nlp_evaluation(
    db: Session,
    session_question_id: UUID,
    features: dict,
    scores: dict,
    grammar_result: dict | None = None,
) -> NLPEvaluation:
    """
    Create or update the NLP evaluation for one interview answer.

    Deterministic NLP features and scores are stored alongside
    contextual grammar-analysis results.
    """

    evaluation = (
        db.query(NLPEvaluation)
        .filter(
            NLPEvaluation.session_question_id
            == session_question_id
        )
        .first()
    )

    if evaluation is None:
        evaluation = NLPEvaluation(
            session_question_id=session_question_id
        )
        db.add(evaluation)

    overall_score = scores.get("overall_score")

    if overall_score is None:
        raise ValueError(
            "Cannot save NLP evaluation without an overall NLP score."
        )

    # -----------------------------
    # Scores
    # -----------------------------

    evaluation.overall_score = float(overall_score)

    evaluation.vocabulary_score = scores.get(
        "vocabulary_score"
    )

    evaluation.vocabulary_diversity_score = scores.get(
        "vocabulary_diversity_score"
    )

    evaluation.repetition_score = scores.get(
        "repetition_score"
    )

    evaluation.grammar_score = scores.get(
        "grammar_score"
    )

    evaluation.sentence_structure_score = scores.get(
        "sentence_structure_score"
    )

    evaluation.english_consistency_score = scores.get(
        "english_consistency_score"
    )

    evaluation.code_switching_score = scores.get(
        "code_switching_score"
    )

    evaluation.communication_clarity_score = scores.get(
        "communication_clarity_score"
    )

    # -----------------------------
    # Deterministic NLP features
    # -----------------------------

    evaluation.word_count = features.get(
        "word_count"
    )

    evaluation.unique_word_count = features.get(
        "unique_word_count"
    )

    evaluation.vocabulary_diversity = features.get(
        "vocabulary_diversity"
    )

    evaluation.average_word_length = features.get(
        "average_word_length"
    )

    evaluation.sentence_count = features.get(
        "sentence_count"
    )

    evaluation.average_sentence_length = features.get(
        "average_sentence_length"
    )

    evaluation.hindi_word_count = features.get(
        "hindi_word_count"
    )

    evaluation.hindi_word_ratio = features.get(
        "hindi_word_ratio"
    )

    # Store the detected Hindi/Hinglish words as JSON text.
    hindi_words = features.get("hindi_words")

    if hindi_words is not None:
        evaluation.hindi_words = json.dumps(
            hindi_words,
            ensure_ascii=False,
        )
    else:
        evaluation.hindi_words = None

    evaluation.english_word_count = features.get("english_word_count")
    evaluation.english_word_ratio = features.get("english_word_ratio")
    evaluation.english_words = (
        json.dumps(features["english_words"], ensure_ascii=False)
        if features.get("english_words") is not None
        else None
    )
    evaluation.code_switching_count = features.get("code_switching_count")
    evaluation.code_switching_ratio = features.get("code_switching_ratio")
    evaluation.dominant_language = features.get("dominant_language")
    evaluation.language_switching_examples = (
        json.dumps(
            features["language_switching_examples"],
            ensure_ascii=False,
        )
        if features.get("language_switching_examples") is not None
        else None
    )
    evaluation.word_language_identification = (
        json.dumps(
            features["word_language_identification"],
            ensure_ascii=False,
        )
        if features.get("word_language_identification") is not None
        else None
    )

    # -----------------------------
    # Grammar analysis
    # -----------------------------

    if grammar_result is not None:
        evaluation.grammar_score = grammar_result.get(
            "grammar_score"
        )

        evaluation.grammar_error_count = grammar_result.get(
            "error_count",
            0,
        )

        grammar_errors = grammar_result.get(
            "errors",
            [],
        )

        evaluation.grammar_errors = json.dumps(
            grammar_errors,
            ensure_ascii=False,
        )

        evaluation.grammar_summary = grammar_result.get(
            "summary"
        )

    else:
        evaluation.grammar_error_count = 0
        evaluation.grammar_errors = json.dumps(
            [],
            ensure_ascii=False,
        )
        evaluation.grammar_summary = None

    # -----------------------------
    # Transcript quality
    # -----------------------------

    transcript_quality = features.get(
        "transcript_quality"
    )

    if transcript_quality is not None:
        evaluation.quality_level = transcript_quality.get(
            "quality"
        )

        evaluation.confidence_level = transcript_quality.get(
            "confidence"
        )

        evaluation.quality_reason = transcript_quality.get(
            "reason"
        )
    else:
        evaluation.quality_level = None
        evaluation.confidence_level = None
        evaluation.quality_reason = None

        
    # -----------------------------
    # Analysis status
    # -----------------------------

    evaluation.analysis_status = "completed"
    evaluation.error_message = None
    evaluation.analyzed_at = datetime.now(
        timezone.utc
    )

    db.commit()
    db.refresh(evaluation)

    return evaluation