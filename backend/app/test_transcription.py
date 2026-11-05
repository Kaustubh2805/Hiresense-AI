from types import SimpleNamespace

import pytest
import numpy as np

from app.services import transcription
from scripts.compare_transcripts import calculate_wer, normalize


def test_prompt_contains_context_and_is_limited_to_200_characters():
    prompt = transcription.build_initial_prompt(
        "Backend Engineer",
        ["Python", "PostgreSQL"],
        "How did you design an API?",
    )
    assert "Backend Engineer" in prompt
    assert "Python" in prompt
    assert "How did you design an API?" in prompt
    assert "Transcribe Hindi and English as spoken" in prompt
    assert len(prompt) <= 200


def test_transcribe_video_uses_extracted_audio_and_cpu_model(monkeypatch, tmp_path):
    monkeypatch.setenv("WHISPER_MULTILINGUAL", "false")
    monkeypatch.setenv("WHISPER_MODEL", "small.en")
    monkeypatch.setenv("WHISPER_LANGUAGE", "en")
    video_path = tmp_path / "video.webm"
    audio_path = tmp_path / "audio.wav"
    video_path.write_bytes(b"video")
    audio_path.write_bytes(b"audio")
    captured = {}

    class FakeModel:
        def transcribe(self, path, **kwargs):
            captured["path"] = path
            captured["kwargs"] = kwargs
            return (
                iter(
                    [
                        SimpleNamespace(text=" Hello", avg_logprob=-0.2),
                        SimpleNamespace(text=" world.", avg_logprob=-0.4),
                    ]
                ),
                SimpleNamespace(duration=4.5),
            )

    monkeypatch.setattr(
        transcription,
        "extract_audio",
        lambda video_path, output_path: audio_path,
    )
    monkeypatch.setattr(
        transcription.soundfile,
        "read",
        lambda *args, **kwargs: (np.zeros(1600, dtype=np.float32), 16000),
    )
    monkeypatch.setattr(transcription, "_get_model", lambda: FakeModel())
    result = transcription.transcribe_video(
        video_path,
        role="Engineer",
        skills=["Python"],
        question="What did you build?",
    )

    assert result == {
        "text": "Hello world.",
        "average_log_probability": -0.30000000000000004,
        "confidence": pytest.approx(0.7408182206817179),
        "duration_seconds": 4.5,
        "model": "small.en",
        "detected_languages": ["en"],
    }
    assert captured["path"].shape == (1600,)
    assert captured["path"].dtype == np.float32
    assert captured["kwargs"]["language"] == "en"
    assert captured["kwargs"]["beam_size"] == 5
    assert captured["kwargs"]["vad_parameters"] == {
        "min_silence_duration_ms": 500
    }
    assert captured["kwargs"]["condition_on_previous_text"] is False
    assert captured["kwargs"]["temperature"] == 0
    assert len(captured["kwargs"]["initial_prompt"]) <= 200


def test_multilingual_transcription_autodetects_language(monkeypatch):
    monkeypatch.setenv("WHISPER_MULTILINGUAL", "true")
    monkeypatch.setenv("WHISPER_MODEL", "small.en")
    monkeypatch.setenv("WHISPER_MODEL_MULTILINGUAL", "small")
    monkeypatch.setenv("WHISPER_LANGUAGE", "auto")

    assert transcription._get_selected_whisper_model() == "small"
    assert transcription._get_whisper_language() is None


def test_multilingual_transcription_detects_language_per_audio_chunk(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("WHISPER_MULTILINGUAL", "true")
    monkeypatch.setenv("WHISPER_LANGUAGE", "auto")
    video_path = tmp_path / "video.webm"
    audio_path = tmp_path / "audio.wav"
    video_path.write_bytes(b"video")
    audio_path.write_bytes(b"audio")
    captured = []

    class FakeModel:
        def transcribe(self, audio, **kwargs):
            captured.append((len(audio), kwargs))
            text = " Hindi" if len(captured) == 1 else " English"
            return (
                iter([SimpleNamespace(text=text, avg_logprob=-0.2)]),
                SimpleNamespace(
                    duration=len(audio) / 16000,
                    language="hi" if len(captured) == 1 else "en",
                ),
            )

    monkeypatch.setattr(
        transcription,
        "extract_audio",
        lambda video_path, output_path: audio_path,
    )
    monkeypatch.setattr(
        transcription.soundfile,
        "read",
        lambda *args, **kwargs: (
            np.zeros(16 * 16000, dtype=np.float32),
            16000,
        ),
    )
    monkeypatch.setattr(transcription, "_get_model", lambda: FakeModel())

    result = transcription.transcribe_video(video_path)

    assert result["text"] == "Hindi English"
    assert len(captured) == 2
    assert [length for length, _ in captured] == [8 * 16000, 8 * 16000]
    assert all("language" not in kwargs for _, kwargs in captured)
    assert result["duration_seconds"] == 16
    assert result["detected_languages"] == ["hi", "en"]


def test_transcript_selection_and_reevaluation_threshold():
    assert transcription.select_transcript("browser text", "whisper text") == (
        "whisper text",
        "whisper",
    )
    assert transcription.select_transcript(
        "Hindi mein diya gaya jawab",
        "unrelated repeated English words",
        confidence=0.4,
    ) == ("Hindi mein diya gaya jawab", "browser")
    assert transcription.select_transcript(
        "No transcript captured.",
        "unreliable Whisper output",
        confidence=0.4,
    ) == ("", "browser")
    assert not transcription.is_transcript_usable(
        "background in Python S12",
        source="browser",
        confidence=0.4,
    )
    assert transcription.is_transcript_usable(
        "A short answer",
        source="browser",
        confidence=0.8,
    )
    assert transcription.select_transcript(
        "browser text",
        "whisper text",
        confidence=0.8,
    ) == ("whisper text", "whisper")
    assert transcription.select_transcript("browser text", None) == (
        "browser text",
        "browser",
    )
    assert transcription.should_reevaluate_answer(
        "No transcript captured.",
        "A useful answer",
    )
    assert transcription.should_reevaluate_answer(
        "one two three four",
        "one two four",
    )
    assert not transcription.should_reevaluate_answer(
        "This is a useful answer.",
        "This is a useful answer",
    )
    assert transcription.select_transcript(
        "browser remains selected",
        "late whisper result",
        source="browser",
    ) == ("browser remains selected", "browser")


def test_word_similarity_is_word_level_and_punctuation_independent():
    assert transcription.word_similarity("A useful answer.", "A useful answer") == 1.0
    assert transcription.word_similarity("one two three four", "one two four") == 0.75


def test_manual_wer_comparison_counts_substitution_insertion_and_deletion():
    reference = normalize("one two three")
    hypothesis = normalize("one too three four")
    wer, substitutions, insertions, deletions = calculate_wer(
        reference,
        hypothesis,
    )

    assert wer == 2 / 3
    assert substitutions == 1
    assert insertions == 1
    assert deletions == 0
