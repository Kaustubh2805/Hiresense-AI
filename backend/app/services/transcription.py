from __future__ import annotations

import os
import re
import tempfile
from functools import lru_cache
from math import exp
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import soundfile

from app.services.audio_extraction import extract_audio

_WHISPER_SAMPLE_RATE = 16000
_MULTILINGUAL_CHUNK_SECONDS = 8
WHISPER_CONFIDENCE_FALLBACK_THRESHOLD = 0.6


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def is_whisper_sync_enabled() -> bool:
    return os.getenv("WHISPER_SYNC", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_initial_prompt(
    role: str | None,
    skills: Iterable[str] | None,
    question: str | None,
) -> str:
    language_instruction = (
        "Transcribe Hindi and English as spoken; preserve both languages, "
        "do not translate."
    )
    skills_text = ", ".join(str(skill) for skill in (skills or []) if skill)
    role_part = f"Role: {role.strip()[:35]}" if role and role.strip() else ""
    skills_part = f"Skills: {skills_text[:55]}" if skills_text else ""
    question_part = (
        f"Question: {question.strip()[:95]}"
        if question and question.strip()
        else ""
    )
    context = " ".join(
        part for part in (role_part, skills_part, question_part) if part
    )
    return f"{language_instruction} {context}".strip()[:200]


def _normalize_language_code(language: object) -> str | None:
    if not isinstance(language, str) or not language.strip():
        return None
    return language.strip().lower().split("-", maxsplit=1)[0]


def _is_multilingual_enabled() -> bool:
    multilingual_flag = os.getenv(
        "WHISPER_MULTILINGUAL",
        "true",
    ).strip().lower()
    language = os.getenv("WHISPER_LANGUAGE", "").strip().lower()
    language_requires_multilingual = bool(language) and language not in {
        "en",
        "english",
    }
    return (
        multilingual_flag in {"1", "true", "yes", "on"}
        or language_requires_multilingual
    )


def _get_whisper_language() -> str | None:
    language = os.getenv("WHISPER_LANGUAGE")
    if language is None or not language.strip():
        return None if _is_multilingual_enabled() else "en"
    language = language.strip()
    if language.lower() in {"auto", "detect", "multilingual", "none"}:
        return None
    return language


def _get_selected_whisper_model() -> str:
    model_name = os.getenv("WHISPER_MODEL", "small.en")
    if _is_multilingual_enabled():
        return os.getenv("WHISPER_MODEL_MULTILINGUAL", "small")
    return model_name


@lru_cache(maxsize=1)
def _get_model():
    from faster_whisper import WhisperModel

    return WhisperModel(
        _get_selected_whisper_model(),
        device="cpu",
        compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
        cpu_threads=_env_int("WHISPER_CPU_THREADS", 4),
        download_root="/models",
    )


def _transcribe_audio(
    model: Any,
    audio: np.ndarray,
    whisper_kwargs: dict[str, Any],
    language: str | None,
) -> tuple[list[Any], float, list[str]]:
    """Auto-detect language independently in short multilingual audio windows."""
    if language is not None:
        segments, info = model.transcribe(
            audio,
            language=language,
            **whisper_kwargs,
        )
        duration = float(
            getattr(info, "duration", 0.0) or len(audio) / _WHISPER_SAMPLE_RATE
        )
        detected_language = _normalize_language_code(
            getattr(info, "language", None)
        ) or _normalize_language_code(language)
        return (
            list(segments),
            duration,
            [detected_language] if detected_language else [],
        )

    chunk_samples = _WHISPER_SAMPLE_RATE * _MULTILINGUAL_CHUNK_SECONDS
    if len(audio) <= chunk_samples:
        segments, info = model.transcribe(audio, **whisper_kwargs)
        duration = float(
            getattr(info, "duration", 0.0) or len(audio) / _WHISPER_SAMPLE_RATE
        )
        detected_language = _normalize_language_code(
            getattr(info, "language", None)
        )
        return (
            list(segments),
            duration,
            [detected_language] if detected_language else [],
        )

    all_segments = []
    duration_seconds = 0.0
    detected_languages: list[str] = []
    for start in range(0, len(audio), chunk_samples):
        chunk = audio[start : start + chunk_samples]
        chunk_segments, info = model.transcribe(
            chunk,
            **whisper_kwargs,
        )
        all_segments.extend(chunk_segments)
        duration_seconds += float(
            getattr(info, "duration", 0.0) or len(chunk) / _WHISPER_SAMPLE_RATE
        )
        detected_language = _normalize_language_code(
            getattr(info, "language", None)
        )
        if detected_language and detected_language not in detected_languages:
            detected_languages.append(detected_language)

    return all_segments, duration_seconds, detected_languages


def transcribe_video(
    video_path: str | Path,
    *,
    role: str = "",
    skills: Iterable[str] | None = None,
    question: str = "",
) -> dict:
    with tempfile.TemporaryDirectory(prefix="hiresense_whisper_") as directory:
        audio_path = extract_audio(
            video_path=video_path,
            output_path=Path(directory) / "audio.wav",
        )
        audio, sample_rate = soundfile.read(
            str(audio_path),
            dtype="float32",
            always_2d=False,
        )
        if sample_rate != _WHISPER_SAMPLE_RATE:
            raise ValueError(
                f"Extracted audio must be 16000 Hz, got {sample_rate} Hz."
            )
        if audio.ndim == 2:
            audio = audio.mean(axis=1, dtype=np.float32)
        if audio.size == 0:
            raise ValueError("Extracted audio contains no samples.")
        model = _get_model()
        whisper_kwargs = {
            "beam_size": 5,
            "vad_filter": True,
            "vad_parameters": {"min_silence_duration_ms": 500},
            "condition_on_previous_text": False,
            "temperature": 0,
            "no_speech_threshold": 0.6,
            "log_prob_threshold": -1.0,
            "compression_ratio_threshold": 2.4,
            "initial_prompt": build_initial_prompt(role, skills, question),
        }
        language = _get_whisper_language()
        segment_list, duration_seconds, detected_languages = _transcribe_audio(
            model,
            audio,
            whisper_kwargs,
            language,
        )

    text = " ".join(
        segment.text.strip()
        for segment in segment_list
        if segment.text and segment.text.strip()
    )
    text = re.sub(r"\s+", " ", text).strip()
    probabilities = [
        float(segment.avg_logprob)
        for segment in segment_list
        if getattr(segment, "avg_logprob", None) is not None
    ]
    average_log_probability = (
        sum(probabilities) / len(probabilities)
        if probabilities
        else None
    )
    return {
        "text": text,
        "average_log_probability": average_log_probability,
        "confidence": (
            exp(average_log_probability)
            if average_log_probability is not None
            else None
        ),
        "duration_seconds": duration_seconds,
        "model": _get_selected_whisper_model(),
        "detected_languages": detected_languages,
    }


def word_similarity(first: str | None, second: str | None) -> float:
    first_words = re.findall(r"[a-z0-9']+", (first or "").lower())
    second_words = re.findall(r"[a-z0-9']+", (second or "").lower())
    if not first_words and not second_words:
        return 1.0
    if not first_words or not second_words:
        return 0.0

    previous = list(range(len(second_words) + 1))
    for row, first_word in enumerate(first_words, start=1):
        current = [row]
        for column, second_word in enumerate(second_words, start=1):
            current.append(
                min(
                    current[column - 1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (first_word != second_word),
                )
            )
        previous = current
    return max(0.0, 1.0 - previous[-1] / max(len(first_words), len(second_words)))


def is_placeholder_transcript(text: str | None) -> bool:
    normalized = re.sub(r"[^a-z ]", "", (text or "").lower()).strip()
    return not normalized or normalized in {
        "no transcript captured",
        "no transcript captured no transcript captured",
    }


def is_transcript_usable(
    text: str | None,
    *,
    source: str,
    confidence: float | None,
) -> bool:
    if is_placeholder_transcript(text):
        return False
    return not (
        source == "browser"
        and confidence is not None
        and confidence < WHISPER_CONFIDENCE_FALLBACK_THRESHOLD
        and len((text or "").split()) < 5
    )


def select_transcript(
    browser_text: str | None,
    whisper_text: str | None,
    source: str | None = None,
    confidence: float | None = None,
) -> tuple[str, str]:
    if source == "browser":
        return (browser_text or "").strip(), "browser"
    if whisper_text and whisper_text.strip():
        if (
            confidence is not None
            and confidence < WHISPER_CONFIDENCE_FALLBACK_THRESHOLD
        ):
            if not is_placeholder_transcript(browser_text):
                return browser_text.strip(), "browser"
            return "", "browser"
        return whisper_text.strip(), "whisper"
    return (browser_text or "").strip(), "browser"


def should_reevaluate_answer(browser_text: str | None, whisper_text: str | None) -> bool:
    if not whisper_text or not whisper_text.strip():
        return False
    return (
        is_placeholder_transcript(browser_text)
        or word_similarity(browser_text, whisper_text) < 0.85
    )
