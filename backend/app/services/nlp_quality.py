from __future__ import annotations


def assess_transcript_quality(
    transcript_text: str,
) -> dict:
    """
    Assess whether a transcript contains enough language
    for reliable NLP interview analysis.

    This measures transcript length only. It does not judge
    the candidate's intelligence, ability, or personality.
    """

    text = (transcript_text or "").strip()
    words = text.split()
    word_count = len(words)

    if word_count == 0:
        return {
            "word_count": 0,
            "quality": "insufficient",
            "confidence": "none",
            "reason": "No transcript was provided.",
        }

    if word_count < 5:
        return {
            "word_count": word_count,
            "quality": "insufficient",
            "confidence": "low",
            "reason": (
                "The answer is too short for reliable "
                "language analysis."
            ),
        }

    if word_count < 15:
        return {
            "word_count": word_count,
            "quality": "limited",
            "confidence": "low",
            "reason": (
                "The answer is short, so vocabulary, "
                "grammar, and sentence-level metrics "
                "may be less reliable."
            ),
        }

    if word_count < 30:
        return {
            "word_count": word_count,
            "quality": "acceptable",
            "confidence": "medium",
            "reason": (
                "The transcript contains enough language "
                "for basic NLP analysis, but some metrics "
                "may still be sensitive to answer length."
            ),
        }

    return {
        "word_count": word_count,
        "quality": "good",
        "confidence": "high",
        "reason": (
            "The transcript contains sufficient language "
            "for the selected NLP metrics."
        ),
    }