from app.services.grammar_analysis import (
    analyze_grammar,
)


def test_grammar_analysis_with_real_ollama():
    transcript = (
        "I worked on a backend project. "
        "I have built several APIs. "
        "The project helped me improve my programming skills."
    )

    result = analyze_grammar(
        transcript
    )

    print("\nGRAMMAR ANALYSIS")
    print(
        "Grammar score:",
        result["grammar_score"],
    )
    print(
        "Error count:",
        result["error_count"],
    )
    print(
        "Errors:",
        result["errors"],
    )
    print(
        "Summary:",
        result["summary"],
    )

    assert 1 <= result["grammar_score"] <= 10
    assert result["error_count"] == len(
        result["errors"]
    )

    assert isinstance(
        result["summary"],
        str,
    )