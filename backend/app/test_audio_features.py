import tempfile
import wave
from pathlib import Path

import numpy as np

from app.services.audio_features import (
    extract_acoustic_features,
    maximum_filler_measurement,
)
from app.services.video_scoring import score_video_features


def test_maximum_filler_measurement_keeps_filler_seen_by_either_transcript():
    measurement = maximum_filler_measurement(
        "Um, I built this.",
        "I, uh, built this.",
        word_count=5,
    )

    assert measurement["filler_word_count"] == 1
    assert measurement["filler_words"] == {"um": 1}
    assert measurement["filler_density_per_100_words"] == 20

def create_test_wav(output_path: Path) -> None:
    """
    Create a small synthetic mono WAV file containing:
    - speech-like audio
    - a period of silence
    - more speech-like audio

    This lets us test feature extraction without requiring
    PostgreSQL, MinIO, Docker, or an actual interview session.
    """

    sample_rate = 16000

    speech_1 = np.sin(
        2 * np.pi * 220 * np.arange(sample_rate * 2) / sample_rate
    )

    silence = np.zeros(
        int(sample_rate * 0.8)
    )

    speech_2 = np.sin(
        2 * np.pi * 220 * np.arange(sample_rate * 2) / sample_rate
    )

    audio = np.concatenate(
        [
            speech_1,
            silence,
            speech_2,
        ]
    )

    audio = (audio * 0.25 * 32767).astype(np.int16)

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio.tobytes())


def test_audio_feature_extraction():
    with tempfile.TemporaryDirectory(
        prefix="hiresense_features_test_"
    ) as temp_directory:

        audio_path = Path(temp_directory) / "test.wav"

        create_test_wav(audio_path)

        features = extract_acoustic_features(
            audio_path=audio_path,
            transcript_text=(
                "I think this approach is useful "
                "because it reduces complexity."
            ),
        )

        print()
        print("ACOUSTIC FEATURE EXTRACTION")
        print("=" * 80)

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

        print(
            f"Words per minute:      "
            f"{features['words_per_minute']:.2f}"
            if features["words_per_minute"] is not None
            else "Words per minute:      unavailable"
        )

        print()
        print("HESITATION FEATURES")
        print("-" * 40)

        print(
            f"Hesitation count:      "
            f"{features['hesitation_count']}"
        )

        print(
            f"Hesitation score:      "
            f"{features['hesitation_score']:.2f}/10"
        )

        print(
            f"Long pause count:      "
            f"{features['long_pause_count']}"
        )

        print(
            f"Pause ratio:           "
            f"{features['pause_ratio']:.3f}"
        )

        print(
            f"Repeated hesitation:   "
            f"{features['repeated_hesitation']}"
        )

        # Verify that hesitation analysis is integrated
        # into acoustic feature extraction.
        assert "hesitation_count" in features
        assert "hesitation_score" in features
        assert "long_pause_count" in features
        assert "pause_ratio" in features
        assert "repeated_hesitation" in features

        assert 1 <= features["hesitation_score"] <= 10

        print()
        print("FEATURE EXTRACTION SUCCESS")
        print("=" * 80)