import json
from types import SimpleNamespace

import pytest

from app.services.video_features import (
    _get_output_fps,
    _get_scaled_dimensions,
    _parse_frame_rate,
    _get_video_metadata,
)


def test_ffmpeg_sampling_caps_work_to_two_frames_per_second() -> None:
    assert _get_output_fps(30) == 2
    assert _get_output_fps(25) == 2
    assert _get_output_fps(24, sample_every_n_frames=4) == 1.2


def test_scaled_frame_dimensions_match_ffmpeg_output_and_preserve_aspect_ratio() -> None:
    assert _get_scaled_dimensions(1920, 1080) == (640, 360)
    assert _get_scaled_dimensions(720, 1280) == (202, 360)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("30000/1001", pytest.approx(29.97, rel=0.001)), ("0/0", 0.0), ("N/A", 0.0)],
)
def test_frame_rate_metadata_parsing(value: str, expected: float) -> None:
    assert _parse_frame_rate(value) == expected


def test_webm_metadata_without_frame_count_uses_sane_fallback(monkeypatch, tmp_path) -> None:
    output = json.dumps(
        {
            "streams": [
                {
                    "width": 640,
                    "height": 480,
                    "avg_frame_rate": "1000/1",
                    "r_frame_rate": "0/0",
                }
            ],
            "format": {"duration": "48.0"},
        }
    )
    monkeypatch.setattr(
        "app.services.video_features.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout=output),
    )

    assert _get_video_metadata(tmp_path / "answer.webm") == (640, 480, 0, 30.0)


def test_video_metadata_uses_named_fields_and_frame_duration(monkeypatch, tmp_path) -> None:
    output = json.dumps(
        {
            "streams": [
                {
                    "width": 1280,
                    "height": 720,
                    "nb_frames": "900",
                    "avg_frame_rate": "1000/1",
                    "r_frame_rate": "0/0",
                    "duration": "30",
                }
            ],
            "format": {"duration": "30"},
        }
    )
    monkeypatch.setattr(
        "app.services.video_features.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout=output),
    )

    assert _get_video_metadata(tmp_path / "answer.webm") == (1280, 720, 900, 30.0)
