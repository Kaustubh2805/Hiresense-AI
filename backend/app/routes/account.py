from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.database import get_db
from app.models import JobProfile, Profile, User
from app.services.resume_parser import extract_resume_text, parse_resume
from app.services.storage import delete_resume, upload_resume
from app.services.transcription import WHISPER_CONFIDENCE_FALLBACK_THRESHOLD


logger = logging.getLogger(__name__)
router = APIRouter()

MAX_RESUME_BYTES = 5 * 1024 * 1024
# Skills dominate the deterministic score; experience/title signals are capped bonuses.
SKILL_SCORE_POINTS = 80
TITLE_BONUS_POINTS = 15
EXPERIENCE_BONUS_POINTS = 5
RECOMMENDATION_SECONDARY_RATIO = 0.60
RECOMMENDATION_SECONDARY_MINIMUM = 20
MAX_RECOMMENDED_PROFILES = 2


def _get_profile(db: Session, user_id: UUID) -> Profile:
    profile = db.get(Profile, user_id)
    if profile is None:
        profile = Profile(user_id=user_id, skills=[])
        db.add(profile)
        db.flush()
    return profile


@router.post("/me/resume")
def upload_user_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = file.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    extension = f".{extension}"
    content_type = (file.content_type or "").lower()
    allowed_types = {
        ".pdf": {"application/pdf"},
        ".docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
        },
    }
    if extension not in allowed_types or content_type not in allowed_types[extension]:
        raise HTTPException(status_code=415, detail="Upload a PDF or DOCX resume.")

    data = file.file.read(MAX_RESUME_BYTES + 1)
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="Resume must be 5 MB or smaller.")
    if extension == ".pdf" and not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The file contents do not match a PDF.")
    if extension == ".docx" and not data.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="The file contents do not match a DOCX document.")

    try:
        resume_text = extract_resume_text(data, extension)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=f"Could not read the resume: {exc}") from exc
    if len(resume_text.strip()) < 200:
        raise HTTPException(
            status_code=422,
            detail="This resume looks like an image. Please upload a text-based PDF or DOCX.",
        )

    parsed = parse_resume(resume_text)
    old_resume_url: str | None = None
    object_name = upload_resume(
        user_id=user.id,
        data=data,
        extension=extension,
        content_type=content_type,
    )
    try:
        profile = _get_profile(db, user.id)
        old_resume_url = profile.resume_url
        profile.parsed_resume = parsed
        profile.experience_years = Decimal(str(parsed["total_years_experience"]))
        profile.resume_filename = filename
        profile.resume_updated_at = datetime.now(timezone.utc)
        profile.resume_url = object_name
        profile.skills = parsed["skills"]
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        try:
            delete_resume(object_name)
        except Exception:
            logger.exception("Could not remove failed resume upload object %s", object_name)
        logger.exception("Could not persist parsed resume for user %s", user.id)
        raise HTTPException(status_code=500, detail="Could not save the parsed resume.") from exc

    if old_resume_url and old_resume_url != object_name:
        try:
            delete_resume(old_resume_url)
        except Exception:
            logger.exception("Could not delete replaced resume object %s", old_resume_url)

    return {
        **parsed,
        "filename": filename,
        "updated_at": profile.resume_updated_at.isoformat(),
    }


@router.get("/me/profile")
def get_user_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(Profile, user.id)
    if profile is None:
        return {
            "skills": [],
            "experiences": [],
            "education": [],
            "summary": "",
            "total_years_experience": 0,
            "filename": None,
            "updated_at": None,
        }
    parsed = profile.parsed_resume or {}
    return {
        **parsed,
        "skills": profile.skills or parsed.get("skills", []),
        "total_years_experience": float(profile.experience_years or 0),
        "filename": profile.resume_filename,
        "updated_at": profile.resume_updated_at.isoformat() if profile.resume_updated_at else None,
    }


@router.put("/me/profile/skills")
def update_user_skills(
    payload: dict[str, list[str]],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    skills = payload.get("skills")
    if not isinstance(skills, list) or any(not isinstance(skill, str) for skill in skills):
        raise HTTPException(status_code=422, detail="skills must be a list of strings.")
    normalized = list(dict.fromkeys(skill.strip().lower() for skill in skills if skill.strip()))[:60]
    profile = _get_profile(db, user.id)
    profile.skills = normalized
    parsed = dict(profile.parsed_resume or {})
    parsed["skills"] = normalized
    profile.parsed_resume = parsed
    db.commit()
    return {"skills": normalized}


def _title_keywords(title: str) -> set[str]:
    ignored = {"engineer", "developer", "designer", "analyst", "senior", "junior", "the", "and"}
    return {
        word
        for word in re.findall(r"[a-z0-9+#.]+", title.lower())
        if (len(word) > 2 or word in {"ml", "ui", "ux", "ai"}) and word not in ignored
    }


def score_job_profiles(
    candidate_skills: Iterable[str],
    years: float,
    experiences: Sequence[dict[str, Any]],
    job_profiles: Sequence[Any],
) -> list[dict[str, Any]]:
    """Score roles using distinctiveness-weighted skills and resume evidence."""
    normalized_candidate_skills = {
        skill.strip().casefold()
        for skill in candidate_skills
        if isinstance(skill, str) and skill.strip()
    }
    skill_profile_counts: dict[str, int] = {}
    profile_skills: dict[str, list[str]] = {}

    for job in job_profiles:
        skills = list(dict.fromkeys(
            skill.casefold()
            for skill in (job.skills or [])
            if isinstance(skill, str) and skill.strip()
        ))
        profile_skills[str(job.id)] = skills
        for skill in skills:
            skill_profile_counts[skill] = skill_profile_counts.get(skill, 0) + 1

    title_and_highlights_parts: list[str] = []
    for item in experiences:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "")
        title_and_highlights_parts.append(title if isinstance(title, str) else "")
        highlights = item.get("highlights", [])
        if isinstance(highlights, list):
            title_and_highlights_parts.extend(
                text for text in highlights if isinstance(text, str)
            )
        elif isinstance(highlights, str):
            title_and_highlights_parts.append(highlights)
    title_and_highlights = " ".join(title_and_highlights_parts).casefold()

    scored: list[dict[str, Any]] = []
    for job in job_profiles:
        required = profile_skills[str(job.id)]
        matched = [skill for skill in required if skill in normalized_candidate_skills]
        missing = [skill for skill in required if skill not in normalized_candidate_skills]
        weights = {
            skill: 1 / skill_profile_counts.get(skill, 1)
            for skill in required
        }
        total_weight = sum(weights.values())
        matched_weight = sum(weights[skill] for skill in matched)
        skill_points = (
            matched_weight / total_weight * SKILL_SCORE_POINTS
            if total_weight
            else 0
        )
        keywords = _title_keywords(job.title)
        title_hits = sum(
            1
            for keyword in keywords
            if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", title_and_highlights)
        )
        title_points = min(
            TITLE_BONUS_POINTS,
            TITLE_BONUS_POINTS * title_hits / max(len(keywords), 1),
        )
        experience_points = min(
            EXPERIENCE_BONUS_POINTS,
            max(0, years) / 10 * EXPERIENCE_BONUS_POINTS,
        )
        match_percent = round(
            min(100, skill_points + title_points + experience_points)
        )
        useful_missing = sorted(
            missing,
            key=lambda skill: (skill_profile_counts.get(skill, 1), required.index(skill)),
        )[:3]
        if matched:
            reason = (
                f"You list {', '.join(matched)} — {len(matched)} of {len(required)} "
                f"{job.title} skills."
            )
        else:
            reason = f"You list 0 of {len(required)} {job.title} skills."
        scored.append({
            "id": str(job.id),
            "title": job.title,
            "description": job.description,
            "match_percent": match_percent,
            "matched_skills": matched,
            "missing_skills": useful_missing,
            "recommended": False,
            "recommended_rank": None,
            "badge": None,
            "reason": reason,
        })

    scored.sort(key=lambda item: (-item["match_percent"], item["title"]))
    if scored and scored[0]["match_percent"] > 0:
        scored[0]["recommended"] = True
        scored[0]["recommended_rank"] = 1
        scored[0]["badge"] = "Best match"
        if (
            len(scored) > 1
            and scored[1]["match_percent"] >= RECOMMENDATION_SECONDARY_MINIMUM
            and scored[1]["match_percent"]
            >= scored[0]["match_percent"] * RECOMMENDATION_SECONDARY_RATIO
        ):
            scored[1]["recommended"] = True
            scored[1]["recommended_rank"] = 2
            scored[1]["badge"] = "Also a good fit"
    return scored


@router.get("/me/recommended-job-profiles")
def recommended_job_profiles(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(Profile, user.id)
    if profile is None or not profile.resume_url:
        return {"resume_required": True, "profiles": []}

    parsed = profile.parsed_resume or {}
    candidate_skills = profile.skills or []
    years = float(profile.experience_years or 0)
    experiences = parsed.get("experiences", [])
    if not isinstance(experiences, list):
        experiences = []
    profiles = db.scalars(
        select(JobProfile)
        .where(JobProfile.is_active.is_(True))
        .order_by(JobProfile.title.asc())
    ).all()
    scored = score_job_profiles(candidate_skills, years, experiences, profiles)
    response: dict[str, Any] = {"resume_required": False, "profiles": scored}
    if not scored or scored[0]["match_percent"] == 0:
        response["message"] = (
            "We could not match your resume skills to a role yet — add skills on the Resume page."
        )
    return response


@router.get("/me/interviews")
def get_user_interviews(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text(
            """
            SELECT
                s.id AS session_id,
                jp.title AS job_title,
                s.started_at,
                s.ended_at,
                s.status,
                COALESCE(q.questions_answered, 0) AS questions_answered,
                CASE
                    WHEN s.status = 'completed' AND (
                        ii.session_id IS NULL
                        OR jsonb_typeof(
                            ii.insights_json -> 'language_analysis'
                        ) IS DISTINCT FROM 'object'
                        OR EXISTS (
                            SELECT 1
                            FROM session_questions sq
                            LEFT JOIN nlp_evaluations nlp
                              ON nlp.session_question_id = sq.id
                            WHERE sq.session_id = s.id
                              AND sq.answered_at IS NOT NULL
                              AND cardinality(
                                  regexp_split_to_array(
                                      NULLIF(
                                          trim(
                                              CASE
                                                  WHEN sq.transcript_source = 'whisper'
                                                       AND sq.transcript_whisper IS NOT NULL
                                                  THEN sq.transcript_whisper
                                                  ELSE sq.transcript_text
                                              END
                                          ),
                                          ''
                                      ),
                                      '\\s+'
                                  )
                              ) >= 5
                              AND (
                                  (
                                      sq.transcript_whisper IS NOT NULL
                                      AND COALESCE(sq.transcript_source, 'browser')
                                          != CASE
                                              WHEN sq.transcript_confidence
                                                   < :whisper_confidence_fallback_threshold
                                              THEN 'browser'
                                              ELSE 'whisper'
                                          END
                                  )
                                  OR nlp.session_question_id IS NULL
                                  OR nlp.english_word_count IS NULL
                                  OR nlp.code_switching_ratio IS NULL
                                  OR nlp.language_switching_examples IS NULL
                                  OR nlp.word_language_identification IS NULL
                              )
                        )
                    )
                    THEN 'pending'
                    ELSE ii.analysis_status
                END AS analysis_status,
                ii.insights_json
            FROM interview_sessions s
            JOIN job_profiles jp ON jp.id = s.job_profile_id
            LEFT JOIN (
                SELECT session_id, COUNT(*) FILTER (WHERE answered_at IS NOT NULL) AS questions_answered
                FROM session_questions
                GROUP BY session_id
            ) q ON q.session_id = s.id
            LEFT JOIN interview_insights ii ON ii.session_id = s.id
            WHERE s.user_id = :user_id
            ORDER BY CASE WHEN s.status = 'completed' THEN 0 ELSE 1 END, s.started_at DESC
            """
        ),
        {
            "user_id": user.id,
            "whisper_confidence_fallback_threshold": WHISPER_CONFIDENCE_FALLBACK_THRESHOLD,
        },
    ).mappings()
    result = []
    for row in rows:
        analysis_status = row["analysis_status"]
        insights = row["insights_json"]
        analysis_ready = analysis_status == "completed" and isinstance(insights, dict)
        overall_scores = (insights or {}).get("overall_scores", {}) if analysis_ready else {}
        benchmarks = (insights or {}).get("research_benchmarks", {}) if analysis_ready else {}
        strengths = (benchmarks.get("strengths") or []) if isinstance(benchmarks, dict) else []
        weaknesses = (benchmarks.get("weaknesses") or []) if isinstance(benchmarks, dict) else []
        end = row["ended_at"]
        started_at = row["started_at"]
        duration = int((end - started_at).total_seconds()) if end and started_at else None
        result.append({
            "session_id": str(row["session_id"]),
            "job_title": row["job_title"],
            "started_at": started_at.isoformat() if started_at else None,
            "ended_at": end.isoformat() if end else None,
            "duration_seconds": duration,
            "questions_answered": row["questions_answered"],
            "status": row["status"],
            "analysis_status": analysis_status or ("pending" if row["status"] == "completed" else None),
            "overall_score": overall_scores.get("overall_session") if analysis_ready else None,
            "domain_scores": {
                key: overall_scores.get(key) if analysis_ready else None
                for key in ("answer", "audio", "nlp", "video")
            },
            "top_strength": _benchmark_name(strengths[0]) if strengths else None,
            "top_weakness": _benchmark_name(weaknesses[0]) if weaknesses else None,
            "overall_assessment": (insights or {}).get("overall_assessment") if analysis_ready else None,
        })
    return result


def _benchmark_name(item: Any) -> str | None:
    if isinstance(item, dict):
        return item.get("name") or item.get("domain")
    return item if isinstance(item, str) else None
