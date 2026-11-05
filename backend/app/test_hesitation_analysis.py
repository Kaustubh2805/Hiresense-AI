from app.services.hesitation_analysis import detect_hesitation


def print_result(title: str, result: dict) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    for key, value in result.items():
        print(f"{key}: {value}")


def test_hesitation_analysis():
    clean = detect_hesitation(
        pause_count=1,
        total_pause_seconds=0.4,
        longest_pause_seconds=0.4,
        duration_seconds=20.0,
        filler_word_count=0,
    )

    print_result("CLEAN SPEECH", clean)

    assert clean["hesitation_count"] == 0
    assert clean["hesitation_score"] == 9.5
    assert clean["repeated_hesitation"] is False

    hesitant = detect_hesitation(
        pause_count=5,
        total_pause_seconds=7.0,
        longest_pause_seconds=1.4,
        duration_seconds=20.0,
        filler_word_count=4,
    )

    print_result("HESITANT SPEECH PATTERN", hesitant)

    assert hesitant["hesitation_count"] == 4
    assert hesitant["hesitation_score"] == 3.5
    assert hesitant["long_pause_count"] == 1
    assert hesitant["repeated_hesitation"] is True

    print()
    print("=" * 70)
    print("HESITATION ANALYSIS SUCCESS")
    print("=" * 70)