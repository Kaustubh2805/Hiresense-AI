from app.services import resume_parser
from app.services.resume_parser import ResumeParse
from app.services.skills_taxonomy import find_skills


def test_deterministic_skills_use_word_boundaries() -> None:
    assert find_skills("I use JavaScript and PostgreSQL in production.") == [
        "javascript",
        "postgresql",
    ]
    assert "java" not in find_skills("JavaScript")


def test_llm_skills_are_canonicalized_and_unknown_skills_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        resume_parser,
        "_parse_with_ollama",
        lambda _text: ResumeParse(skills=["JS", "invented platform"]),
    )

    parsed = resume_parser.parse_resume("A sufficiently detailed resume text.")

    assert parsed["parse_quality"] == "full"
    assert parsed["skills"] == ["javascript"]


def test_parser_falls_back_to_basic_when_ollama_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(resume_parser, "_parse_with_ollama", lambda _text: None)
    text = (
        "Summary\nExperienced developer with many years of software engineering work.\n"
        "Experience\nSenior Engineer at Example 2018 - 2023\nBuilt JavaScript applications.\n"
        "Education\nBachelor of Science in Computer Science 2014 - 2018\n"
    )

    parsed = resume_parser.parse_resume(text)

    assert parsed["parse_quality"] == "basic"
    assert parsed["total_years_experience"] == 9
    assert "javascript" in parsed["skills"]
