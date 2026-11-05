from app.services.nlp_features import extract_nlp_features
from app.services.nlp_scoring import score_nlp_features


def test_long_unpunctuated_transcript_excludes_sentence_structure_weight():
    text = (
        "I designed a service with clear interfaces and tested every endpoint before "
        "deploying it to production while monitoring latency, reliability, and user "
        "feedback across several releases"
    )
    features = extract_nlp_features(text)
    scores = score_nlp_features(features)

    assert features["word_count"] > 25
    assert features["punctuation_missing"] is True
    expected = (
        scores["vocabulary_score"] * 0.50
        + scores["communication_clarity_score"] * 0.50
    )
    assert scores["overall_score"] == round(max(1.0, min(10.0, expected)), 1)


def test_short_transcript_does_not_get_punctuation_flag():
    assert not extract_nlp_features("I built an API")["punctuation_missing"]
