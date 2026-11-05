from app.services.audio_features import (
    detect_filler_words,
    score_filler_usage,
)


def run_test(
    transcript: str,
):
    analysis = detect_filler_words(
        transcript
    )

    score = score_filler_usage(
        filler_word_count=(
            analysis["filler_word_count"]
        ),
        word_count=analysis["word_count"],
    )

    print()
    print("FILLER-WORD ANALYSIS")
    print("=" * 80)

    print(
        f"Transcript:             "
        f"{transcript!r}"
    )

    print(
        f"Word count:             "
        f"{analysis['word_count']}"
    )

    print(
        f"Filler count:           "
        f"{analysis['filler_word_count']}"
    )

    print(
        f"Filler density:         "
        f"{analysis['filler_density_per_100_words']:.2f}"
        f" per 100 words"
    )

    print(
        f"Detected fillers:       "
        f"{analysis['filler_words']}"
    )

    print(
        f"Filler score:           "
        f"{score:.2f}/10"
        if score is not None
        else
        "Filler score:           unavailable"
    )

    print("=" * 80)


def main():
    # ---------------------------------------------------------
    # Test 1: clean answer
    # ---------------------------------------------------------

    run_test(
        "I think this approach is useful because "
        "it reduces the complexity of the system."
    )

    # ---------------------------------------------------------
    # Test 2: answer containing fillers
    # ---------------------------------------------------------

    run_test(
        "Um, I think, you know, basically this "
        "approach is, um, kind of useful."
    )

    print()
    print("FILLER ANALYSIS SUCCESS")
    print()


if __name__ == "__main__":
    main()