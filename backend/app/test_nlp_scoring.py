from app.services.nlp_features import (
    extract_nlp_features,
)

from app.services.nlp_scoring import (
    score_nlp_features,
)


def test_nlp_scoring():
    transcript = (
        "I worked on a backend project. "
        "Haan, mujhe APIs build karna tha. "
        "Basically I improved the performance."
    )

    features = extract_nlp_features(
        transcript
    )

    scores = score_nlp_features(
        features
    )

    print("\nNLP SCORES")
    print(
        "Vocabulary:",
        scores["vocabulary_score"],
    )
    print(
        "Vocabulary diversity:",
        scores["vocabulary_diversity_score"],
    )
    print(
        "Repetition:",
        scores["repetition_score"],
    )
    print(
        "Grammar:",
        scores["grammar_score"],
    )
    print(
        "Sentence structure:",
        scores["sentence_structure_score"],
    )
    print(
        "English consistency:",
        scores["english_consistency_score"],
    )
    print(
        "Code switching:",
        scores["code_switching_score"],
    )
    print(
        "Communication clarity:",
        scores["communication_clarity_score"],
    )
    print(
        "Hindi count:",
        scores["hindi_word_count"],
    )
    print(
        "Hindi ratio:",
        scores["hindi_word_ratio"],
    )
    print(
        "Overall NLP:",
        scores["overall_score"],
    )

    assert 1 <= scores["vocabulary_score"] <= 10
    assert 1 <= scores["grammar_score"] <= 10
    assert 1 <= scores["english_consistency_score"] <= 10
    assert 1 <= scores["code_switching_score"] <= 10
    assert 1 <= scores["communication_clarity_score"] <= 10
    assert 1 <= scores["overall_score"] <= 10

    assert scores["hindi_word_count"] >= 3

    # "the" must NOT be classified as Hindi.
    assert "the" not in scores["hindi_words"]


def test_hinglish_patterns_do_not_lower_default_communication_scores():
    features = extract_nlp_features(
        "I built a project with an API and tested the result."
    )
    hinglish_features = {
        **features,
        "hindi_word_ratio": 0.6,
        "english_word_ratio": 0.4,
        "code_switching_ratio": 0.5,
    }

    english_scores = score_nlp_features(features)
    hinglish_scores = score_nlp_features(hinglish_features)

    assert hinglish_scores["overall_score"] == english_scores["overall_score"]
    assert (
        hinglish_scores["communication_clarity_score"]
        == english_scores["communication_clarity_score"]
    )
    assert hinglish_scores["english_consistency_score"] == 10.0
    assert hinglish_scores["code_switching_score"] == 10.0