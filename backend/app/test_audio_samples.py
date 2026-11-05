from uuid import UUID

from app.db.database import SessionLocal
from app.services.audio_sample_selection import select_audio_samples


SESSION_ID = UUID(
    "add11190-f56e-452f-94a3-b1f1d0b403d0"
)


def main():
    db = SessionLocal()

    try:
        samples = select_audio_samples(
            db=db,
            session_id=SESSION_ID,
        )

        print()
        print("SELECTED AUDIO SAMPLES")
        print("=" * 80)

        for sample in samples:
            print()
            print(f"Sample type:       {sample.sample_type}")
            print(f"Question order:    {sample.question_order}")
            print(f"Source:             {sample.source}")
            print(f"Duration:           {sample.time_taken_seconds}s")
            print(f"Question ID:        {sample.session_question_id}")
            print(f"Video URL:          {sample.video_url}")
            print(f"Transcript:         {sample.transcript_text}")
            print("-" * 80)

        print()
        print(f"Total samples: {len(samples)}")

    finally:
        db.close()


if __name__ == "__main__":
    main()