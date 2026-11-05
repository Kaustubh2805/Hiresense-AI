from __future__ import annotations

import json
import uuid
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models import (
    InterviewSession,
    JobProfile,
    SessionQuestion,
    QuestionBank,
)

from app.services.nlp_analysis_pipeline import (
    analyze_session_question_nlp,
)

from app.services.audio_analysis_pipeline import (
    analyze_session_question_audio,
)

from app.services.video_analysis_pipeline import (
    analyze_session_videos,
)

from app.agents.insight_agent import InsightAgent
from app.services.timing import timed
from app.services.transcription_jobs import (
    finalize_session_transcripts,
    wait_for_session_transcriptions,
)


INSIGHT_AGENT = InsightAgent()
logger = logging.getLogger(__name__)


def _parse_json_field(value, default):
    if not value:
        return default
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        logger.warning("Invalid persisted language JSON")
        return default
    return parsed if isinstance(parsed, type(default)) else default


def _analyze_question_in_own_session(
    kind: str,
    session_question_id: UUID,
) -> tuple[bool, float]:
    db = SessionLocal()
    timings: dict[str, float] = {}
    stage = f"{kind}_question_{session_question_id}"
    try:
        with timed(stage, timings):
            if kind == "nlp":
                analyze_session_question_nlp(db=db, session_question_id=session_question_id)
            else:
                analyze_session_question_audio(db=db, session_question_id=session_question_id)
        return True, timings[stage]
    except Exception:
        logger.exception("%s analysis failed for question %s", kind.upper(), session_question_id)
        return False, timings.get(stage, 0.0)
    finally:
        db.close()


def _run_question_group(
    kind: str,
    questions: list[tuple[UUID, bool]],
) -> tuple[dict[str, int], dict[str, float], float]:
    counts = {"attempted": 0, "skipped_existing": 0, "completed": 0, "failed": 0}
    timings: dict[str, float] = {}
    pending: list[UUID] = []
    for question_id, has_existing in questions:
        if has_existing:
            counts["skipped_existing"] += 1
        else:
            counts["attempted"] += 1
            pending.append(question_id)

    started = time.perf_counter()
    max_workers = max(1, min(4, os.cpu_count() or 1))
    if pending:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_analyze_question_in_own_session, kind, question_id): question_id
                for question_id in pending
            }
            for future in as_completed(futures):
                question_id = futures[future]
                succeeded, elapsed = future.result()
                timings[str(question_id)] = elapsed
                counts["completed" if succeeded else "failed"] += 1
    return counts, timings, time.perf_counter() - started


def generate_insights_from_database(
    db: Session,
    session_id: uuid.UUID,
    timings: dict[str, float] | None = None,
) -> dict:
    """
    Read the persisted interview analysis results directly from
    PostgreSQL and generate the final Insight Agent report.

    This intentionally uses raw SQL because the existing
    video_evaluations database schema differs from the current
    SQLAlchemy VideoEvaluation model.
    """

    # -------------------------------------------------------------
    # Load answered session questions
    # -------------------------------------------------------------

    session_questions_result = db.execute(
        text(
            """
            SELECT
                id,
                question_order,
                question_text,
                source,
                source_question_id,
                parent_session_question_id,
                time_taken_seconds,
                time_taken_seconds AS time_take
            FROM session_questions
            WHERE session_id = :session_id
              AND answered_at IS NOT NULL
            ORDER BY question_order
            """
        ),
        {
            "session_id": session_id,
        },
    )
    question_rows = list(session_questions_result.mappings())
    question_ids = [row["id"] for row in question_rows]

    # -------------------------------------------------------------
    # Build question metadata
    #
    # Actual database relationship:
    #
    # session_questions.source_question_id
    #             ↓
    # question_bank.id
    #             ↓
    # question_bank.category
    #
    # Baseline and AI follow-up questions may have no
    # source_question_id, so category can legitimately be NULL.
    # -------------------------------------------------------------
    role = ""

    role_row = db.execute(
        select(JobProfile.title)
        .join(
            QuestionBank,
            QuestionBank.job_profile_id == JobProfile.id,
        )
        .join(
            SessionQuestion,
            SessionQuestion.source_question_id == QuestionBank.id,
        )
        .where(
            SessionQuestion.session_id == session_id,
            SessionQuestion.source_question_id.is_not(None),
        )
        .limit(1)
    ).first()

    if role_row is not None:
        role = role_row[0]


    question_metadata_result = db.execute(
        text(
            """
            SELECT
                sq.id,
                sq.question_order,
                sq.question_text,
                sq.source,
                CASE
                    WHEN sq.transcript_source = 'whisper'
                         AND sq.transcript_whisper IS NOT NULL
                    THEN sq.transcript_whisper
                    ELSE sq.transcript_text
                END AS answer_text,
                qb.category AS category
            FROM session_questions sq
            LEFT JOIN question_bank qb
                ON qb.id = sq.source_question_id
            WHERE sq.session_id = :session_id
              AND sq.answered_at IS NOT NULL
            ORDER BY sq.question_order
            """
        ),
        {
            "session_id": session_id,
        },
    )

    question_metadata = {
        str(row["id"]): {
            "answer_text": row["answer_text"],
            "category": row["category"],
        }
        for row in question_metadata_result.mappings()
    }

    evaluation_maps: dict[str, dict[str, dict]] = {}
    for key, table_name in (
        ("technical", "answer_evaluations"),
        ("nlp", "nlp_evaluations"),
        ("audio", "audio_evaluations"),
        ("video", "video_evaluations"),
    ):
        evaluation_maps[key] = {}
        if not question_ids:
            continue
        rows = db.execute(
            text(
                f"""
                SELECT session_question_id, row_to_json(e) AS evaluation
                FROM (
                    SELECT *
                    FROM {table_name}
                    WHERE session_question_id = ANY(CAST(:ids AS uuid[]))
                ) AS e
                """
            ),
            {"ids": question_ids},
        ).mappings()
        evaluation_maps[key] = {
            str(row["session_question_id"]): row["evaluation"]
            for row in rows
        }

    # -------------------------------------------------------------
    # Build Insight Agent question context
    # -------------------------------------------------------------

    question_results = []

    for question_row in question_rows:

        question_id = question_row["id"]
        question_id_string = str(question_id)

        metadata = question_metadata.get(
            question_id_string,
            {},
        )

        # ---------------------------------------------------------
        # Technical evaluation
        # ---------------------------------------------------------

        technical_result = evaluation_maps["technical"].get(question_id_string)

        # ---------------------------------------------------------
        # NLP evaluation
        # ---------------------------------------------------------

        nlp_result = evaluation_maps["nlp"].get(question_id_string)

        # ---------------------------------------------------------
        # Audio evaluation
        # ---------------------------------------------------------

        audio_result = evaluation_maps["audio"].get(question_id_string)

        # ---------------------------------------------------------
        # Video evaluation
        #
        # IMPORTANT:
        # Read directly from the existing database schema.
        # Do NOT use the SQLAlchemy VideoEvaluation relationship.
        # ---------------------------------------------------------

        video_result = evaluation_maps["video"].get(question_id_string)

        # ---------------------------------------------------------
        # Convert persisted analysis into Insight Agent context
        # ---------------------------------------------------------

        time_take = (
            question_row.get("time_take")
            if question_row.get("time_take") is not None
            else question_row.get("time_taken_seconds")
        )

        question_results.append(
            {
                "question_id": question_id_string,

                "question_order": question_row[
                    "question_order"
                ],

                "question": question_row[
                    "question_text"
                ],

                "source": question_row.get("source"),

                "source_question_id": (
                    str(question_row["source_question_id"])
                    if question_row.get("source_question_id")
                    is not None
                    else None
                ),

                "parent_session_question_id": (
                    str(question_row["parent_session_question_id"])
                    if question_row.get("parent_session_question_id")
                    is not None
                    else None
                ),

                "time_take": time_take,
                "time_taken_seconds": time_take,

                "answer": metadata.get(
                    "answer_text"
                ),

                "answer_text": metadata.get(
                    "answer_text"
                ),
                "answer_word_count": (
                    len(metadata["answer_text"].split())
                    if isinstance(metadata.get("answer_text"), str)
                    and metadata.get("answer_text").strip()
                    else None
                ),

                "category": metadata.get(
                    "category"
                ),

                # -------------------------------------------------
                # Technical
                # -------------------------------------------------

                "technical_score": (
                    technical_result.get("rating")
                    if technical_result
                    else None
                ),

                "technical_evaluation": (
                    technical_result
                    if technical_result
                    else None
                ),

                # -------------------------------------------------
                # NLP
                # -------------------------------------------------

                "nlp_evaluation": (
                    {
                        "overall_score": nlp_result.get(
                            "overall_score"
                        ),

                        "grammar_score": nlp_result.get(
                            "grammar_score"
                        ),

                        "communication_clarity_score": nlp_result.get(
                            "communication_clarity_score"
                        ),

                        "vocabulary_score": nlp_result.get(
                            "vocabulary_score"
                        ),
                        "word_count": nlp_result.get("word_count"),
                        "grammar_error_count": nlp_result.get("grammar_error_count"),
                        "hindi_word_ratio": nlp_result.get("hindi_word_ratio"),
                        "hindi_word_count": nlp_result.get("hindi_word_count"),
                        "hindi_words": _parse_json_field(
                            nlp_result.get("hindi_words"),
                            {},
                        ),
                        "english_word_count": nlp_result.get("english_word_count"),
                        "english_word_ratio": nlp_result.get("english_word_ratio"),
                        "english_words": _parse_json_field(
                            nlp_result.get("english_words"),
                            {},
                        ),
                        "code_switching_count": nlp_result.get("code_switching_count"),
                        "code_switching_ratio": nlp_result.get("code_switching_ratio"),
                        "dominant_language": nlp_result.get("dominant_language"),
                        "language_switching_examples": _parse_json_field(
                            nlp_result.get("language_switching_examples"),
                            [],
                        ),
                        "code_switching_score": nlp_result.get("code_switching_score"),
                        "english_consistency_score": nlp_result.get("english_consistency_score"),
                        "sentence_structure_score": nlp_result.get("sentence_structure_score"),
                    }
                    if nlp_result
                    else None
                ),

                # -------------------------------------------------
                # Audio
                # -------------------------------------------------

                "audio_evaluation": (
                    {
                        "overall_score": audio_result.get(
                            "overall_score"
                        ),

                        "fluency": audio_result.get(
                            "fluency"
                        ),

                        "pace": audio_result.get(
                            "pace"
                        ),

                        "volume": audio_result.get(
                            "volume"
                        ),

                        "filler_word_score": audio_result.get(
                            "filler_word_score"
                        ),

                        "hesitation_score": audio_result.get(
                            "hesitation_score"
                        ),
                        "words_per_minute": audio_result.get("words_per_minute"),
                        "filler_word_count": audio_result.get("filler_word_count"),
                        "pause_count": audio_result.get("pause_count"),
                        "total_pause_seconds": audio_result.get("total_pause_seconds"),
                        "hesitation_count": audio_result.get("hesitation_count"),
                        "pause_management": audio_result.get("pause_management"),
                    }
                    if audio_result
                    else None
                ),

                # -------------------------------------------------
                # Video
                # -------------------------------------------------

                "video_evaluation": (
                    {
                        "overall_score": video_result.get(
                            "overall_score"
                        ),

                        "eye_contact": video_result.get(
                            "eye_contact"
                        ),

                        "facial_expression": video_result.get(
                            "facial_expression"
                        ),

                        "posture": video_result.get(
                            "posture"
                        ),

                        "head_movement": video_result.get(
                            "head_movement"
                        ),

                        "gestures": video_result.get(
                            "gestures"
                        ),

                        "body_language": video_result.get(
                            "body_language"
                        ),

                        "attentiveness": video_result.get(
                            "attentiveness"
                        ),

                        "visual_confidence": video_result.get(
                            "visual_confidence"
                        ),

                        "eye_contact_percentage": video_result.get(
                            "eye_contact_percentage"
                        ),

                        "face_visibility_percentage": video_result.get(
                            "face_visibility_percentage"
                        ),

                        "posture_score": video_result.get(
                            "posture_score"
                        ),

                        "gesture_count": video_result.get(
                            "gesture_count"
                        ),

                        "head_movement_count": video_result.get(
                            "head_movement_count"
                        ),
                    }
                    if video_result
                    else None
                ),
            }
        )

    # -------------------------------------------------------------
    # Generate Insight Agent report
    # -------------------------------------------------------------

    insight_report = INSIGHT_AGENT.generate_insights(
        role=role,
        question_results=question_results,
        timings=timings,
    )

    return insight_report.to_dict()


def run_post_interview_analysis(
    db: Session,
    session_id: uuid.UUID,
) -> dict:
    """
    Run post-interview analysis safely.

    Existing NLP and audio evaluations are reused.
    Missing evaluations are generated.

    Video analysis uses up to five available recorded answers.
    """

    # ---------------------------------------------------------
    # LOAD SESSION
    # ---------------------------------------------------------

    session = db.scalar(
        select(InterviewSession).where(
            InterviewSession.id == session_id
        )
    )

    if session is None:
        raise ValueError(f"Interview session not found: {session_id}")

    job_profile = None

    if session.job_profile_id is not None:
        job_profile = db.scalar(
            select(JobProfile).where(
                JobProfile.id == session.job_profile_id
            )
        )

    role = job_profile.title if job_profile is not None else ""

    if session is None:
        raise ValueError(
            f"Interview session not found: {session_id}"
        )

    if session.status != "completed":
        raise ValueError(
            "Post-interview analysis can only run "
            "for a completed interview."
        )

    wait_for_session_transcriptions(db, session_id)
    db.expire_all()

    # ---------------------------------------------------------
    # LOAD ANSWERED QUESTIONS
    # ---------------------------------------------------------

    answered_questions = db.scalars(
        select(SessionQuestion)
        .where(
            SessionQuestion.session_id == session_id,
            SessionQuestion.answered_at.is_not(None),
        )
        .order_by(
            SessionQuestion.question_order.asc()
        )
    ).all()

    finalize_session_transcripts(db, answered_questions)

    # ---------------------------------------------------------
    # RESULT
    # ---------------------------------------------------------

    result = {
        "session_id": str(session_id),

        "status": "completed",

        "nlp": {
            "attempted": 0,
            "skipped_existing": 0,
            "completed": 0,
            "failed": 0,
        },

        "audio": {
            "attempted": 0,
            "skipped_existing": 0,
            "completed": 0,
            "failed": 0,
        },

        "video": {
            "attempted": True,
            "completed": False,
            "successful_samples": 0,
            "failed_samples": 0,
        },
    }

    timings: dict[str, float] = {}
    question_flags = [
        (
            question.id,
            question.nlp_evaluation is not None
            and question.nlp_evaluation.english_word_count is not None
            and question.nlp_evaluation.code_switching_ratio is not None
            and question.nlp_evaluation.language_switching_examples is not None
            and question.nlp_evaluation.word_language_identification is not None,
            question.audio_evaluation is not None,
        )
        for question in answered_questions
    ]
    nlp_questions = [(question_id, has_nlp) for question_id, has_nlp, _ in question_flags]
    audio_questions = [(question_id, has_audio) for question_id, _, has_audio in question_flags]

    with ThreadPoolExecutor(max_workers=3) as groups:
        nlp_future = groups.submit(_run_question_group, "nlp", nlp_questions)
        audio_future = groups.submit(_run_question_group, "audio", audio_questions)
        video_started = time.perf_counter()
        video_future = groups.submit(analyze_session_videos, db=db, session_id=session_id)

        result["nlp"], nlp_item_timings, timings["nlp"] = nlp_future.result()
        result["audio"], audio_item_timings, timings["audio"] = audio_future.result()
        try:
            video_results = video_future.result()
            result["video"]["successful_samples"] = sum(
                item.analysis_status == "completed" for item in video_results
            )
            result["video"]["failed_samples"] = sum(
                item.analysis_status == "failed" for item in video_results
            )
            result["video"]["completed"] = result["video"]["successful_samples"] > 0
        except Exception:
            logger.exception("Video analysis failed for session %s", session_id)
        timings["video"] = time.perf_counter() - video_started
        timings["nlp_questions"] = nlp_item_timings
        timings["audio_questions"] = audio_item_timings

    try:
        with timed("insight_generation", timings):
            result["insights"] = generate_insights_from_database(
                db=db,
                session_id=session_id,
                timings=timings,
            )
    except Exception as exc:
            logger.exception("Insight generation failed for session %s", session_id)
            result["insights"] = {"status": "failed", "error": str(exc)}
    if isinstance(result["insights"], dict):
            result["insights"]["measurement_notes"] = [
                "Filler counts use the higher detected count from the browser and Whisper transcripts because Whisper may omit hesitation words."
            ]

    # ---------------------------------------------------------
    # FINAL SUMMARY
    # ---------------------------------------------------------

    result["timings"] = timings
    print("[POST-ANALYSIS] timing summary")
    print(f"{'Stage':<32} {'Seconds':>10}")
    print("-" * 44)
    for stage_name, duration in timings.items():
        if isinstance(duration, (float, int)):
            print(f"{stage_name:<32} {duration:>10.3f}")
    print(
        "[POST-ANALYSIS]",
        f"Finished session={session_id} "
        f"NLP completed="
        f"{result['nlp']['completed']} "
        f"NLP skipped="
        f"{result['nlp']['skipped_existing']} "
        f"Audio completed="
        f"{result['audio']['completed']} "
        f"Audio skipped="
        f"{result['audio']['skipped_existing']} "
        f"Video completed="
        f"{result['video']['completed']}",
    )

    return result