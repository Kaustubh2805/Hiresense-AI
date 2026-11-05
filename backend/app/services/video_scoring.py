from __future__ import annotations

from dataclasses import dataclass

from app.services.video_features import VideoFeatureResult


@dataclass
class VideoScoreResult:
    eye_contact: float
    facial_expression: float
    posture: float
    head_movement: float
    gestures: float
    body_language: float
    attentiveness: float
    visual_confidence: float

    overall_score: float


def _clamp_score(score: float) -> float:
    """Keep every factor strictly within the 1–10 range."""

    return round(
        max(1.0, min(10.0, score)),
        1,
    )


def _score_from_percentage(
    percentage: float,
) -> float:
    """
    Convert a 0–100 observable percentage into a 1–10 score.
    """

    return _clamp_score(
        1.0 + (percentage / 100.0) * 9.0
    )


def _score_eye_contact(
    percentage: float,
) -> float:
    """
    Score approximate camera-directed gaze.

    This represents an observable gaze estimate only.
    """

    if percentage >= 75:
        return 10.0

    if percentage >= 65:
        return 9.0

    if percentage >= 55:
        return 8.0

    if percentage >= 45:
        return 7.0

    if percentage >= 35:
        return 6.0

    if percentage >= 25:
        return 5.0

    return 4.0


def _score_facial_expression(
    activity_percentage: float,
) -> float:
    """
    Score observable facial movement.

    Moderate movement receives a higher score than either
    almost no movement or extremely high movement.

    This does not classify emotion.
    """

    if activity_percentage < 1.0:
        return 5.0

    if activity_percentage < 3.0:
        return 7.0

    if activity_percentage < 8.0:
        return 9.0

    if activity_percentage < 15.0:
        return 10.0

    if activity_percentage < 25.0:
        return 8.0

    return 6.0


def _score_posture(
    stability_percentage: float,
    pose_detected_frames: int,
    analyzed_frames: int,
) -> float:
    """
    Score observable posture stability.

    If the posture signal is unavailable, fall back to pose
    visibility so the pipeline remains robust.
    """

    if analyzed_frames <= 0:
        return 1.0

    if stability_percentage > 0:
        return _score_from_percentage(
            stability_percentage
        )

    pose_visibility = (
        pose_detected_frames
        / analyzed_frames
    ) * 100.0

    return _score_from_percentage(
        pose_visibility
    )


def _score_head_movement(
    movement_count: int,
    analyzed_frames: int,
) -> float:
    """
    Score observable head movement frequency.

    This measures movement frequency only.
    It does not infer nervousness, confidence,
    personality, or emotion.
    """

    if analyzed_frames <= 0:
        return 1.0

    movement_rate = (
        movement_count / analyzed_frames
    )

    if movement_rate <= 0.01:
        return 6.0

    if movement_rate <= 0.03:
        return 8.0

    if movement_rate <= 0.08:
        return 10.0

    if movement_rate <= 0.15:
        return 8.0

    if movement_rate <= 0.25:
        return 6.0

    return 4.0


def _score_gestures(
    gesture_count: int,
    analyzed_frames: int,
) -> float:
    """
    Score observable hand/wrist movement.

    A moderate amount of visible movement is treated as stronger
    observable engagement than either no movement or extremely
    frequent movement.
    """

    if analyzed_frames <= 0:
        return 1.0

    gesture_rate = (
        gesture_count / analyzed_frames
    )

    if gesture_rate == 0:
        return 5.0

    if gesture_rate <= 0.03:
        return 7.0

    if gesture_rate <= 0.10:
        return 9.0

    if gesture_rate <= 0.20:
        return 10.0

    if gesture_rate <= 0.35:
        return 8.0

    return 6.0


def score_video_features(
    features: VideoFeatureResult,
) -> VideoScoreResult:
    """
    Convert observable computer-vision signals into explainable
    1–10 visual scores.

    No personality or psychological classifier is used.
    """

    eye_contact = _score_eye_contact(
        features.eye_contact_percentage
    )

    facial_expression = _score_facial_expression(
        features.facial_expression_activity
    )

    posture = _score_posture(
        stability_percentage=(
            features.posture_stability_percentage
        ),
        pose_detected_frames=(
            features.pose_detected_frames
        ),
        analyzed_frames=(
            features.analyzed_frames
        ),
    )

    head_movement = _score_head_movement(
        features.head_movement_count,
        features.analyzed_frames,
    )

    gestures = _score_gestures(
        features.gesture_count,
        features.analyzed_frames,
    )

    body_language = _clamp_score(
        (
            posture
            + head_movement
            + gestures
        ) / 3.0
    )

    attentiveness = _clamp_score(
        (
            eye_contact
            + facial_expression
            + posture
        ) / 3.0
    )

    visual_confidence = _clamp_score(
        (
            attentiveness
            + body_language
            + eye_contact
        ) / 3.0
    )

    overall_score = _clamp_score(
        (
            eye_contact
            + facial_expression
            + posture
            + head_movement
            + gestures
            + body_language
            + attentiveness
            + visual_confidence
        ) / 8.0
    )

    return VideoScoreResult(
        eye_contact=eye_contact,
        facial_expression=facial_expression,
        posture=posture,
        head_movement=head_movement,
        gestures=gestures,
        body_language=body_language,
        attentiveness=attentiveness,
        visual_confidence=visual_confidence,
        overall_score=overall_score,
    )