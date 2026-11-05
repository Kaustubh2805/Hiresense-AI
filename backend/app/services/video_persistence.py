from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.video_features import VideoFeatureResult
from app.services.video_scoring import VideoScoreResult


def save_video_evaluation(
    db: Session,
    session_question_id: uuid.UUID,
    features: VideoFeatureResult,
    scores: VideoScoreResult,
    session_id: uuid.UUID | None = None,
):
    """
    Save one video's visual analysis into the existing
    video_evaluations PostgreSQL table.

    Populates both factor scores and legacy TRD column counterparts.
    """

    if session_id is None:
        session_row = db.execute(
            text("SELECT session_id FROM session_questions WHERE id = :sq_id"),
            {"sq_id": session_question_id},
        ).fetchone()
        if session_row is not None:
            session_id = session_row[0]

    if session_id is None:
        raise ValueError(
            f"Cannot save video evaluation without a valid session_id for question {session_question_id}"
        )

    posture_percentage = (
        (
            features.pose_detected_frames
            / features.analyzed_frames
        ) * 100.0
        if features.analyzed_frames > 0
        else 0.0
    )

    query = text(
        """
        INSERT INTO video_evaluations (
            id,
            session_id,
            session_question_id,
            overall_score,
            camera_engagement_score,
            facial_engagement_score,
            posture_score,
            head_movement_score,
            body_movement_score,
            visual_presence_score,
            composure_score,
            frame_count,
            analyzed_frame_count,
            face_detection_ratio,
            camera_engagement_ratio,
            posture_stability,
            eye_contact,
            facial_expression,
            posture,
            head_movement,
            gestures,
            body_language,
            attentiveness,
            visual_confidence,
            eye_contact_percentage,
            face_visibility_percentage,
            gesture_count,
            head_movement_count,
            analysis_status,
            error_message,
            analyzed_at
        )
        VALUES (
            :id,
            :session_id,
            :session_question_id,
            :overall_score,
            :camera_engagement_score,
            :facial_engagement_score,
            :posture_score,
            :head_movement_score,
            :body_movement_score,
            :visual_presence_score,
            :composure_score,
            :frame_count,
            :analyzed_frame_count,
            :face_detection_ratio,
            :camera_engagement_ratio,
            :posture_stability,
            :eye_contact,
            :facial_expression,
            :posture,
            :head_movement,
            :gestures,
            :body_language,
            :attentiveness,
            :visual_confidence,
            :eye_contact_percentage,
            :face_visibility_percentage,
            :gesture_count,
            :head_movement_count,
            :analysis_status,
            :error_message,
            :analyzed_at
        )
        ON CONFLICT (session_question_id)
        DO UPDATE SET
            session_id = EXCLUDED.session_id,
            overall_score = EXCLUDED.overall_score,
            camera_engagement_score = EXCLUDED.camera_engagement_score,
            facial_engagement_score = EXCLUDED.facial_engagement_score,
            posture_score = EXCLUDED.posture_score,
            head_movement_score = EXCLUDED.head_movement_score,
            body_movement_score = EXCLUDED.body_movement_score,
            visual_presence_score = EXCLUDED.visual_presence_score,
            composure_score = EXCLUDED.composure_score,
            frame_count = EXCLUDED.frame_count,
            analyzed_frame_count = EXCLUDED.analyzed_frame_count,
            face_detection_ratio = EXCLUDED.face_detection_ratio,
            camera_engagement_ratio = EXCLUDED.camera_engagement_ratio,
            posture_stability = EXCLUDED.posture_stability,
            eye_contact = EXCLUDED.eye_contact,
            facial_expression = EXCLUDED.facial_expression,
            posture = EXCLUDED.posture,
            head_movement = EXCLUDED.head_movement,
            gestures = EXCLUDED.gestures,
            body_language = EXCLUDED.body_language,
            attentiveness = EXCLUDED.attentiveness,
            visual_confidence = EXCLUDED.visual_confidence,
            eye_contact_percentage = EXCLUDED.eye_contact_percentage,
            face_visibility_percentage = EXCLUDED.face_visibility_percentage,
            gesture_count = EXCLUDED.gesture_count,
            head_movement_count = EXCLUDED.head_movement_count,
            analysis_status = EXCLUDED.analysis_status,
            error_message = EXCLUDED.error_message,
            analyzed_at = EXCLUDED.analyzed_at
        RETURNING
            id,
            session_id,
            session_question_id,
            overall_score,
            analysis_status
        """
    )

    evaluation_id = uuid.uuid4()

    result = db.execute(
        query,
        {
            "id": evaluation_id,
            "session_id": session_id,
            "session_question_id": session_question_id,
            "overall_score": float(scores.overall_score),
            "camera_engagement_score": float(scores.eye_contact),
            "facial_engagement_score": float(scores.facial_expression),
            "posture_score": float(posture_percentage),
            "head_movement_score": float(scores.head_movement),
            "body_movement_score": float(scores.gestures),
            "visual_presence_score": float(scores.body_language),
            "composure_score": float(scores.attentiveness),
            "frame_count": features.total_frames,
            "analyzed_frame_count": features.analyzed_frames,
            "face_detection_ratio": round(features.face_visibility_percentage / 100.0, 4),
            "camera_engagement_ratio": round(features.eye_contact_percentage / 100.0, 4),
            "posture_stability": round(features.posture_stability_percentage / 100.0, 4),
            "eye_contact": float(scores.eye_contact),
            "facial_expression": float(scores.facial_expression),
            "posture": float(scores.posture),
            "head_movement": float(scores.head_movement),
            "gestures": float(scores.gestures),
            "body_language": float(scores.body_language),
            "attentiveness": float(scores.attentiveness),
            "visual_confidence": float(scores.visual_confidence),
            "eye_contact_percentage": float(features.eye_contact_percentage),
            "face_visibility_percentage": float(features.face_visibility_percentage),
            "gesture_count": features.gesture_count,
            "head_movement_count": features.head_movement_count,
            "analysis_status": "completed",
            "error_message": None,
            "analyzed_at": datetime.now(timezone.utc),
        },
    )

    db.commit()

    row = result.fetchone()

    return row