from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from concurrent.futures import Future, ThreadPoolExecutor, wait
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.answer_evaluation import AnswerEvaluation
from app.models.session_question import SessionQuestion
from app.services.ai_interview_service import evaluate_answer
from app.services.storage import download_interview_video
from app.services.transcription import (
    is_transcript_usable,
    select_transcript,
    should_reevaluate_answer,
    transcribe_video,
)

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")
_futures: dict[UUID, Future] = {}
_futures_lock = threading.Lock()


def _run_transcription(
    question_id: UUID,
    video_url: str,
    role: str,
    skills: list[str],
    question_text: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix="hiresense_whisper_video_") as directory:
        video_path = Path(directory) / "interview.webm"
        download_interview_video(video_url, str(video_path))
        result = transcribe_video(
            video_path,
            role=role,
            skills=skills,
            question=question_text,
        )

    db = SessionLocal()
    try:
        question = db.scalar(
            select(SessionQuestion).where(SessionQuestion.id == question_id)
        )
        if question is None:
            logger.warning("Whisper result discarded; question %s no longer exists", question_id)
            return
        question.transcript_whisper = result["text"]
        question.transcript_confidence = result["confidence"]
        question.transcript_languages = json.dumps(
            result.get("detected_languages", [])
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def enqueue_transcription(
    question_id: UUID,
    video_url: str,
    *,
    role: str = "",
    skills: list[str] | None = None,
    question_text: str = "",
) -> Future:
    with _futures_lock:
        existing = _futures.get(question_id)
        if existing is not None and not existing.done():
            return existing
        future = _executor.submit(
            _run_transcription,
            question_id,
            video_url,
            role,
            skills or [],
            question_text,
        )
        _futures[question_id] = future
        return future


def wait_for_session_transcriptions(db, session_id: UUID) -> None:
    timeout = max(0.0, float(os.getenv("WHISPER_WAIT_TIMEOUT_SECONDS", "30")))
    session_data = db.execute(
        select(SessionQuestion, ).where(
            SessionQuestion.session_id == session_id,
            SessionQuestion.answered_at.is_not(None),
            SessionQuestion.video_url.is_not(None),
        )
    ).scalars().all()
    if not session_data:
        return

    profile = session_data[0].session.job_profile if session_data[0].session else None
    role = profile.title if profile else ""
    skills = list(profile.skills or []) if profile and profile.skills else []
    futures = []
    for question in session_data:
        if question.transcript_whisper is None:
            futures.append(
                enqueue_transcription(
                    question.id,
                    question.video_url,
                    role=role,
                    skills=skills,
                    question_text=question.question_text,
                )
            )
    if not futures:
        return

    completed, pending = wait(futures, timeout=timeout)
    for future in completed:
        try:
            future.result()
        except Exception:
            logger.exception("Whisper transcription failed before analysis for session %s", session_id)
    if pending:
        logger.warning(
            "Whisper analysis wait timed out for session %s with %s job(s) pending",
            session_id,
            len(pending),
        )


def finalize_session_transcripts(
    db,
    questions: list[SessionQuestion],
) -> None:
    for question in questions:
        browser_text = question.transcript_text or ""
        whisper_text = question.transcript_whisper or ""
        final_text, source = select_transcript(
            browser_text,
            whisper_text,
            confidence=question.transcript_confidence,
        )
        source_changed = question.transcript_source != source
        if source_changed:
            question.nlp_evaluation = None
            question.audio_evaluation = None
        question.transcript_source = source

        if not is_transcript_usable(
            final_text,
            source=source,
            confidence=question.transcript_confidence,
        ):
            question.nlp_evaluation = None
            question.audio_evaluation = None
            question.evaluation = None
            continue

        evaluation = db.scalar(
            select(AnswerEvaluation).where(
                AnswerEvaluation.session_question_id == question.id
            )
        )
        if evaluation is None or (
            source_changed
            and should_reevaluate_answer(browser_text, whisper_text)
        ):
            try:
                result = evaluate_answer(
                    question_text=question.question_text,
                    answer_text=final_text,
                    evaluation_type=question.source,
                )
                if evaluation is None:
                    evaluation = AnswerEvaluation(
                        session_question_id=question.id,
                        evaluation_type=question.source,
                        rating=result.rating,
                        correctness=result.correctness,
                        relevance=result.relevance,
                        completeness=result.completeness,
                        clarity=result.clarity,
                        coherence=result.coherence,
                        technical_understanding=result.technical_understanding,
                        verdict=result.verdict,
                        feedback=result.feedback,
                    )
                    db.add(evaluation)
                else:
                    evaluation.evaluation_type = question.source
                    evaluation.rating = result.rating
                    evaluation.correctness = result.correctness
                    evaluation.relevance = result.relevance
                    evaluation.completeness = result.completeness
                    evaluation.clarity = result.clarity
                    evaluation.coherence = result.coherence
                    evaluation.technical_understanding = result.technical_understanding
                    evaluation.verdict = result.verdict
                    evaluation.feedback = result.feedback
            except Exception:
                logger.exception(
                    "Could not re-evaluate question %s against its selected transcript",
                    question.id,
                )
    db.commit()
