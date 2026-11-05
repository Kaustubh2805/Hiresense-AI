import tempfile
from pathlib import Path
from uuid import UUID

from app.db.database import SessionLocal
from app.services.audio_extraction import extract_audio
from app.services.audio_features import extract_acoustic_features
from app.services.audio_sample_selection import select_audio_samples
from app.services.audio_scoring import score_audio_features
from app.services.storage import download_interview_video


SESSION_ID = UUID(
    "add11190-f56e-452f-94a3-b1f1d0b403d0"
)


def main():
    db = SessionLocal()

    try:
        print()
        print("REAL AUDIO ANALYSIS PIPELINE")
        print("=" * 80)

        # ------------------------------------------------------------------
        # 1. Select a real recording from the completed interview.
        # ------------------------------------------------------------------

        samples = select_audio_samples(
            db=db,
            session_id=SESSION_ID,
        )

        if not samples:
            raise RuntimeError(
                "No audio samples were found for the session."
            )

        sample = samples[0]

        print()
        print("SELECTED SAMPLE")
        print("-" * 80)
        print(
            f"Sample type:       {sample.sample_type}"
        )
        print(
            f"Question order:    {sample.question_order}"
        )
        print(
            f"Question ID:       {sample.session_question_id}"
        )
        print(
            f"Video object:      {sample.video_url}"
        )
        print(
            f"Transcript:        {sample.transcript_text!r}"
        )

        # ------------------------------------------------------------------
        # 2. Create temporary local files.
        # ------------------------------------------------------------------

        with tempfile.TemporaryDirectory(
            prefix="hiresense_audio_pipeline_"
        ) as temp_directory:

            temp_directory = Path(
                temp_directory
            )

            video_path = (
                temp_directory / "input.webm"
            )

            audio_path = (
                temp_directory / "output.wav"
            )

            # --------------------------------------------------------------
            # 3. Download the real video from MinIO.
            # --------------------------------------------------------------

            print()
            print("DOWNLOADING VIDEO")
            print("-" * 80)

            download_interview_video(
                object_name=sample.video_url,
                output_path=str(video_path),
            )

            print(
                f"Downloaded video size: "
                f"{video_path.stat().st_size} bytes"
            )

            # --------------------------------------------------------------
            # 4. Extract normalized WAV audio.
            # --------------------------------------------------------------

            print()
            print("EXTRACTING AUDIO")
            print("-" * 80)

            extract_audio(
                video_path=video_path,
                output_path=audio_path,
            )

            print(
                f"Extracted audio size: "
                f"{audio_path.stat().st_size} bytes"
            )

            # --------------------------------------------------------------
            # 5. Extract real acoustic features.
            # --------------------------------------------------------------

            print()
            print("EXTRACTING ACOUSTIC FEATURES")
            print("-" * 80)

            features = extract_acoustic_features(
                audio_path=audio_path,
                transcript_text=sample.transcript_text,
            )

            print(
                f"Duration:              "
                f"{features['duration_seconds']:.2f} s"
            )

            print(
                f"Sample rate:           "
                f"{features['sample_rate']} Hz"
            )

            print(
                f"Mean RMS:              "
                f"{features['mean_rms']:.6f}"
            )

            print(
                f"Maximum RMS:           "
                f"{features['max_rms']:.6f}"
            )

            print(
                f"Speech ratio:          "
                f"{features['speech_ratio']:.3f}"
            )

            print(
                f"Silence ratio:         "
                f"{features['silence_ratio']:.3f}"
            )

            print(
                f"Pause count:           "
                f"{features['pause_count']}"
            )

            print(
                f"Total pause time:      "
                f"{features['total_pause_seconds']:.2f} s"
            )

            print(
                f"Average pause:         "
                f"{features['average_pause_seconds']:.2f} s"
            )

            print(
                f"Longest pause:         "
                f"{features['longest_pause_seconds']:.2f} s"
            )

            if features["words_per_minute"] is not None:
                print(
                    f"Words per minute:      "
                    f"{features['words_per_minute']:.2f}"
                )
            else:
                print(
                    "Words per minute:      unavailable"
                )

            # --------------------------------------------------------------
            # 6. Convert real features into 1–10 scores.
            # --------------------------------------------------------------

            print()
            print("SCORING REAL FEATURES")
            print("-" * 80)

            scores = score_audio_features(
                features
            )

            print(
                f"Pace:                  "
                f"{scores['pace']:.2f}/10"
            )

            print(
                f"Pause management:      "
                f"{scores['pause_management']:.2f}/10"
            )

            print(
                f"Fluency:               "
                f"{scores['fluency']:.2f}/10"
            )

            print(
                f"Vocal energy:          "
                f"{scores['vocal_energy']:.2f}/10"
            )

            print("-" * 80)

            print(
                f"Overall audio score:   "
                f"{scores['overall_score']:.2f}/10"
            )

            print()
            print("=" * 80)
            print("REAL AUDIO PIPELINE SUCCESS")
            print("=" * 80)
            print()

    finally:
        db.close()


if __name__ == "__main__":
    main()