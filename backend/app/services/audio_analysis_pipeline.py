from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.session_question import SessionQuestion
from app.services.audio_extraction import extract_audio
from app.services.audio_features import (
    extract_acoustic_features,
    maximum_filler_measurement,
    score_filler_usage,
)
from app.services.audio_persistence import save_audio_evaluation
from app.services.audio_scoring import score_audio_features
from app.services.storage import download_interview_video
from app.services.transcription import select_transcript


class AudioAnalysisPipelineError(Exception):
    """Raised when audio analysis cannot be completed."""


def analyze_session_question_audio(
    db: Session,
    session_question_id: UUID,
):
    """
    Run the complete audio-analysis pipeline for one answered question.

    Pipeline:
        1. Load SessionQuestion.
        2. Download its recorded video from MinIO.
        3. Extract a mono 16 kHz WAV file.
        4. Extract measurable audio features.
        5. Calculate 1-10 audio communication scores.
        6. Persist the AudioEvaluation.
    """

    session_question = (
        db.query(SessionQuestion)
        .filter(SessionQuestion.id == session_question_id)
        .first()
    )

    if session_question is None:
        raise AudioAnalysisPipelineError(
            f"Session question not found: {session_question_id}"
        )

    if not session_question.video_url:
        raise AudioAnalysisPipelineError(
            f"Session question has no recorded video: {session_question_id}"
        )

    with tempfile.TemporaryDirectory(
        prefix="hiresense_audio_"
    ) as temp_directory:

        temp_directory_path = Path(temp_directory)

        video_path = (
            temp_directory_path
            / f"{session_question_id}.webm"
        )

        audio_path = (
            temp_directory_path
            / f"{session_question_id}.wav"
        )

        try:
            # ---------------------------------------------------------
            # Step 1: Download the recorded interview video.
            # ---------------------------------------------------------
            download_interview_video(
                object_name=session_question.video_url,
                output_path=str(video_path),
            )

            # ---------------------------------------------------------
            # Step 2: Extract mono 16 kHz PCM audio.
            # ---------------------------------------------------------
            extract_audio(
                video_path=video_path,
                output_path=audio_path,
            )

            # ---------------------------------------------------------
            # Step 3: Extract measurable acoustic features.
            #
            # The transcript is passed in because filler-word and
            # words-per-minute analysis use the transcript as well.
            # ---------------------------------------------------------
            transcript_text, _ = select_transcript(
                session_question.transcript_text,
                session_question.transcript_whisper,
                session_question.transcript_source,
                session_question.transcript_confidence,
            )
            features = extract_acoustic_features(
                audio_path=audio_path,
                transcript_text=transcript_text,
            )
            filler_measurement = maximum_filler_measurement(
                session_question.transcript_text,
                session_question.transcript_whisper,
                features["word_count"],
            )
            features.update(filler_measurement)
            features["filler_word_score"] = score_filler_usage(
                features["filler_word_count"],
                features["word_count"],
            )

            # ---------------------------------------------------------
            # Step 4: Convert measurable features into 1-10 scores.
            # ---------------------------------------------------------
            scores = score_audio_features(features)

            # ---------------------------------------------------------
            # Step 5: Persist the completed audio evaluation.
            # ---------------------------------------------------------
            evaluation = save_audio_evaluation(
                db=db,
                session_question_id=session_question_id,
                features=features,
                scores=scores,
            )

            return evaluation

        except Exception as exc:
            raise AudioAnalysisPipelineError(
                "Audio analysis pipeline failed for "
                f"session question {session_question_id}: {exc}"
            ) from exc