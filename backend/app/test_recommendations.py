from types import SimpleNamespace
from uuid import uuid4

from app.routes.account import recommended_job_profiles, score_job_profiles
from app.seed.seed_data import JOB_PROFILES
from app.services.skills_taxonomy import SKILLS_TAXONOMY, find_skills


def _job_profiles():
    return [
        SimpleNamespace(
            id=uuid4(),
            title=profile["title"],
            description=profile["description"],
            skills=profile["skills"],
        )
        for profile in JOB_PROFILES
    ]


def _score(skills: list[str]):
    return score_job_profiles(skills, 0, [], _job_profiles())


def test_every_seeded_job_skill_exists_in_taxonomy() -> None:
    missing = {
        skill
        for profile in JOB_PROFILES
        for skill in profile["skills"]
        if skill not in SKILLS_TAXONOMY
    }

    assert not missing


def test_taxonomy_recognizes_resume_variants_without_false_positives() -> None:
    extracted = set(
        find_skills(
            "REST APIs, RESTful services, dashboards, data visualisation, "
            "machine-learning, ML models, wireframes, user experience research, "
            "CI-CD, GitHub Actions, JavaScript, JS, TS, and Node."
        )
    )

    assert {
        "rest api",
        "data visualization",
        "machine learning",
        "wireframing",
        "user research",
        "ci/cd",
        "javascript",
        "typescript",
        "node.js",
    } <= extracted
    assert "java" not in extracted


def test_full_stack_resume_ranks_full_stack_first_and_caps_recommendations() -> None:
    results = _score([
        "javascript",
        "typescript",
        "react",
        "node.js",
        "html",
        "css",
        "sql",
        "rest api",
        "git",
        "docker",
    ])
    recommended = [item for item in results if item["recommended"]]

    assert results[0]["title"] == "Full Stack Developer"
    assert results[0]["recommended_rank"] == 1
    assert results[0]["badge"] == "Best match"
    assert len(recommended) <= 2
    assert all(item["reason"].startswith("You list ") for item in recommended)


def test_data_resume_ranks_data_analyst_first() -> None:
    results = _score(["python", "sql", "pandas", "tableau", "excel"])

    assert results[0]["title"] == "Data Analyst"
    assert results[0]["recommended_rank"] == 1


def test_ml_resume_ranks_ml_engineer_first() -> None:
    results = _score([
        "pytorch",
        "tensorflow",
        "scikit-learn",
        "machine learning",
        "python",
    ])

    assert results[0]["title"] == "ML Engineer"
    assert results[0]["recommended_rank"] == 1
    data_analyst = next(item for item in results if item["title"] == "Data Analyst")
    if data_analyst["recommended_rank"] == 2:
        assert data_analyst["match_percent"] >= 20
        assert data_analyst["match_percent"] >= results[0]["match_percent"] * 0.60


def test_no_matching_skills_produces_no_recommendation() -> None:
    results = _score([])

    assert results
    assert all(not item["recommended"] for item in results)
    assert all(item["recommended_rank"] is None for item in results)
    assert all(item["match_percent"] == 0 for item in results)
    assert all(item["badge"] is None for item in results)


def test_missing_skills_are_limited_to_three_useful_skills() -> None:
    results = _score([])

    assert all(len(item["missing_skills"]) <= 3 for item in results)


def test_endpoint_explains_when_resume_skills_match_no_role() -> None:
    db = SimpleNamespace(
        get=lambda *_args: SimpleNamespace(
            resume_url="resume.pdf",
            parsed_resume={"experiences": []},
            skills=[],
            experience_years=0,
        ),
        scalars=lambda *_args: SimpleNamespace(all=_job_profiles),
    )

    response = recommended_job_profiles(
        user=SimpleNamespace(id=uuid4()),
        db=db,
    )

    assert response["message"] == (
        "We could not match your resume skills to a role yet — add skills on the Resume page."
    )
    assert all(not item["recommended"] for item in response["profiles"])


def test_profiles_without_a_resume_receive_resume_required_response() -> None:
    response = recommended_job_profiles(
        user=SimpleNamespace(id=uuid4()),
        db=SimpleNamespace(get=lambda *_args: None),
    )

    assert response == {"resume_required": True, "profiles": []}
