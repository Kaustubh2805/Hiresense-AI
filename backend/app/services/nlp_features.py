from __future__ import annotations

import re
from collections import Counter


# Common conversational Hindi/Hinglish words. The set is deliberately broader
# than a tiny dictionary so that Romanized Hinglish and Devanagari text can be
# recognized without misclassifying common English words such as "to" or "is".
HINDI_WORDS = {
    "haan",
    "han",
    "nahi",
    "nahin",
    "acha",
    "accha",
    "achha",
    "bas",
    "bahut",
    "bohot",
    "thoda",
    "thodi",
    "thode",
    "kyun",
    "kyunki",
    "kya",
    "kaise",
    "kaisa",
    "kaisi",
    "mera",
    "meri",
    "mere",
    "humara",
    "hamara",
    "humari",
    "hamari",
    "aap",
    "aapka",
    "aapki",
    "mujhe",
    "mujhse",
    "maine",
    "apna",
    "apne",
    "apni",
    "tum",
    "tumhara",
    "tumhari",
    "woh",
    "woh",
    "yeh",
    "yah",
    "jo",
    "jab",
    "tab",
    "phir",
    "lekin",
    "magar",
    "agar",
    "toh",
    "fir",
    "karna",
    "karta",
    "karti",
    "karte",
    "kiya",
    "kiye",
    "kiyun",
    "ki",
    "ko",
    "mein",
    "humne",
    "hume",
    "humein",
    "jisme",
    "jisse",
    "batao",
    "batana",
    "hoga",
    "hogi",
    "honge",
    "shuru",
    "se",
    "sab",
    "kuch",
    "saath",
    "karunga",
    "karungi",
    "karne",
    "kaam",
    "samajh",
    "samajhta",
    "samajhti",
    "samjha",
    "samjhi",
    "chahiye",
    "sakta",
    "sakti",
    "sakte",
    "hai",
    "hain",
    "tha",
    "thi",
    "raha",
    "rahi",
    "rahe",
    "gaya",
    "gayi",
    "wala",
    "wali",
    "wale",
    "acche",
    "achhe",
    "dikkat",
    "aur",
    "aurat",
    "aati",
    "aata",
    "aati",
    "bata",
    "batata",
    "kar",
    "karen",
    "karte",
    "kartey",
    "bhi",
    "behtar",
    "bura",
    "jaan",
    "dikhai",
    "samajh",
    "samajhkar",
    "mai",
    "hain",
    "hoon",
    "hun",
    "hu",
    "ho",
    "kyu",
    "kyunki",
    "kyon",
    "yahan",
    "wahan",
    "ka",
    "ke",
    "ki",
    "kisi",
    "kuchh",
    "koi",
    "kya",
    "mera",
    "meri",
    "mere",
    "ham",
    "hum",
    "unka",
    "unki",
    "unke",
    "aap",
    "aapne",
    "aapko",
    "aapke",
    "aapse",
    "tumne",
    "tumko",
    "tumhe",
    "tumse",
    "mujhko",
    "mujhko",
    "hume",
    "humein",
    "hoga",
    "hogi",
    "honge",
    "hote",
    "hoti",
    "hota",
    "kar",
    "karke",
    "karta",
    "karti",
    "karte",
    "kare",
    "karna",
    "karne",
    "karunga",
    "karungi",
    "kiya",
    "kiye",
    "gaya",
    "gayi",
    "gaye",
    "raha",
    "rahi",
    "rahe",
    "tha",
    "thi",
    "bana",
    "banaya",
    "banayi",
    "banaya",
    "hua",
    "hui",
    "hue",
    "diya",
    "liya",
    "chahiye",
    "sakta",
    "sakti",
    "sakte",
    "apna",
    "apni",
    "apne",
    "wala",
    "wali",
    "wale",
    "sabhi",
    "sabko",
    "sabse",
    "bas",
    "abhi",
    "phir",
    "fir",
    "toh",
    "lekin",
    "magar",
    "agar",
    "kyunki",
    "jab",
    "tab",
    "tak",
    "par",
    "pe",
    "se",
    "bhi",
    "aur",
    "bahut",
    "bohot",
    "thoda",
    "thodi",
    "thode",
    "accha",
    "achha",
    "acha",
    "nahi",
    "nahin",
    "haan",
    "han",
    "kaise",
    "kaisa",
    "kaisi",
    "kyun",
    "kyunki",
}

DEVANAGARI_WORDS = {
    "मैं",
    "मुझे",
    "मैंने",
    "हां",
    "नहीं",
    "अच्छा",
    "बास",
    "बहुत",
    "थोड़ा",
    "क्यों",
    "क्यूं",
    "क्या",
    "कैसे",
    "मेरा",
    "मेरी",
    "तुम",
    "वह",
    "यह",
    "जो",
    "जब",
    "तब",
    "फिर",
    "लेकिन",
    "अगर",
    "तो",
    "करना",
    "किया",
    "करें",
    "किया",
    "है",
    "हैं",
    "था",
    "थी",
    "रहा",
    "रही",
    "गया",
    "गयी",
    "को",
    "में",
    "से",
    "साथ",
    "कुछ",
    "सब",
    "प्रॉब्लम",
    "समस्या",
    "अपना",
    "अपने",
    "अपनी",
    "और",
    "अच्छे",
    "सिर्फ",
    "सीख",
    "सीखा",
    "देना",
    "दिया",
    "लिया",
    "पढ़ा",
    "काफी",
    "अलगे",
    "कम",
    "ज्यादा",
}


def _normalize_token(token: str) -> str:
    if not token:
        return ""
    normalized = (
        token.strip()
        .lower()
        .replace("’", "'")
        .replace("`", "'")
    )
    return re.sub(
        r"^[^A-Za-z\u0900-\u097F]+|[^A-Za-z\u0900-\u097F]+$",
        "",
        normalized,
    )


ENGLISH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "but",
    "by",
    "can",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "she",
    "that",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "about",
    "because",
    "through",
    "into",
    "like",
    "just",
    "also",
    "very",
    "more",
    "most",
    "some",
    "such",
    "than",
    "then",
    "these",
    "those",
    "before",
    "after",
    "under",
    "over",
    "again",
    "how",
    "should",
    "could",
    "would",
    "maybe",
    "actually",
    "basically",
    "practically",
    "simply",
    "problem",
}

TECHNICAL_WORDS = {
    "python",
    "django",
    "flask",
    "react",
    "next",
    "node",
    "javascript",
    "typescript",
    "java",
    "sql",
    "postgres",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "api",
    "apis",
    "rest",
    "graphql",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "ci",
    "cd",
    "devops",
    "ml",
    "ai",
    "machine",
    "learning",
    "data",
    "model",
    "backend",
    "frontend",
    "ui",
    "ux",
    "backend",
    "microservices",
    "nosql",
    "excel",
    "powerbi",
    "tableau",
    "terraform",
    "spark",
    "pandas",
    "numpy",
    "tensorflow",
    "pytorch",
    "linux",
    "git",
    "github",
    "jira",
    "agile",
    "scrum",
    "algorithm",
    "algorithms",
    "systemdesign",
    "design",
    "architecture",
    "database",
    "management",
    "deployment",
    "production",
    "testing",
    "automation",
    "sdlc",
    "etl",
    "etl",
    "html",
    "css",
    "json",
    "xml",
    "yaml",
    "api",
}


# Words that often indicate conversational hesitation.
HESITATION_WORDS = {
    "um",
    "umm",
    "uh",
    "uhh",
    "hmm",
    "hmmm",
}


def _is_devanagari_word(word: str) -> bool:
    return bool(re.search(r"[\u0900-\u097F]", word))


def _is_english_word(word: str) -> bool:
    normalized = _normalize_token(word)
    if not normalized:
        return False
    if _is_devanagari_word(normalized):
        return False
    if normalized in HINDI_WORDS or normalized in DEVANAGARI_WORDS:
        return False
    if normalized in ENGLISH_STOPWORDS or normalized in TECHNICAL_WORDS:
        return True
    return bool(re.fullmatch(r"[a-z]+(?:'[a-z]+)?", normalized))


def _is_hindi_word(word: str) -> bool:
    normalized = _normalize_token(word)
    if not normalized:
        return False
    if normalized in ENGLISH_STOPWORDS or normalized in TECHNICAL_WORDS:
        return False
    if _is_devanagari_word(normalized):
        return True
    return normalized in HINDI_WORDS or normalized in DEVANAGARI_WORDS


def tokenize_words(text: str) -> list[str]:
    """
    Convert transcript text into normalized word tokens.
    """
    if not text:
        return []

    tokens = re.findall(
        r"[A-Za-z\u0900-\u097F]+(?:['’][A-Za-z\u0900-\u097F]+)?",
        text.lower(),
    )
    return [_normalize_token(token) for token in tokens if _normalize_token(token)]


def split_sentences(text: str) -> list[str]:
    """
    Split transcript into simple sentence-like units.

    This is intentionally lightweight. Web Speech transcripts
    frequently do not contain perfect punctuation.
    """
    if not text or not text.strip():
        return []

    sentences = re.split(r"[.!?]+", text)

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def calculate_vocabulary_features(
    words: list[str],
) -> dict:
    """
    Calculate measurable vocabulary characteristics.
    """
    word_count = len(words)

    if word_count == 0:
        return {
            "word_count": 0,
            "unique_word_count": 0,
            "vocabulary_diversity": 0.0,
            "average_word_length": 0.0,
            "repeated_word_count": 0,
            "repetition_ratio": 0.0,
        }

    counts = Counter(words)

    unique_word_count = len(counts)

    vocabulary_diversity = unique_word_count / word_count

    average_word_length = sum(len(word) for word in words) / word_count

    repeated_word_count = sum(
        count - 1
        for count in counts.values()
        if count > 1
    )

    repetition_ratio = repeated_word_count / word_count

    return {
        "word_count": word_count,
        "unique_word_count": unique_word_count,
        "vocabulary_diversity": vocabulary_diversity,
        "average_word_length": average_word_length,
        "repeated_word_count": repeated_word_count,
        "repetition_ratio": repetition_ratio,
    }


def calculate_sentence_features(
    text: str,
    words: list[str],
) -> dict:
    """
    Calculate sentence-level communication features.
    """
    sentences = split_sentences(text)

    sentence_count = len(sentences)

    if sentence_count == 0:
        average_sentence_length = 0.0
    else:
        average_sentence_length = len(words) / sentence_count

    long_sentence_count = 0

    for sentence in sentences:
        sentence_words = tokenize_words(sentence)

        if len(sentence_words) >= 30:
            long_sentence_count += 1

    return {
        "sentence_count": sentence_count,
        "average_sentence_length": average_sentence_length,
        "long_sentence_count": long_sentence_count,
        "punctuation_missing": (
            len(words) > 25 and not re.search(r"[.!?]", text)
        ),
    }


def detect_hindi_words(
    words: list[str],
) -> dict:
    """
    Detect a conservative set of Hindi/Hinglish words appearing in the
    transcript while avoiding common English stop words and technical terms.
    """
    hindi_counts = Counter()
    english_counts = Counter()
    classified_sequence: list[str] = []
    word_language_identification: list[dict[str, str]] = []
    code_switches: list[str] = []

    previous_classified_word = None
    previous_classified_label = None

    for word in words:
        normalized = _normalize_token(word)
        if not normalized:
            continue

        if _is_hindi_word(normalized):
            hindi_counts[normalized] += 1
            label = "hindi"
        elif _is_english_word(normalized):
            english_counts[normalized] += 1
            label = "english"
        else:
            label = "unknown"

        word_language_identification.append(
            {"word": normalized, "language": label}
        )

        if label in {"hindi", "english"}:
            classified_sequence.append(label)
            if (
                previous_classified_label is not None
                and previous_classified_label != label
                and previous_classified_word is not None
            ):
                code_switches.append(
                    f"{previous_classified_word} -> {normalized}"
                )
            previous_classified_word = normalized
            previous_classified_label = label

    total_classified = len(classified_sequence)
    hindi_word_count = sum(hindi_counts.values())
    english_word_count = sum(english_counts.values())

    if total_classified:
        hindi_word_ratio = hindi_word_count / total_classified
        english_word_ratio = english_word_count / total_classified
    else:
        hindi_word_ratio = 0.0
        english_word_ratio = 0.0

    code_switching_count = sum(
        1
        for index in range(1, len(classified_sequence))
        if classified_sequence[index - 1] != classified_sequence[index]
    )

    dominant_language = "unknown"
    if hindi_word_count and english_word_count:
        dominant_language = (
            "hindi" if hindi_word_count >= english_word_count else "english"
        )
    elif hindi_word_count:
        dominant_language = "hindi"
    elif english_word_count:
        dominant_language = "english"

    return {
        "hindi_word_count": hindi_word_count,
        "hindi_word_ratio": hindi_word_ratio,
        "english_word_count": english_word_count,
        "english_word_ratio": english_word_ratio,
        "code_switching_count": code_switching_count,
        "code_switching_ratio": (
            code_switching_count / max(total_classified - 1, 1)
            if total_classified > 1
            else 0.0
        ),
        "dominant_language": dominant_language,
        "mixed_language": hindi_word_count > 0 and english_word_count > 0,
        "hindi_words": dict(hindi_counts),
        "detected_hindi_words": dict(hindi_counts),
        "english_words": dict(english_counts),
        "detected_english_words": dict(english_counts),
        "word_language_identification": word_language_identification,
        "language_switching_examples": code_switches,
        "language_switching_count": len(code_switches),
    }


def detect_hesitation_words(
    words: list[str],
) -> dict:
    """
    Detect explicit hesitation words in the transcript.
    """
    hesitation_words = [
        word for word in words if word in HESITATION_WORDS
    ]

    counts = Counter(hesitation_words)

    return {
        "hesitation_word_count": len(hesitation_words),
        "hesitation_words": dict(counts),
    }


def extract_nlp_features(
    transcript_text: str,
) -> dict:
    """
    Extract explainable NLP/linguistic features from a transcript.

    This function does not assign a psychological or intelligence judgment.
    It measures observable language characteristics.
    """
    normalized_text = transcript_text.strip() if transcript_text else ""

    words = tokenize_words(normalized_text)

    vocabulary = calculate_vocabulary_features(words)
    sentence_features = calculate_sentence_features(normalized_text, words)
    language_features = detect_hindi_words(words)
    hesitation_features = detect_hesitation_words(words)

    return {
        "transcript_text": normalized_text,
        "word_count": vocabulary["word_count"],
        "unique_word_count": vocabulary["unique_word_count"],
        "vocabulary_diversity": vocabulary["vocabulary_diversity"],
        "average_word_length": vocabulary["average_word_length"],
        "repeated_word_count": vocabulary["repeated_word_count"],
        "repetition_ratio": vocabulary["repetition_ratio"],
        "sentence_count": sentence_features["sentence_count"],
        "average_sentence_length": sentence_features["average_sentence_length"],
        "long_sentence_count": sentence_features["long_sentence_count"],
        "punctuation_missing": sentence_features["punctuation_missing"],
        "hindi_word_count": language_features["hindi_word_count"],
        "hindi_word_ratio": language_features["hindi_word_ratio"],
        "hindi_words": language_features["hindi_words"],
        "english_word_count": language_features["english_word_count"],
        "english_word_ratio": language_features["english_word_ratio"],
        "english_words": language_features["english_words"],
        "detected_hindi_words": language_features["detected_hindi_words"],
        "detected_english_words": language_features["detected_english_words"],
        "word_language_identification": language_features[
            "word_language_identification"
        ],
        "code_switching_count": language_features["code_switching_count"],
        "code_switching_ratio": language_features["code_switching_ratio"],
        "dominant_language": language_features["dominant_language"],
        "mixed_language": language_features["mixed_language"],
        "language_switching_examples": language_features[
            "language_switching_examples"
        ],
        "language_switching_count": language_features["language_switching_count"],
        "hesitation_word_count": hesitation_features["hesitation_word_count"],
        "hesitation_words": hesitation_features["hesitation_words"],
    }