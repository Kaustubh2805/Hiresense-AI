from app.services.nlp_features import (
    extract_nlp_features,
)


def test_nlp_feature_extraction():
    transcript = (
        "I worked on a backend project. "
        "Haan, mujhe APIs build karna tha. "
        "Basically I improved the performance."
    )

    features = extract_nlp_features(transcript)

    print("\nNLP FEATURES")
    print("Word count:", features["word_count"])
    print(
        "Unique words:",
        features["unique_word_count"],
    )
    print(
        "Vocabulary diversity:",
        features["vocabulary_diversity"],
    )
    print(
        "Average word length:",
        features["average_word_length"],
    )
    print(
        "Sentence count:",
        features["sentence_count"],
    )
    print(
        "Average sentence length:",
        features["average_sentence_length"],
    )
    print(
        "Hindi word count:",
        features["hindi_word_count"],
    )
    print(
        "Hindi words:",
        features["hindi_words"],
    )
    print(
        "Hesitation words:",
        features["hesitation_words"],
    )

    assert features["word_count"] > 0
    assert features["unique_word_count"] > 0
    assert features["vocabulary_diversity"] > 0
    assert features["sentence_count"] == 3

    assert features["hindi_word_count"] >= 2
    assert "haan" in features["hindi_words"]
    assert "mujhe" in features["hindi_words"]
    assert "karna" in features["hindi_words"]

    assert features["hesitation_word_count"] == 0


def test_hinglish_metrics_count_words_switches_and_technical_terms():
    features = extract_nlp_features(
        "I have completed my project aur maine Python use kiya hai."
    )

    assert features["word_count"] == 11
    assert features["hindi_word_count"] == 4
    assert features["english_word_count"] == 7
    assert features["hindi_word_ratio"] == 4 / 11
    assert features["english_word_ratio"] == 7 / 11
    assert features["dominant_language"] == "english"
    assert features["mixed_language"] is True
    assert features["code_switching_count"] == 3
    assert "python" in features["english_words"]
    assert "maine" in features["hindi_words"]
    assert {"word": "maine", "language": "hindi"} in features[
        "word_language_identification"
    ]
    assert features["language_switching_examples"] == [
        "project -> aur",
        "maine -> python",
        "use -> kiya",
    ]


def test_common_english_words_are_not_hindi():
    features = extract_nlp_features(
        "To is in it can the was have are the main problem."
    )

    assert features["hindi_word_count"] == 0
    assert features["english_word_count"] == features["word_count"]
    assert "main" in features["english_words"]
    assert "problem" in features["english_words"]


def test_devanagari_words_are_detected_alongside_english():
    features = extract_nlp_features(
        "मैं Python सीख रहा हूँ और project को improve कर रहा हूँ."
    )

    assert features["mixed_language"] is True
    assert features["hindi_word_count"] > 0
    assert features["english_word_count"] == 3
    assert "मैं" in features["hindi_words"]
    assert "python" in features["english_words"]


def test_romanized_hindi_words_detect_switches_in_bilingual_answer():
    features = extract_nlp_features(
        "mai backend mein kaam kar raha hu, and then I deployed it."
    )

    assert features["hindi_word_count"] == 6
    assert features["english_word_count"] == 6
    assert features["mixed_language"] is True
    assert features["code_switching_count"] == 3
    assert features["language_switching_examples"] == [
        "mai -> backend",
        "backend -> mein",
        "hu -> and",
    ]