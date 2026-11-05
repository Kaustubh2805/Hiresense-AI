from app.services.nlp_quality import assess_transcript_quality


def test_empty_transcript():
    result = assess_transcript_quality("")

    assert result["quality"] == "insufficient"
    assert result["confidence"] == "none"


def test_very_short_transcript():
    result = assess_transcript_quality(
        "I built APIs"
    )

    assert result["word_count"] == 3
    assert result["quality"] == "insufficient"
    assert result["confidence"] == "low"


def test_medium_transcript():
    result = assess_transcript_quality(
        "I worked on several projects during my engineering "
        "degree and learned how to build APIs and database systems."
    )

    assert result["word_count"] >= 15
    assert result["quality"] == "acceptable"
    assert result["confidence"] == "medium"


def test_long_transcript():
    transcript = (
        "During my internship I worked on a backend application "
        "where I designed APIs, connected the application to a "
        "database, implemented authentication, and worked with "
        "the frontend team to integrate the complete system. "
        "This experience improved my understanding of software "
        "development and taught me how to debug problems systematically."
    )

    result = assess_transcript_quality(transcript)

    assert result["word_count"] >= 30
    assert result["quality"] == "good"
    assert result["confidence"] == "high"