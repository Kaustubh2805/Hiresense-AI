import sys
from uuid import UUID

from app.db.database import SessionLocal
from app.services.video_sample_selection import select_video_samples
from app.services.storage import download_interview_video
from app.services.video_features import analyze_video_features
from app.services.video_scoring import score_video_features
from app.services.video_persistence import save_video_evaluation

DEFAULT_SESSION_ID = UUID("cb3351a0-d79d-4807-9206-521187da7b22")


def main(session_id: UUID = DEFAULT_SESSION_ID):
    db = SessionLocal()

    try:
        samples = select_video_samples(
            db=db,
            session_id=session_id,
        )

        longest_video = samples[0]

        print("Selected video:")
        print("Question:", longest_video.question_order)
        print("Duration:", longest_video.duration_seconds)
        print("Object:", longest_video.video_url)

        output_path = (
            f"/tmp/video_analysis_{longest_video.session_question_id}.webm"
        )

        print("\nDownloading video from MinIO...")

        download_interview_video(
            object_name=longest_video.video_url,
            output_path=output_path,
        )

        print("Downloaded:", output_path)

        print("\nRunning computer vision analysis...")

        result = analyze_video_features(
            video_path=output_path,
        )

        print("\n===== VIDEO FEATURE RESULTS =====")
        print("Total frames:", result.total_frames)
        print("Analyzed frames:", result.analyzed_frames)
        print("Face detected frames:", result.face_detected_frames)
        print("Pose detected frames:", result.pose_detected_frames)
        print(
            "Face visibility:",
            f"{result.face_visibility_percentage}%",
        )
        print("Head movements:", result.head_movement_count)
        print("Gestures:", result.gesture_count)
        scores = score_video_features(result)

        print("\n===== VIDEO SCORE RESULTS =====")
        print("Eye contact:", scores.eye_contact)
        print("Facial expression:", scores.facial_expression)
        print("Posture:", scores.posture)
        print("Head movement:", scores.head_movement)
        print("Gestures:", scores.gestures)
        print("Body language:", scores.body_language)
        print("Attentiveness:", scores.attentiveness)
        print("Visual confidence:", scores.visual_confidence)
        print("Overall score:", scores.overall_score)

        print("\nSaving video evaluation to PostgreSQL...")

        saved_evaluation = save_video_evaluation(
            db=db,
            session_question_id=longest_video.session_question_id,
            features=result,
            scores=scores,
        )

        print("===== VIDEO EVALUATION SAVED =====")
        print("Evaluation ID:", saved_evaluation.id)
        print("Session question ID:", saved_evaluation.session_question_id)
        print("Overall score:", saved_evaluation.overall_score)
        print("Analysis status:", saved_evaluation.analysis_status)
    finally:
        db.close()


if __name__ == "__main__":
    main(UUID(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SESSION_ID)