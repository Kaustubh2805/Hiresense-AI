from app.services.audio_scoring import score_audio_features


def test_audio_scoring():
    features = {
        "words_per_minute": 125.0,
        "pause_count": 2,
        "total_pause_seconds": 1.0,
        "duration_seconds": 10.0,
        "speech_ratio": 0.85,
        "mean_rms": 0.08,
        "filler_word_score": 8.0,
        "hesitation_score": 6.5,
    }

    scores = score_audio_features(features)

    print("\nAUDIO SCORES")
    print(f"Pace:              {scores['pace']}/10")
    print(f"Pause management:  {scores['pause_management']}/10")
    print(f"Fluency:           {scores['fluency']}/10")
    print(f"Vocal energy:      {scores['vocal_energy']}/10")
    print(f"Filler words:      {scores['filler_word_score']}/10")
    print(f"Hesitation:        {scores['hesitation_score']}/10")
    print(f"Overall:           {scores['overall_score']}/10")

    assert "pace" in scores
    assert "pause_management" in scores
    assert "fluency" in scores
    assert "vocal_energy" in scores
    assert "filler_word_score" in scores
    assert "hesitation_score" in scores
    assert "overall_score" in scores

    assert scores["hesitation_score"] == 6.5

    assert 1 <= scores["pace"] <= 10
    assert 1 <= scores["pause_management"] <= 10
    assert 1 <= scores["fluency"] <= 10
    assert 1 <= scores["vocal_energy"] <= 10
    assert 1 <= scores["filler_word_score"] <= 10
    assert 1 <= scores["hesitation_score"] <= 10
    assert 1 <= scores["overall_score"] <= 10