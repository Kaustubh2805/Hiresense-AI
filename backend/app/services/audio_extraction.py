from pathlib import Path
import subprocess


class AudioExtractionError(Exception):
    """Raised when audio extraction fails."""


def extract_audio(
    video_path: str | Path,
    output_path: str | Path,
) -> Path:
    """
    Extract the audio track from a video file.

    The resulting audio is:
    - WAV format
    - mono
    - 16 kHz sample rate
    - PCM 16-bit

    These settings give us a consistent input for
    later audio analysis.
    """

    video_path = Path(video_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise AudioExtractionError(
            f"Video file does not exist: {video_path}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-acodec",
        "pcm_s16le",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise AudioExtractionError(
            "FFmpeg could not be executed."
        ) from exc

    if result.returncode != 0:
        raise AudioExtractionError(
            "FFmpeg audio extraction failed:\n"
            f"{result.stderr}"
        )

    if not output_path.exists():
        raise AudioExtractionError(
            "FFmpeg completed successfully, "
            "but the output audio file was not created."
        )

    if output_path.stat().st_size == 0:
        raise AudioExtractionError(
            "FFmpeg created an empty audio file."
        )

    return output_path