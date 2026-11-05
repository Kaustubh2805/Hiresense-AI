import tempfile
from pathlib import Path
from uuid import UUID

from app.db.database import SessionLocal
from app.services.audio_extraction import extract_audio
from app.services.audio_sample_selection import select_audio_samples
from app.services.storage import download_interview_video
from app.services.audio_inspection import inspect_wav

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

        if not samples:
            print("No audio samples were found.")
            return

        baseline_sample = next(
            (
                sample
                for sample in samples
                if sample.sample_type == "baseline"
            ),
            None,
        )

        if baseline_sample is None:
            print("No baseline sample was found.")
            return

        print()
        print("AUDIO EXTRACTION TEST")
        print("=" * 80)
        print(f"Session ID:       {SESSION_ID}")
        print(f"Sample type:      {baseline_sample.sample_type}")
        print(f"Question order:   {baseline_sample.question_order}")
        print(f"Question ID:      {baseline_sample.session_question_id}")
        print(f"Video object:     {baseline_sample.video_url}")
        print()

        with tempfile.TemporaryDirectory(
            prefix="hiresense_audio_test_"
        ) as temp_directory:

            temp_directory = Path(temp_directory)

            video_path = (
                temp_directory / "input.webm"
            )

            audio_path = (
                temp_directory / "output.wav"
            )

            print("Downloading video from MinIO...")

            download_interview_video(
                object_name=baseline_sample.video_url,
                output_path=str(video_path),
            )

            print(
                f"Downloaded video size: "
                f"{video_path.stat().st_size} bytes"
            )

            print()
            print("Extracting audio with FFmpeg...")

            extract_audio(
                video_path=video_path,
                output_path=audio_path,
            )

            print(
                f"Extracted audio size: "
                f"{audio_path.stat().st_size} bytes"
            )
            audio_info = inspect_wav(audio_path)

            print()
            print("WAV INSPECTION")
            print("-" * 80)
            print(f"Channels:          {audio_info['channels']}")
            print(f"Sample rate:       {audio_info['sample_rate']} Hz")
            print(f"Sample width:      {audio_info['sample_width_bytes']} bytes")
            print(f"Frame count:       {audio_info['frame_count']}")
            print(
                f"Duration:          "
                f"{audio_info['duration_seconds']:.2f} seconds"
            )
            print()
            print("AUDIO EXTRACTION SUCCESS")
            print("=" * 80)
            print(f"Video file: {video_path}")
            print(f"Audio file: {audio_path}")
            print()
            print(
                "The temporary files will be deleted automatically."
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()