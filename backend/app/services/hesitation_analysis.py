from __future__ import annotations


def detect_hesitation(
    *,
    pause_count: int,
    total_pause_seconds: float,
    longest_pause_seconds: float,
    duration_seconds: float,
    filler_word_count: int = 0,
) -> dict:
    """
    Detect observable hesitation patterns from already-extracted
    speech/pause features.

    This does NOT claim to measure a person's psychological state.
    It only measures observable speech-disruption patterns.
    """

    if duration_seconds <= 0:
        return {
            "hesitation_count": 0,
            "hesitation_score": 10.0,
            "long_pause_count": 0,
            "pause_ratio": 0.0,
            "repeated_hesitation": False,
        }

    pause_ratio = total_pause_seconds / duration_seconds

    # A pause >= 0.75 seconds is treated as a long pause.
    # We do not have individual pause durations here, so the
    # longest pause is used as an observable long-pause indicator.
    long_pause_count = 1 if longest_pause_seconds >= 0.75 else 0

    hesitation_count = 0

    # Repeated pauses are more relevant than one natural pause.
    if pause_count >= 3:
        hesitation_count += 1

    # A long pause is an observable hesitation indicator.
    if longest_pause_seconds >= 0.75:
        hesitation_count += 1

    # A high amount of silence relative to the answer duration
    # indicates more disrupted speech flow.
    if pause_ratio >= 0.30:
        hesitation_count += 1

    # Multiple fillers provide an additional verbal-disruption signal.
    if filler_word_count >= 3:
        hesitation_count += 1

    # Score the observable hesitation pattern on a 1-10 scale.
    if (
        hesitation_count == 0
        and pause_ratio <= 0.10
        and longest_pause_seconds < 0.75
    ):
        hesitation_score = 9.5
    elif hesitation_count <= 1 and pause_ratio <= 0.20:
        hesitation_score = 8.0
    elif hesitation_count <= 2 and pause_ratio <= 0.30:
        hesitation_score = 6.5
    elif hesitation_count <= 3 and pause_ratio <= 0.40:
        hesitation_score = 5.0
    else:
        hesitation_score = 3.5

    repeated_hesitation = (
        pause_count >= 3
        or filler_word_count >= 3
    )

    return {
        "hesitation_count": hesitation_count,
        "hesitation_score": hesitation_score,
        "long_pause_count": long_pause_count,
        "pause_ratio": pause_ratio,
        "repeated_hesitation": repeated_hesitation,
    }