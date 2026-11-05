def clamp_score(score: float) -> float:
    """
    Keep a score inside the 1–10 range.
    """

    return round(
        max(
            1.0,
            min(10.0, score),
        ),
        2,
    )


def score_pace(
    words_per_minute: float | None,
) -> float | None:
    """
    Score speaking pace on a 1–10 scale.

    Approximate interview speaking range:
        120–160 WPM -> strongest score

    This is intentionally a soft scoring curve rather than
    a strict pass/fail threshold.
    """

    if words_per_minute is None:
        return None

    if words_per_minute < 60:
        score = 4.0

    elif words_per_minute < 90:
        score = 6.0

    elif words_per_minute < 110:
        score = 7.5

    elif words_per_minute <= 160:
        score = 10.0

    elif words_per_minute <= 180:
        score = 8.0

    elif words_per_minute <= 210:
        score = 6.5

    else:
        score = 4.0

    return clamp_score(score)


def score_pause_management(
    pause_count: int,
    total_pause_seconds: float,
    duration_seconds: float,
) -> float | None:
    """
    Score pause management on a 1–10 scale.

    The score considers:
    - number of meaningful pauses
    - percentage of the answer spent paused

    Short pauses are normal and are not treated as a problem.
    """

    if duration_seconds <= 0:
        return None

    pause_ratio = (
        total_pause_seconds / duration_seconds
    )

    if pause_ratio <= 0.10 and pause_count <= 3:
        score = 9.5

    elif pause_ratio <= 0.20 and pause_count <= 5:
        score = 8.0

    elif pause_ratio <= 0.30 and pause_count <= 7:
        score = 6.5

    elif pause_ratio <= 0.40:
        score = 5.0

    else:
        score = 3.5

    return clamp_score(score)


def score_fluency(
    speech_ratio: float,
    pause_count: int,
    duration_seconds: float,
) -> float | None:
    """
    Estimate speech fluency from continuous speech activity.

    This is an acoustic fluency proxy, not a linguistic fluency
    judgment.
    """

    if duration_seconds <= 0:
        return None

    if speech_ratio >= 0.85 and pause_count <= 2:
        score = 9.5

    elif speech_ratio >= 0.70 and pause_count <= 4:
        score = 8.0

    elif speech_ratio >= 0.55 and pause_count <= 6:
        score = 6.5

    elif speech_ratio >= 0.40:
        score = 5.0

    else:
        score = 3.5

    return clamp_score(score)


def score_vocal_energy(
    mean_rms: float,
) -> float:
    """
    Score relative vocal energy on a 1–10 scale.

    RMS depends on the microphone and recording environment,
    so this is a coarse proxy rather than an absolute loudness
    measurement.
    """

    if mean_rms < 0.02:
        score = 3.5

    elif mean_rms < 0.04:
        score = 5.0

    elif mean_rms < 0.06:
        score = 6.5

    elif mean_rms < 0.10:
        score = 8.0

    elif mean_rms < 0.16:
        score = 9.0

    else:
        score = 7.0

    return clamp_score(score)


def calculate_overall_audio_score(
    scores: list[float | None],
) -> float | None:
    """
    Calculate the overall audio score from available factor scores.

    Missing factors are ignored.
    """

    available_scores = [
        score
        for score in scores
        if score is not None
    ]

    if not available_scores:
        return None

    return clamp_score(
        sum(available_scores)
        / len(available_scores)
    )


def score_audio_features(
    features: dict,
) -> dict:
    """
    Convert extracted acoustic features into explainable
    1–10 communication scores.

    This function does not use an LLM or pretrained model.
    """

    pace_score = score_pace(
        features.get("words_per_minute")
    )

    pause_score = score_pause_management(
        pause_count=features.get("pause_count", 0),
        total_pause_seconds=features.get(
            "total_pause_seconds",
            0.0,
        ),
        duration_seconds=features.get(
            "duration_seconds",
            0.0,
        ),
    )

    fluency_score = score_fluency(
        speech_ratio=features.get(
            "speech_ratio",
            0.0,
        ),
        pause_count=features.get(
            "pause_count",
            0,
        ),
        duration_seconds=features.get(
            "duration_seconds",
            0.0,
        ),
    )

    vocal_energy_score = score_vocal_energy(
        mean_rms=features.get(
            "mean_rms",
            0.0,
        )
    )

    filler_score = features.get(
        "filler_word_score"
    )

    hesitation_score = features.get("hesitation_score")
    
    overall_score = calculate_overall_audio_score(
        [
            pace_score,
            pause_score,
            fluency_score,
            vocal_energy_score,
            filler_score,
        ]
    )

    return {
        "pace": pace_score,
        "pause_management": pause_score,
        "fluency": fluency_score,
        "vocal_energy": vocal_energy_score,
        "filler_word_score": filler_score,
        "overall_score": overall_score,
        "hesitation_score": hesitation_score,
    }