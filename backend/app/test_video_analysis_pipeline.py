import sys
from uuid import UUID

from app.db.database import SessionLocal
from app.services.video_analysis_pipeline import analyze_session_videos


SESSION_ID = UUID(
    "4f81691f-bc64-4107-9526-c6913b8e98ff"
)


def main(session_id: UUID = SESSION_ID):
    db = SessionLocal()

    try:
        print("Starting video analysis (up to five answers)...")
        print(f"Session: {session_id}")

        results = analyze_session_videos(
            db=db,
            session_id=session_id,
        )

        print()
        print("===== VIDEO ANALYSIS RESULTS =====")

        print(f"Result count: {len(results)}")

        for result in results:
            print()
            print(
                f"Question order: {result.question_order}"
            )
            print(
                f"Session question ID: "
                f"{result.session_question_id}"
            )
            print(
                f"Status: "
                f"{result.analysis_status}"
            )
            print(
                f"Overall score: "
                f"{result.overall_score}"
            )

            if result.error_message:
                print(
                    f"Error: "
                    f"{result.error_message}"
                )

    finally:
        db.close()


if __name__ == "__main__":
    main(UUID(sys.argv[1]) if len(sys.argv) > 1 else SESSION_ID)