import json
from pathlib import Path

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models import JobProfile, QuestionBank

JOB_PROFILES = [
    {
        "title": "Full Stack Developer",
        "description": (
            "A software development role focused on building and maintaining "
            "both frontend and backend applications."
        ),
        "skills": ["javascript", "typescript", "react", "node.js", "html", "css", "sql", "rest api", "git", "docker"],
    },
    {
        "title": "Data Analyst",
        "description": (
            "A data-focused role involving data cleaning, analysis, "
            "visualization, and extracting actionable insights."
        ),
        "skills": ["python", "sql", "pandas", "numpy", "excel", "power bi", "tableau", "statistics", "data analysis", "data visualization"],
    },
    {
        "title": "ML Engineer",
        "description": (
            "A machine learning role focused on developing, evaluating, "
            "deploying, and maintaining machine learning systems."
        ),
        "skills": ["python", "machine learning", "deep learning", "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "sql"],
    },
    {
        "title": "DevOps Engineer",
        "description": (
            "A role focused on automation, CI/CD, infrastructure, "
            "deployment, monitoring, and reliable software delivery."
        ),
        "skills": ["linux", "bash", "docker", "kubernetes", "ci/cd", "aws", "terraform", "ansible", "jenkins", "prometheus", "grafana"],
    },
    {
        "title": "UI/UX Designer",
        "description": (
            "A design role focused on user experience, interaction design, "
            "visual design, usability, and user-centered product development."
        ),
        "skills": ["figma", "user research", "wireframing", "prototyping", "interaction design", "visual design", "accessibility", "adobe xd"],
    },
]


def seed_job_profiles():
    db = SessionLocal()

    try:
        for profile_data in JOB_PROFILES:
            existing_profile = db.scalar(
                select(JobProfile).where(
                    JobProfile.title == profile_data["title"]
                )
            )

            if existing_profile:
                existing_profile.description = profile_data["description"]
                existing_profile.skills = profile_data["skills"]
                existing_profile.is_active = True
                print(f"Updated job profile: {profile_data['title']}")
                continue

            profile = JobProfile(
                title=profile_data["title"],
                description=profile_data["description"],
                skills=profile_data["skills"],
            )

            db.add(profile)

        db.commit()

        print("Job profile seeding completed.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

def seed_questions():
    

    data_file = Path("/app/data/questions.json")

    if not data_file.exists():
        raise FileNotFoundError(
            f"Question data file not found: {data_file}"
        )

    with data_file.open("r", encoding="utf-8") as file:
        questions = json.load(file)

    db = SessionLocal()

    try:
        inserted = 0
        skipped = 0

        for question_data in questions:
            profile = db.scalar(
                select(JobProfile).where(
                    JobProfile.title == question_data["profile"]
                )
            )

            if profile is None:
                raise ValueError(
                    f"Job profile not found: "
                    f"{question_data['profile']}"
                )

            existing_question = db.scalar(
                select(QuestionBank).where(
                    QuestionBank.job_profile_id == profile.id,
                    QuestionBank.question_text
                    == question_data["question_text"],
                )
            )

            if existing_question:
                skipped += 1
                continue

            question = QuestionBank(
                job_profile_id=profile.id,
                question_text=question_data["question_text"],
                category=question_data.get("category"),
                is_active=question_data.get("is_active", True),
            )

            db.add(question)
            inserted += 1

        db.commit()

        print(f"Questions inserted: {inserted}")
        print(f"Questions skipped: {skipped}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

if __name__ == "__main__":
    seed_job_profiles()
    seed_questions()