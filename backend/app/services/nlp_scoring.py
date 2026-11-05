from __future__ import annotations


def clamp_score(score: float) -> float:
    """
    Keep every score within the required 1-10 range.
    """
    return round(
        max(1.0, min(10.0, score)),
        1,
    )


def score_vocabulary_diversity(
    vocabulary_diversity: float,
) -> float:
    """
    Score lexical diversity.

    Higher diversity generally indicates that the candidate
    is not repeatedly using the same small set of words.
    """
    if vocabulary_diversity >= 0.85:
        return 10.0

    if vocabulary_diversity >= 0.75:
        return 9.0

    if vocabulary_diversity >= 0.65:
        return 8.0

    if vocabulary_diversity >= 0.55:
        return 7.0

    if vocabulary_diversity >= 0.45:
        return 6.0

    if vocabulary_diversity >= 0.35:
        return 5.0

    if vocabulary_diversity >= 0.25:
        return 4.0

    return 3.0


def score_repetition(
    repetition_ratio: float,
) -> float:
    """
    Score unnecessary word repetition.

    Lower repetition is better.
    """
    if repetition_ratio <= 0.05:
        return 10.0

    if repetition_ratio <= 0.10:
        return 9.0

    if repetition_ratio <= 0.15:
        return 8.0

    if repetition_ratio <= 0.20:
        return 7.0

    if repetition_ratio <= 0.30:
        return 6.0

    if repetition_ratio <= 0.40:
        return 5.0

    return 3.5


def score_sentence_structure(
    average_sentence_length: float,
    long_sentence_count: int,
    sentence_count: int,
) -> float:
    """
    Score sentence structure.

    This rewards reasonably sized sentences and penalizes
    excessive numbers of very long sentences.

    It does not claim that short or long sentences are
    inherently grammatically correct.
    """
    if sentence_count == 0:
        return 5.0

    score = 8.0

    if 8 <= average_sentence_length <= 25:
        score += 1.0

    elif 5 <= average_sentence_length < 8:
        score += 0.0

    elif 25 < average_sentence_length <= 35:
        score -= 0.5

    elif average_sentence_length > 35:
        score -= 1.5

    long_sentence_ratio = (
        long_sentence_count / sentence_count
    )

    if long_sentence_ratio == 0:
        score += 1.0

    elif long_sentence_ratio <= 0.25:
        score += 0.0

    elif long_sentence_ratio <= 0.50:
        score -= 1.0

    else:
        score -= 2.0

    return clamp_score(score)


def score_english_consistency(
    hindi_word_ratio: float,
) -> float:
    """
    Score how consistently a transcript remains in English.

    This is a language-pattern metric, not a proxy for intelligence or
    communication quality. A moderate Hinglish mix is still treated as
    understandable and not automatically poor.
    """
    if hindi_word_ratio <= 0.05:
        return 10.0

    if hindi_word_ratio <= 0.10:
        return 9.0

    if hindi_word_ratio <= 0.20:
        return 8.0

    if hindi_word_ratio <= 0.35:
        return 7.0

    if hindi_word_ratio <= 0.50:
        return 6.0

    if hindi_word_ratio <= 0.70:
        return 5.0

    return 4.0


def score_code_switching(
    hindi_word_ratio: float,
    *,
    code_switching_ratio: float | None = None,
    english_word_ratio: float | None = None,
    english_required: bool = False,
) -> float:
    """
    Provide an English-only consistency score only when English is required.

    Otherwise code switching remains a descriptive metric and receives a neutral
    score so Hinglish does not lower communication or technical evaluations.
    """
    if not english_required:
        return 10.0

    if code_switching_ratio is None:
        code_switching_ratio = hindi_word_ratio

    if code_switching_ratio <= 0.02:
        return 10.0
    if code_switching_ratio <= 0.05:
        return 9.5
    if code_switching_ratio <= 0.10:
        return 9.0
    if code_switching_ratio <= 0.20:
        return 8.0
    if code_switching_ratio <= 0.30:
        return 7.0
    if code_switching_ratio <= 0.45:
        return 6.0
    return 5.0


def score_vocabulary(
    vocabulary_diversity: float,
    repetition_ratio: float,
) -> float:
    """
    Combine vocabulary diversity and repetition into
    one vocabulary score.
    """
    diversity_score = score_vocabulary_diversity(
        vocabulary_diversity
    )

    repetition_score = score_repetition(
        repetition_ratio
    )

    return clamp_score(
        (
            diversity_score * 0.70
            + repetition_score * 0.30
        )
    )


def score_grammar(
    sentence_structure_score: float,
) -> float:
    """
    Initial grammar-related score.

    At this stage this is a sentence-structure proxy,
    not a full grammatical correctness engine.

    A dedicated grammar model will be added later.
    """
    return clamp_score(
        sentence_structure_score
    )


def score_communication_clarity(
    vocabulary_score: float,
    sentence_structure_score: float,
    english_consistency_score: float | None = None,
    punctuation_missing: bool = False,
    english_required: bool = False,
) -> float:
    """
    Estimate written/transcript communication clarity.
    """
    if english_required and english_consistency_score is not None:
        if punctuation_missing:
            return clamp_score(
                (
                    vocabulary_score * 0.30
                    + english_consistency_score * 0.35
                )
                / 0.65
            )

        return clamp_score(
            (
                vocabulary_score * 0.30
                + sentence_structure_score * 0.35
                + english_consistency_score * 0.35
            )
        )

    return clamp_score(
        (
            vocabulary_score * 0.45
            + sentence_structure_score * 0.55
        )
    )


def calculate_overall_nlp_score(
    *,
    vocabulary_score: float,
    grammar_score: float,
    english_consistency_score: float,
    code_switching_score: float,
    communication_clarity_score: float,
    punctuation_missing: bool = False,
    english_required: bool = False,
) -> float:
    """
    Calculate the overall NLP communication score.

    Every component contributes to a 1-10 overall score.
    """
    if not english_required:
        if punctuation_missing:
            return clamp_score(
                vocabulary_score * 0.50
                + communication_clarity_score * 0.50
            )

        return clamp_score(
            vocabulary_score * 0.36
            + grammar_score * 0.28
            + communication_clarity_score * 0.36
        )

    if punctuation_missing:
        return clamp_score(
            (
                vocabulary_score * 0.25
                + english_consistency_score * 0.20
                + code_switching_score * 0.10
                + communication_clarity_score * 0.25
            )
            / 0.80
        )

    return clamp_score(
        (
            vocabulary_score * 0.25
            + grammar_score * 0.20
            + english_consistency_score * 0.20
            + code_switching_score * 0.10
            + communication_clarity_score * 0.25
        )
    )


def score_nlp_features(
    features: dict,
) -> dict:
    """
    Convert extracted NLP features into explainable
    1-10 communication scores.
    """
    vocabulary_score = score_vocabulary(
        vocabulary_diversity=features.get(
            "vocabulary_diversity",
            0.0,
        ),
        repetition_ratio=features.get(
            "repetition_ratio",
            0.0,
        ),
    )

    sentence_structure_score = score_sentence_structure(
        average_sentence_length=features.get(
            "average_sentence_length",
            0.0,
        ),
        long_sentence_count=features.get(
            "long_sentence_count",
            0,
        ),
        sentence_count=features.get(
            "sentence_count",
            0,
        ),
    )

    punctuation_missing = bool(features.get("punctuation_missing", False))
    grammar_score = (
        5.0
        if punctuation_missing
        else score_grammar(sentence_structure_score)
    )

    english_required = bool(features.get("english_required", False))
    english_consistency_score = (
        score_english_consistency(
            features.get("hindi_word_ratio", 0.0)
        )
        if english_required
        else 10.0
    )

    code_switching_score = score_code_switching(
        features.get(
            "hindi_word_ratio",
            0.0,
        ),
        code_switching_ratio=features.get(
            "code_switching_ratio",
            features.get(
                "hindi_word_ratio",
                0.0,
            ),
        ),
        english_word_ratio=features.get(
            "english_word_ratio",
            0.0,
        ),
        english_required=english_required,
    )

    communication_clarity_score = (
        score_communication_clarity(
            vocabulary_score=vocabulary_score,
            sentence_structure_score=(
                sentence_structure_score
            ),
            english_consistency_score=(
                english_consistency_score
            ),
            punctuation_missing=punctuation_missing,
            english_required=english_required,
        )
    )

    overall_score = calculate_overall_nlp_score(
        vocabulary_score=vocabulary_score,
        grammar_score=grammar_score,
        english_consistency_score=(
            english_consistency_score
        ),
        code_switching_score=(
            code_switching_score
        ),
        communication_clarity_score=(
            communication_clarity_score
        ),
        punctuation_missing=punctuation_missing,
        english_required=english_required,
    )

    return {
        "vocabulary_score": vocabulary_score,
        "vocabulary_diversity_score": (
            score_vocabulary_diversity(
                features.get(
                    "vocabulary_diversity",
                    0.0,
                )
            )
        ),
        "repetition_score": score_repetition(
            features.get(
                "repetition_ratio",
                0.0,
            )
        ),
        "grammar_score": grammar_score,
        "sentence_structure_score": (
            sentence_structure_score
        ),
        "punctuation_missing": punctuation_missing,
        "english_consistency_score": (
            english_consistency_score
        ),
        "code_switching_score": (
            code_switching_score
        ),
        "communication_clarity_score": (
            communication_clarity_score
        ),
        "overall_score": overall_score,
        "hindi_word_count": features.get(
            "hindi_word_count",
            0,
        ),
        "hindi_word_ratio": features.get(
            "hindi_word_ratio",
            0.0,
        ),
        "hindi_words": features.get(
            "hindi_words",
            {},
        ),
        "english_word_count": features.get(
            "english_word_count",
            0,
        ),
        "english_word_ratio": features.get(
            "english_word_ratio",
            0.0,
        ),
        "code_switching_count": features.get(
            "code_switching_count",
            0,
        ),
        "code_switching_ratio": features.get(
            "code_switching_ratio",
            0.0,
        ),
        "dominant_language": features.get(
            "dominant_language",
            "unknown",
        ),
        "mixed_language": features.get(
            "mixed_language",
            False,
        ),
        "language_switching_examples": features.get(
            "language_switching_examples",
            [],
        ),
    }