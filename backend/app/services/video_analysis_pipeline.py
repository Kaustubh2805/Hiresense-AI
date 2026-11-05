from __future__ import annotations

import os
import tempfile
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.services.storage import download_interview_video
from app.services.video_features import analyze_video_features
from app.services.video_persistence import save_video_evaluation
from app.services.video_sample_selection import (
    VideoSample,
    select_video_samples,
)
from app.services.video_scoring import score_video_features
from app.services.timing import timed

logger = logging.getLogger(__name__)


@dataclass
class VideoAnalysisResult:
    session_question_id: UUID
    question_order: int
    analysis_status: str
    overall_score: float | None = None
    error_message: str | None = None
    timings: dict[str, float] | None = None


class VideoAnalysisPipelineError(Exception):
    """Raised when the session video analysis pipeline cannot run."""


def analyze_session_videos(
    db: Session,
    session_id: UUID,
) -> list[VideoAnalysisResult]:
    """
    Analyze up to five selected videos from a completed interview.

    The selector prioritizes the longest and a moderate-duration answer,
    then adds answers spread through the interview.

    Each video is:
    - downloaded from MinIO
    - decoded with FFmpeg
    - analyzed with MediaPipe
    - converted into 1–10 visual scores
    - persisted into video_evaluations

    A failure for one video does not stop analysis of the other video.
    """

    samples = select_video_samples(
        db=db,
        session_id=session_id,
    )

    if not samples:
        raise VideoAnalysisPipelineError(
            "No completed interview answers have a stored video and valid duration."
        )

    if len(samples) == 1:
        return [_analyze_single_video(db=db, sample=samples[0])]

    results: list[VideoAnalysisResult] = []
    with ProcessPoolExecutor(
        max_workers=min(5, len(samples), max(1, os.cpu_count() or 1)),
        mp_context=multiprocessing.get_context("spawn"),
    ) as executor:
        futures = {executor.submit(_analyze_video_sample, sample): sample for sample in samples}
        for future in as_completed(futures):
            sample = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(
                    VideoAnalysisResult(
                        session_question_id=sample.session_question_id,
                        question_order=sample.question_order,
                        analysis_status="failed",
                        error_message=str(exc),
                    )
                )
    return sorted(results, key=lambda result: result.question_order)


def _analyze_video_sample(sample: VideoSample) -> VideoAnalysisResult:
    db = SessionLocal()
    try:
        return _analyze_single_video(db=db, sample=sample)
    finally:
        db.close()


def _analyze_single_video(
    db: Session,
    sample: VideoSample,
) -> VideoAnalysisResult:
    temp_path: str | None = None
    timings: dict[str, float] = {}

    try:
        extension = os.path.splitext(
            sample.video_url
        )[1] or ".webm"

        with tempfile.NamedTemporaryFile(
            prefix=(
                f"video_analysis_"
                f"{sample.session_question_id}_"
            ),
            suffix=extension,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name

        print(
            f"Downloading video for question "
            f"{sample.question_order}..."
        )

        with timed(f"video_download_{sample.session_question_id}", timings):
            download_interview_video(
                object_name=sample.video_url,
                output_path=temp_path,
            )

        print(
            f"Running visual analysis for question "
            f"{sample.question_order}..."
        )

        with timed(f"video_features_{sample.session_question_id}", timings):
            features = analyze_video_features(video_path=temp_path)
        timings.update(features.timings)

        scores = score_video_features(
            features,
        )

        save_video_evaluation(
            db=db,
            session_question_id=sample.session_question_id,
            features=features,
            scores=scores,
            session_id=sample.session_id,
        )

        print(
            f"Completed video analysis for question "
            f"{sample.question_order}: "
            f"{scores.overall_score}/10"
        )

        return VideoAnalysisResult(
            session_question_id=sample.session_question_id,
            question_order=sample.question_order,
            analysis_status="completed",
            overall_score=scores.overall_score,
            timings=timings,
        )

    except Exception as exc:
        print(
            f"Video analysis failed for question "
            f"{sample.question_order}: {exc}"
        )

        return VideoAnalysisResult(
            session_question_id=sample.session_question_id,
            question_order=sample.question_order,
            analysis_status="failed",
            error_message=str(exc),
            timings=timings,
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                logger.warning("Could not remove temporary video file %s", temp_path, exc_info=True)