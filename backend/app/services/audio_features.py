from pathlib import Path
import re

import librosa
import numpy as np
from app.services.hesitation_analysis import detect_hesitation

class AudioFeatureExtractionError(Exception):
    """Raised when audio feature extraction fails."""


def calculate_words_per_minute(
    transcript_text: str | None,
    duration_seconds: float,
) -> float | None:
    """
    Calculate speaking rate from the existing interview transcript.

    Returns words per minute, or None when there is not enough
    information to calculate it reliably.
    """

    if not transcript_text:
        return None

    if duration_seconds <= 0:
        return None

    words = transcript_text.split()

    if not words:
        return None

    word_count = len(words)

    return (
        word_count / duration_seconds
    ) * 60.0

def detect_filler_words(
    transcript_text: str | None,
) -> dict:
    """
    Detect common filler words and phrases in an interview transcript.

    The detector intentionally focuses on relatively clear filler
    expressions. Ambiguous words such as "well" and "like" are not
    counted initially because they can be legitimate parts of a sentence.

    Returns:
        filler_word_count:
            Total number of detected filler expressions.

        filler_words:
            Dictionary containing each detected filler and its count.

        word_count:
            Number of transcript words.

        filler_density_per_100_words:
            Number of fillers per 100 transcript words.
    """

    if not transcript_text:
        return {
            "filler_word_count": 0,
            "filler_words": {},
            "word_count": 0,
            "filler_density_per_100_words": 0.0,
        }

    text = transcript_text.lower()

    # Normalize punctuation while preserving spaces.
    text = re.sub(
        r"[^\w\s']",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if not text:
        return {
            "filler_word_count": 0,
            "filler_words": {},
            "word_count": 0,
            "filler_density_per_100_words": 0.0,
        }

    words = text.split()

    word_count = len(words)

    # Multi-word expressions are checked first.
    filler_patterns = {
        "you know": r"\byou\s+know\b",
        "i mean": r"\bi\s+mean\b",
        "kind of": r"\bkind\s+of\b",
        "sort of": r"\bsort\s+of\b",
        "basically": r"\bbasically\b",
        "actually": r"\bactually\b",
        "literally": r"\bliterally\b",
        "um": r"\bum+\b",
        "uh": r"\buh+\b",
    }

    detected_fillers: dict[str, int] = {}

    total_filler_count = 0

    for filler_name, pattern in filler_patterns.items():
        matches = re.findall(
            pattern,
            text,
        )

        count = len(matches)

        if count > 0:
            detected_fillers[filler_name] = count
            total_filler_count += count

    filler_density_per_100_words = (
        total_filler_count / word_count
    ) * 100.0 if word_count else 0.0

    return {
        "filler_word_count": total_filler_count,
        "filler_words": detected_fillers,
        "word_count": word_count,
        "filler_density_per_100_words": (
            float(filler_density_per_100_words)
        ),
    }


def maximum_filler_measurement(
    browser_transcript: str | None,
    whisper_transcript: str | None,
    word_count: int,
) -> dict:
    browser = detect_filler_words(browser_transcript)
    whisper = detect_filler_words(whisper_transcript)
    count = max(
        browser["filler_word_count"],
        whisper["filler_word_count"],
    )
    by_type = (
        browser["filler_words"]
        if browser["filler_word_count"] >= whisper["filler_word_count"]
        else whisper["filler_words"]
    )
    return {
        "filler_word_count": count,
        "filler_words": by_type,
        "filler_density_per_100_words": (
            count / word_count * 100 if word_count else 0.0
        ),
    }


def score_filler_usage(
    filler_word_count: int,
    word_count: int,
) -> float | None:
    """
    Score filler-word usage on a 1–10 scale.

    The score is based on filler density rather than raw filler count,
    because longer answers naturally have more opportunities to contain
    filler expressions.

    Lower filler density produces a higher score.
    """

    if word_count <= 0:
        return None

    filler_density = (
        filler_word_count / word_count
    ) * 100.0

    if filler_density <= 0:
        score = 10.0

    elif filler_density <= 2:
        score = 9.0

    elif filler_density <= 4:
        score = 8.0

    elif filler_density <= 6:
        score = 6.5

    elif filler_density <= 10:
        score = 5.0

    else:
        score = 3.5

    return float(score)

def extract_acoustic_features(
    audio_path: str | Path,
    transcript_text: str | None = None,
) -> dict:
    """
    Extract basic acoustic features from a WAV recording.

    The input is expected to be the normalized WAV produced by
    audio_extraction.extract_audio():
        - mono
        - 16 kHz
        - PCM 16-bit

    This function measures observable acoustic properties.
    It does not produce interview scores.
    """

    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise AudioFeatureExtractionError(
            f"Audio file does not exist: {audio_path}"
        )

    try:
        audio, sample_rate = librosa.load(
            str(audio_path),
            sr=16000,
            mono=True,
        )
    except Exception as exc:
        raise AudioFeatureExtractionError(
            f"Could not load audio file: {audio_path}"
        ) from exc

    if audio.size == 0:
        raise AudioFeatureExtractionError(
            "Audio file contains no samples."
        )

    duration_seconds = float(
        librosa.get_duration(
            y=audio,
            sr=sample_rate,
        )
    )
    words_per_minute = calculate_words_per_minute(
        transcript_text=transcript_text,
        duration_seconds=duration_seconds,
    )

    filler_analysis = detect_filler_words(
        transcript_text
    )

    filler_word_count = (
        filler_analysis["filler_word_count"]
    )

    filler_density_per_100_words = (
        filler_analysis["filler_density_per_100_words"]
    )

    filler_word_score = score_filler_usage(
        filler_word_count=filler_word_count,
        word_count=filler_analysis["word_count"],
    )
    # RMS energy measures the signal's average amplitude.
    # It is useful as a raw proxy for vocal energy/volume.
    rms = librosa.feature.rms(
        y=audio,
    )[0]

    mean_rms = float(
        np.mean(rms)
    )

    max_rms = float(
        np.max(rms)
    )

    # Convert the waveform into short-time frames.
    # This allows us to distinguish relatively quiet sections
    # from sections containing stronger speech energy.
    frame_length = 512
    hop_length = 256

    rms_frames = librosa.feature.rms(
        y=audio,
        frame_length=frame_length,
        hop_length=hop_length,
    )[0]

    # A dynamic threshold is more reliable than a fixed amplitude
    # threshold because browser recordings can have different
    # microphone levels.
    noise_floor = float(
        np.percentile(
            rms_frames,
            20,
        )
    )

    speech_threshold = max(
        noise_floor * 2.0,
        0.01,
    )

    speech_frames = (
        rms_frames >= speech_threshold
    )

    speech_frame_count = int(
        np.sum(speech_frames)
    )

    total_frame_count = len(
        speech_frames
    )

    speech_ratio = (
        speech_frame_count / total_frame_count
        if total_frame_count
        else 0.0
    )

    silence_ratio = max(
        0.0,
        1.0 - speech_ratio,
    )

    # Convert frame indexes into approximate time intervals.
    frame_duration = (
        hop_length / sample_rate
    )

    pause_count = 0
    total_pause_seconds = 0.0
    longest_pause_seconds = 0.0

    current_pause_frames = 0

    for is_speech in speech_frames:
        if is_speech:
            if current_pause_frames > 0:
                pause_seconds = (
                    current_pause_frames
                    * frame_duration
                )

                # Ignore extremely short gaps.
                # They are usually natural signal variation,
                # not meaningful pauses in speech.
                if pause_seconds >= 0.25:
                    pause_count += 1
                    total_pause_seconds += pause_seconds
                    longest_pause_seconds = max(
                        longest_pause_seconds,
                        pause_seconds,
                    )

                current_pause_frames = 0

        else:
            current_pause_frames += 1

    # Handle a recording that ends during silence.
    if current_pause_frames > 0:
        pause_seconds = (
            current_pause_frames
            * frame_duration
        )

        if pause_seconds >= 0.25:
            pause_count += 1
            total_pause_seconds += pause_seconds
            longest_pause_seconds = max(
                longest_pause_seconds,
                pause_seconds,
            )

    average_pause_seconds = (
        total_pause_seconds / pause_count
        if pause_count
        else 0.0
    )

    hesitation_analysis = detect_hesitation(
        pause_count=pause_count,
        total_pause_seconds=total_pause_seconds,
        longest_pause_seconds=longest_pause_seconds,
        duration_seconds=duration_seconds,
        filler_word_count=filler_analysis["filler_word_count"],
    )

    return {
        "duration_seconds": duration_seconds,
        "sample_rate": int(sample_rate),
        "mean_rms": mean_rms,
        "max_rms": max_rms,
        "speech_ratio": float(speech_ratio),
        "silence_ratio": float(silence_ratio),
        "pause_count": pause_count,
        "total_pause_seconds": float(
            total_pause_seconds
        ),
        "average_pause_seconds": float(
            average_pause_seconds
        ),
        "longest_pause_seconds": float(
            longest_pause_seconds
        ),
        "words_per_minute": words_per_minute,
        "filler_word_count": filler_word_count,
        "filler_words": filler_analysis["filler_words"],
        "word_count": filler_analysis["word_count"],
        "filler_density_per_100_words": (
            filler_density_per_100_words
        ),
        "filler_word_score": filler_word_score,
        
        "hesitation_count": hesitation_analysis["hesitation_count"],
        "hesitation_score": hesitation_analysis["hesitation_score"],
        "long_pause_count": hesitation_analysis["long_pause_count"],
        "pause_ratio": hesitation_analysis["pause_ratio"],
        "repeated_hesitation": hesitation_analysis["repeated_hesitation"],
    }