from pathlib import Path
import wave


def inspect_wav(audio_path: str | Path) -> dict:
    """
    Inspect a WAV file and return its basic audio properties.
    """

    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file does not exist: {audio_path}"
        )

    with wave.open(str(audio_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()

    duration_seconds = (
        frame_count / sample_rate
        if sample_rate
        else 0
    )

    return {
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate": sample_rate,
        "frame_count": frame_count,
        "duration_seconds": duration_seconds,
    }