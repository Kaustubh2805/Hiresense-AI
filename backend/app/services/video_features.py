from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import json
import logging
from pathlib import Path
import subprocess
import time

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class VideoFeatureResult:
    total_frames: int
    analyzed_frames: int
    face_detected_frames: int
    pose_detected_frames: int

    # Percentage of analyzed frames where a face was visible.
    face_visibility_percentage: float

    # Percentage of face-detected frames where the gaze estimate
    # indicated that the candidate was looking approximately toward
    # the camera.
    eye_contact_percentage: float

    # Observable facial movement activity.
    facial_expression_activity: float

    # Observable posture stability.
    posture_stability_percentage: float

    head_movement_count: int
    gesture_count: int
    timings: dict[str, float] = field(default_factory=dict)


class VideoFeatureExtractionError(Exception):
    pass


logger = logging.getLogger(__name__)
LEGACY_SAMPLE_INTERVAL = 5
MAX_ANALYZED_VIDEO_FRAMES = 180
MAX_ANALYSIS_FPS = 2.0
ANALYSIS_FRAME_HEIGHT = 360


def _parse_frame_rate(value: str | None) -> float:
    try:
        rate = float(Fraction(value or ""))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0
    return rate if rate > 0 else 0.0


def _get_output_fps(source_fps: float, sample_every_n_frames: int = 1) -> float:
    if source_fps <= 0 or sample_every_n_frames <= 0:
        raise VideoFeatureExtractionError("Frame rate and sample interval must be positive.")
    return min(
        source_fps / (LEGACY_SAMPLE_INTERVAL * sample_every_n_frames),
        MAX_ANALYSIS_FPS,
    )


def _get_scaled_dimensions(width: int, height: int) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        raise VideoFeatureExtractionError("Video dimensions must be positive.")
    scaled_width = max(2, round(width * ANALYSIS_FRAME_HEIGHT / height))
    if scaled_width % 2:
        scaled_width += 1
    return scaled_width, ANALYSIS_FRAME_HEIGHT


def _get_video_metadata(video_path: Path) -> tuple[int, int, int, float]:
    """
    Read video dimensions and frame count using FFprobe.

    Returns:
        width, height, frame_count, source_fps
    """

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,nb_frames,avg_frame_rate,r_frame_rate,duration:"
        "format=duration",
        "-of",
        "json",
        str(video_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise VideoFeatureExtractionError(
            f"Could not inspect video with ffprobe: {video_path}"
        ) from exc

    output = result.stdout.strip()

    if not output:
        raise VideoFeatureExtractionError(
            "FFprobe returned no video metadata."
        )

    try:
        metadata = json.loads(output)
        streams = metadata.get("streams", [])
        if not streams:
            raise VideoFeatureExtractionError("FFprobe found no video stream.")
        stream = streams[0]
        width = int(stream["width"])
        height = int(stream["height"])
        raw_frame_count = stream.get("nb_frames")
        frame_count = (
            int(raw_frame_count)
            if raw_frame_count not in {None, "", "N/A"}
            else 0
        )
        raw_duration = stream.get("duration") or metadata.get("format", {}).get("duration")
        duration = float(raw_duration) if raw_duration not in {None, "", "N/A"} else 0.0
        source_fps = _parse_frame_rate(stream.get("avg_frame_rate", ""))
        if source_fps <= 0 or source_fps > 60:
            source_fps = _parse_frame_rate(stream.get("r_frame_rate", ""))
        if source_fps <= 0 or source_fps > 60:
            estimated_fps = frame_count / duration if frame_count > 0 and duration > 0 else 0.0
            source_fps = estimated_fps if 0 < estimated_fps <= 60 else 30.0
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VideoFeatureExtractionError(
            f"Invalid FFprobe metadata: {output}"
        ) from exc

    if width <= 0 or height <= 0:
        raise VideoFeatureExtractionError(
            "Video has invalid dimensions."
        )

    if source_fps <= 0:
        raise VideoFeatureExtractionError("Video has an invalid frame rate.")

    return width, height, frame_count, source_fps


def _decode_video_frames(
    video_path: Path,
    width: int,
    height: int,
    output_fps: float,
):
    """
    Decode video frames through FFmpeg and yield BGR OpenCV frames.
    """

    scaled_width, scaled_height = _get_scaled_dimensions(width, height)
    frame_size = scaled_width * scaled_height * 3

    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vf",
        f"fps={output_fps:.6f},scale={scaled_width}:{scaled_height}",
        "-frames:v",
        str(MAX_ANALYZED_VIDEO_FRAMES),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "pipe:1",
    ]

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise VideoFeatureExtractionError(
            "FFmpeg is not installed or is not available in PATH."
        ) from exc

    try:
        while True:
            raw_frame = process.stdout.read(frame_size)

            if not raw_frame:
                break

            if len(raw_frame) != frame_size:
                raise VideoFeatureExtractionError(
                    "FFmpeg returned an incomplete video frame."
                )

            frame = np.frombuffer(
                raw_frame,
                dtype=np.uint8,
            ).reshape(
                (scaled_height, scaled_width, 3)
            )

            yield frame

        stderr_output = process.stderr.read().decode(
            "utf-8",
            errors="replace",
        )

        return_code = process.wait()

        if return_code != 0:
            raise VideoFeatureExtractionError(
                "FFmpeg failed while decoding the video: "
                f"{stderr_output.strip()}"
            )

    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def _distance(
    point_a,
    point_b,
) -> float:
    return float(
        (
            (point_a.x - point_b.x) ** 2
            + (point_a.y - point_b.y) ** 2
        )
        ** 0.5
    )


def _normalized_distance(
    point_a,
    point_b,
    reference_distance: float,
) -> float:
    if reference_distance <= 1e-6:
        return 0.0

    return _distance(point_a, point_b) / reference_distance


def _estimate_eye_contact(
    landmarks,
) -> bool:
    """
    Estimate whether the candidate is approximately looking toward
    the camera using MediaPipe iris/eye landmarks.

    This is an observable gaze-direction heuristic, not a
    psychological or attention classifier.
    """

    # MediaPipe Face Mesh indices.
    #
    # Left eye:
    #   33  -> outer/left eye corner
    #   133 -> inner/right eye corner
    #   468 -> left iris landmark
    #
    # Right eye:
    #   362 -> inner/left eye corner
    #   263 -> outer/right eye corner
    #   473 -> right iris landmark
    #
    # With refine_landmarks=True these iris landmarks are available.

    required_indices = (
        33,
        133,
        362,
        263,
        468,
        473,
    )

    if any(
        index >= len(landmarks)
        for index in required_indices
    ):
        return False

    left_outer = landmarks[33]
    left_inner = landmarks[133]
    left_iris = landmarks[468]

    right_inner = landmarks[362]
    right_outer = landmarks[263]
    right_iris = landmarks[473]

    left_eye_width = _distance(
        left_outer,
        left_inner,
    )

    right_eye_width = _distance(
        right_inner,
        right_outer,
    )

    if left_eye_width <= 1e-6 or right_eye_width <= 1e-6:
        return False

    left_ratio = (
        _distance(
            left_outer,
            left_iris,
        )
        / left_eye_width
    )

    right_ratio = (
        _distance(
            right_inner,
            right_iris,
        )
        / right_eye_width
    )

    # Looking approximately toward the camera tends to place the
    # iris near the central region of the visible eye.
    #
    # We intentionally use a tolerant range because webcam angle,
    # face orientation and lighting can affect the estimate.
    left_centered = 0.25 <= left_ratio <= 0.75
    right_centered = 0.25 <= right_ratio <= 0.75

    return left_centered and right_centered


def _calculate_facial_expression_signal(
    landmarks,
    previous_expression_state: dict[str, float] | None,
) -> tuple[float, dict[str, float]]:
    """
    Measure observable facial movement.

    The result represents movement/activity of facial landmarks.
    It does NOT classify emotions such as happiness, confidence,
    nervousness, etc.
    """

    # Mouth landmarks.
    upper_lip = landmarks[13]
    lower_lip = landmarks[14]
    mouth_left = landmarks[61]
    mouth_right = landmarks[291]

    # Eye landmarks.
    left_eye_top = landmarks[159]
    left_eye_bottom = landmarks[145]
    right_eye_top = landmarks[386]
    right_eye_bottom = landmarks[374]

    mouth_width = _distance(
        mouth_left,
        mouth_right,
    )

    if mouth_width <= 1e-6:
        mouth_width = 1.0

    mouth_opening = _normalized_distance(
        upper_lip,
        lower_lip,
        mouth_width,
    )

    left_eye_height = _distance(
        left_eye_top,
        left_eye_bottom,
    )

    right_eye_height = _distance(
        right_eye_top,
        right_eye_bottom,
    )

    eye_width = (
        _distance(landmarks[33], landmarks[133])
        + _distance(landmarks[362], landmarks[263])
    ) / 2.0

    if eye_width <= 1e-6:
        eye_width = 1.0

    eye_opening = (
        left_eye_height + right_eye_height
    ) / (2.0 * eye_width)

    current_state = {
        "mouth_opening": mouth_opening,
        "eye_opening": eye_opening,
    }

    if previous_expression_state is None:
        return 0.0, current_state

    mouth_change = abs(
        mouth_opening
        - previous_expression_state["mouth_opening"]
    )

    eye_change = abs(
        eye_opening
        - previous_expression_state["eye_opening"]
    )

    # Convert landmark movement into a bounded observable activity
    # signal. The values are intentionally conservative.
    activity = min(
        1.0,
        (mouth_change * 8.0)
        + (eye_change * 12.0),
    )

    return activity, current_state


def _calculate_posture_stability(
    landmarks,
) -> float:
    """
    Estimate posture stability from visible shoulder/hip alignment.

    This measures geometric stability of the visible upper body.
    It does not make a judgment about personality or confidence.
    """

    left_shoulder = landmarks[
        mp.solutions.pose.PoseLandmark.LEFT_SHOULDER
    ]
    right_shoulder = landmarks[
        mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER
    ]

    left_hip = landmarks[
        mp.solutions.pose.PoseLandmark.LEFT_HIP
    ]
    right_hip = landmarks[
        mp.solutions.pose.PoseLandmark.RIGHT_HIP
    ]

    shoulder_visibility = min(
        left_shoulder.visibility,
        right_shoulder.visibility,
    )

    if shoulder_visibility < 0.5:
        return 0.0

    shoulder_center_x = (
        left_shoulder.x + right_shoulder.x
    ) / 2.0

    shoulder_center_y = (
        left_shoulder.y + right_shoulder.y
    ) / 2.0

    hip_visibility = min(
        left_hip.visibility,
        right_hip.visibility,
    )

    if hip_visibility >= 0.5:
        hip_center_x = (
            left_hip.x + right_hip.x
        ) / 2.0

        hip_center_y = (
            left_hip.y + right_hip.y
        ) / 2.0

        torso_dx = abs(
            shoulder_center_x - hip_center_x
        )

        torso_dy = abs(
            shoulder_center_y - hip_center_y
        )

        if torso_dy > 1e-6:
            torso_lean = torso_dx / torso_dy
        else:
            torso_lean = torso_dx
    else:
        # Webcam interviews frequently do not show the hips.
        # Fall back to shoulder symmetry.
        torso_lean = abs(
            left_shoulder.y
            - right_shoulder.y
        )

    # Shoulder tilt.
    shoulder_tilt = abs(
        left_shoulder.y
        - right_shoulder.y
    )

    instability = (
        min(1.0, torso_lean)
        + min(1.0, shoulder_tilt * 4.0)
    ) / 2.0

    stability = max(
        0.0,
        min(
            1.0,
            1.0 - instability,
        ),
    )

    return stability


def analyze_video_features(
    video_path: str | Path,
    sample_every_n_frames: int = 1,
) -> VideoFeatureResult:
    """
    Extract observable visual signals from an interview video.

    Signals include:

    - face visibility
    - approximate camera-directed eye contact
    - observable facial movement
    - posture stability
    - head movement
    - hand/wrist movement

    This function does NOT infer personality, emotion, confidence,
    nervousness, honesty, or psychological state.

    Video decoding is handled by FFmpeg.
    """

    video_path = Path(video_path)

    if not video_path.exists():
        raise VideoFeatureExtractionError(
            f"Video file does not exist: {video_path}"
        )

    if sample_every_n_frames <= 0:
        raise VideoFeatureExtractionError(
            "sample_every_n_frames must be greater than zero."
        )

    source_width, source_height, reported_frame_count, source_fps = _get_video_metadata(
        video_path
    )

    # The previous path analyzed every fifth source frame. Apply that
    # sampling and resize during FFmpeg decode to avoid full-size frames.
    output_fps = _get_output_fps(source_fps, sample_every_n_frames)
    width = max(2, int(round(source_width * 480 / source_height / 2) * 2))
    height = 480
    total_frames = reported_frame_count

    analyzed_frames = 0
    face_detected_frames = 0
    pose_detected_frames = 0

    eye_contact_frames = 0

    facial_expression_activity_values: list[float] = []
    posture_stability_values: list[float] = []

    previous_head_x: float | None = None
    previous_head_y: float | None = None

    previous_left_wrist: tuple[float, float] | None = None
    previous_right_wrist: tuple[float, float] | None = None

    previous_expression_state: dict[str, float] | None = None

    head_movement_count = 0
    gesture_count = 0

    mp_face_mesh = mp.solutions.face_mesh
    mp_pose = mp.solutions.pose

    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as face_mesh, mp_pose.Pose(
        static_image_mode=False,
        model_complexity=0,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose_detector:

        frame_index = 0
        feature_started = time.perf_counter()
        mediapipe_seconds = 0.0

        for frame in _decode_video_frames(
            video_path=video_path,
            width=width,
            height=height,
            output_fps=output_fps,
        ):
            analyzed_frames += 1

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            mediapipe_started = time.perf_counter()
            face_mesh_result = face_mesh.process(rgb_frame)
            pose_result = pose_detector.process(rgb_frame)
            mediapipe_seconds += time.perf_counter() - mediapipe_started

            if face_mesh_result.multi_face_landmarks:
                face_detected_frames += 1
                landmarks = face_mesh_result.multi_face_landmarks[0].landmark
                head_x = (min(point.x for point in landmarks) + max(point.x for point in landmarks)) / 2
                head_y = (min(point.y for point in landmarks) + max(point.y for point in landmarks)) / 2

                if previous_head_x is not None:
                    movement_distance = (
                        (
                            head_x
                            - previous_head_x
                        ) ** 2
                        + (
                            head_y
                            - previous_head_y
                        ) ** 2
                    ) ** 0.5

                    if movement_distance > 0.03:
                        head_movement_count += 1

                previous_head_x = head_x
                previous_head_y = head_y

                face_landmarks = (
                    face_mesh_result
                    .multi_face_landmarks[0]
                    .landmark
                )

                if _estimate_eye_contact(
                    face_landmarks
                ):
                    eye_contact_frames += 1

                (
                    expression_activity,
                    previous_expression_state,
                ) = _calculate_facial_expression_signal(
                    face_landmarks,
                    previous_expression_state,
                )

                facial_expression_activity_values.append(
                    expression_activity
                )

            if pose_result.pose_landmarks:
                pose_detected_frames += 1

                landmarks = (
                    pose_result
                    .pose_landmarks
                    .landmark
                )

                posture_stability = (
                    _calculate_posture_stability(
                        landmarks
                    )
                )

                posture_stability_values.append(
                    posture_stability
                )

                left_wrist = landmarks[
                    mp_pose.PoseLandmark.LEFT_WRIST
                ]

                right_wrist = landmarks[
                    mp_pose.PoseLandmark.RIGHT_WRIST
                ]

                if (
                    left_wrist.visibility > 0.5
                    and right_wrist.visibility > 0.5
                ):
                    current_left = (
                        left_wrist.x,
                        left_wrist.y,
                    )

                    current_right = (
                        right_wrist.x,
                        right_wrist.y,
                    )

                    if previous_left_wrist is not None:
                        left_distance = (
                            (
                                current_left[0]
                                - previous_left_wrist[0]
                            ) ** 2
                            + (
                                current_left[1]
                                - previous_left_wrist[1]
                            ) ** 2
                        ) ** 0.5

                        if left_distance > 0.05:
                            gesture_count += 1

                    if previous_right_wrist is not None:
                        right_distance = (
                            (
                                current_right[0]
                                - previous_right_wrist[0]
                            ) ** 2
                            + (
                                current_right[1]
                                - previous_right_wrist[1]
                            ) ** 2
                        ) ** 0.5

                        if right_distance > 0.05:
                            gesture_count += 1

                    previous_left_wrist = current_left
                    previous_right_wrist = current_right

            frame_index += 1

    feature_elapsed = time.perf_counter() - feature_started
    feature_timings = {
        "decode_seconds": max(0.0, feature_elapsed - mediapipe_seconds),
        "mediapipe_seconds": mediapipe_seconds,
    }
    logger.info(
        "[VIDEO-ANALYSIS] file=%s decode_seconds=%.3f mediapipe_seconds=%.3f",
        video_path.name,
        feature_timings["decode_seconds"],
        feature_timings["mediapipe_seconds"],
    )

    if total_frames <= 0:
        total_frames = frame_index

    if analyzed_frames == 0:
        raise VideoFeatureExtractionError(
            "No frames were analyzed."
        )

    face_visibility_percentage = (
        face_detected_frames
        / analyzed_frames
    ) * 100.0

    eye_contact_percentage = (
        (
            eye_contact_frames
            / face_detected_frames
        ) * 100.0
        if face_detected_frames > 0
        else 0.0
    )

    facial_expression_activity = (
        float(
            np.mean(
                facial_expression_activity_values
            )
        ) * 100.0
        if facial_expression_activity_values
        else 0.0
    )

    posture_stability_percentage = (
        float(
            np.mean(
                posture_stability_values
            )
        ) * 100.0
        if posture_stability_values
        else 0.0
    )

    return VideoFeatureResult(
        total_frames=total_frames,
        analyzed_frames=analyzed_frames,
        face_detected_frames=face_detected_frames,
        pose_detected_frames=pose_detected_frames,
        face_visibility_percentage=round(
            face_visibility_percentage,
            2,
        ),
        eye_contact_percentage=round(
            eye_contact_percentage,
            2,
        ),
        facial_expression_activity=round(
            facial_expression_activity,
            2,
        ),
        posture_stability_percentage=round(
            posture_stability_percentage,
            2,
        ),
        head_movement_count=head_movement_count,
        gesture_count=gesture_count,
        timings=feature_timings,
    )