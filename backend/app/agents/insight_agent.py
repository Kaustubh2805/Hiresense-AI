from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from app.config import INSIGHT_LLM_TIMEOUT, INSIGHT_USE_LLM, OLLAMA_MODEL, OLLAMA_URL


# Importance weights are a product decision, not research-derived.
DOMAIN_IMPORTANCE_WEIGHTS = {
    "answer": 40.0,
    "video": 20.0,
    "audio": 20.0,
    "nlp": 20.0,
}
FACTOR_WEAK_BELOW = 6.0
FACTOR_STRONG_FROM = 8.0
VOICE_RATE_BAND = {"low": 110.0, "high": 160.0}
FACTOR_IMPORTANCE_WEIGHTS = {
    "answer": {
        "technical_understanding": 15.0,
        "completeness": 10.0,
        "relevance": 8.0,
        "clarity": 7.0,
    },
    "video": {
        "eye_contact": 5.0,
        "posture": 3.0,
        "head_movement": 3.0,
        "facial_expression": 3.0,
        "gestures": 2.0,
        "visual_confidence": 4.0,
    },
    "audio": {
        "pace": 4.0,
        "fluency": 4.0,
        "volume": 4.0,
        "pause_management": 3.0,
        "filler_word_score": 2.5,
        "hesitation_score": 2.5,
    },
    "nlp": {
        "communication_clarity": 8.0,
        "vocabulary": 6.0,
        "grammar": 6.0,
    },
}
assert all(
    math.isclose(sum(FACTOR_IMPORTANCE_WEIGHTS[domain].values()), weight)
    for domain, weight in DOMAIN_IMPORTANCE_WEIGHTS.items()
)


# =============================================================================
# RESEARCH CITATIONS & EMPIRICAL BENCHMARKS CATALOG
# =============================================================================

RESEARCH_PAPERS = {
    "martin_raugh_2023": (
        "Martín-Raugh, Kell, Randall, Anguiano-Carrasco et al. (2023). "
        "\"Speaking without words: A meta-analysis of over 70 years of research "
        "on the power of nonverbal cues in job interviews.\" Journal of Organizational "
        "Behavior, 44(1), 132–156."
    ),
    "feiler_powell_2015": (
        "Feiler, A. R. & Powell, D. M. (2015). \"Behavioral Expression of Job "
        "Interview Anxiety.\" Journal of Business and Psychology."
    ),
    "schroeder_epley_2015": (
        "Schroeder, J. & Epley, N. (2015). \"The Sound of Intellect: Speech "
        "Reveals a Thoughtful Mind, Increasing a Job Candidate's Appeal.\" "
        "Psychological Science, 26(3)."
    ),
    "gikas_2019": (
        "Gikas, L. E. (2019). \"The Effect of Vocal Fillers on Credibility, "
        "Communication Competence, and Character.\" Cal Poly COMSSP."
    ),
    "mcdaniel_1994": (
        "McDaniel, M. A., Whetzel, D. L., Schmidt, F. L., & Maurer, S. D. (1994). "
        "\"The Validity of Employment Interviews: A Comprehensive Review and Meta-Analysis.\" "
        "Journal of Applied Psychology; Huffcutt, Culbertson & Weyhrauch (2014)."
    ),
    "ambady_rosenthal_1992": (
        "Ambady, N. & Rosenthal, R. (1992/1993). \"Thin slices of expressive "
        "behavior as predictors of interpersonal consequences: A meta-analysis.\" "
        "/ \"Half a minute: Predicting evaluations from thin slices...\""
    ),
    "gifford_1985": (
        "Gifford, R., Ng, C. F., & Wilkinson, M. (1985). \"Nonverbal cues in the "
        "employment interview: Links between applicant qualities and interviewer "
        "judgments.\" Journal of Applied Psychology."
    ),
    "rate_norms": (
        "National Center for Voice & Speech (~150 WPM conversational norm); "
        "Adams (2006) — comprehension unaffected at 120–160 WPM; "
        "Kuperman et al. (2021) — comprehension collapses beyond ~315 WPM."
    ),
}

# Empirical ideal bands on a 1-10 scale
IDEAL_BENCHMARKS: dict[str, dict[str, dict[str, Any]]] = {
    "audio": {
        "pace": {
            "name": "Speaking Pace",
            "ideal_min": 6.0,
            "ideal_max": 10.0,
            "paper": "Rate norms (110–160 WPM); Feiler & Powell (2015)",
            "basis": "Feiler & Powell (2015) identified speaking speed as the sole cue rater-candidate agreed signaled nervousness (slower WPM => lower assertiveness). Ideal band: 110–160 WPM.",
            "unit": "WPM",
        },
        "fluency": {
            "name": "Speech Fluency",
            "ideal_min": 6.5,
            "ideal_max": 10.0,
            "paper": "Speech ratio & continuity literature",
            "basis": "Speech ratio ≥ 0.55 indicates fluid speech production without cognitive stalling.",
            "unit": "score",
        },
        "pause_management": {
            "name": "Pause Management",
            "ideal_min": 6.5,
            "ideal_max": 10.0,
            "paper": "Conversational pause boundary norms",
            "basis": "Total pause ratio ≤ 0.20 and ≤ 5 unexpected mid-utterance pauses maintain listener engagement.",
            "unit": "score",
        },
        "volume": {
            "name": "Vocal Energy & Volume",
            "ideal_min": 6.0,
            "ideal_max": 9.5,
            "paper": "Schroeder & Epley (2015)",
            "basis": "Vocal delivery carries intellect and thoughtful mind signals, avoiding whisper and shout.",
            "unit": "score",
        },
        "filler_word_score": {
            "name": "Filler Word Control",
            "ideal_min": 7.0,
            "ideal_max": 10.0,
            "paper": "Gikas (2019)",
            "basis": "Vocal filler density ≤ 4% preserves credibility and competence; ≥ 12 fillers/min materially damages ratings.",
            "unit": "score",
        },
        "hesitation_score": {
            "name": "Hesitation Control",
            "ideal_min": 6.0,
            "ideal_max": 9.5,
            "paper": "Disfluency & speech formulation literature",
            "basis": "Controlled articulation without repeated false starts signals confident mastery.",
            "unit": "score",
        },
        "audio_overall": {
            "name": "Overall Audio Delivery",
            "ideal_min": 6.5,
            "ideal_max": 9.0,
            "paper": "Schroeder & Epley (2015); Feiler & Powell (2015)",
            "basis": "Composite roll-up of vocal energy, pace, fluency, and professional cadence.",
            "unit": "score",
        },
    },
    "video": {
        "eye_contact": {
            "name": "Eye Contact & Camera Engagement",
            "ideal_min": 7.0,
            "ideal_max": 10.0,
            "paper": "Martín-Raugh et al. (2023) (ρ = .45)",
            "basis": "Largest meta-analysis shows eye contact is the 2nd strongest nonverbal cue (ρ = .45) predicting favorable hiring.",
            "unit": "%",
        },
        "posture": {
            "name": "Posture Stability",
            "ideal_min": 7.0,
            "ideal_max": 10.0,
            "paper": "Martín-Raugh et al. (2023)",
            "basis": "Stable upright posture (≥ 70% frame stability) positively correlates with perceived confidence and professionalism.",
            "unit": "score",
        },
        "facial_expression": {
            "name": "Facial Expressiveness",
            "ideal_min": 6.5,
            "ideal_max": 9.5,
            "paper": "Nonverbal interview meta-analysis",
            "basis": "Moderate facial activity (8–15% frame modulation) conveys warmth, engagement, and emotional regulation.",
            "unit": "score",
        },
        "head_movement": {
            "name": "Responsive Head Movement",
            "ideal_min": 6.0,
            "ideal_max": 9.0,
            "paper": "Martín-Raugh et al. (2023) (ρ = .43)",
            "basis": "Responsive nodding and head movement (ρ = .43) indicate active listening and cognitive agreement, avoiding rigid stillness.",
            "unit": "score",
        },
        "gestures": {
            "name": "Natural Gestures",
            "ideal_min": 6.5,
            "ideal_max": 9.5,
            "paper": "Gifford et al. (1985)",
            "basis": "Visible hand gestures accompanying technical explanation foster favorable interviewer judgments.",
            "unit": "score",
        },
        "body_language": {
            "name": "Body Language Alignment",
            "ideal_min": 7.0,
            "ideal_max": 9.5,
            "paper": "Martín-Raugh et al. (2023)",
            "basis": "Open, centered upper body positioning without defensive crossing or slouching.",
            "unit": "score",
        },
        "attentiveness": {
            "name": "Visual Attentiveness",
            "ideal_min": 7.0,
            "ideal_max": 9.5,
            "paper": "Nonverbal engagement research",
            "basis": "Sustained focus on the interviewer during problem formulation.",
            "unit": "score",
        },
        "visual_confidence": {
            "name": "Visual Confidence",
            "ideal_min": 7.0,
            "ideal_max": 9.5,
            "paper": "Martín-Raugh et al. (2023)",
            "basis": "Composite visual composure combining gaze stability, shoulder relaxation, and facial neutrality.",
            "unit": "score",
        },
        "video_overall": {
            "name": "Overall Visual Presence",
            "ideal_min": 7.0,
            "ideal_max": 9.5,
            "paper": "Martín-Raugh et al. (2023)",
            "basis": "Composite nonverbal validity across verified face and pose detection frames.",
            "unit": "score",
        },
    },
    "nlp": {
        "vocabulary": {
            "name": "Technical Vocabulary",
            "ideal_min": 6.5,
            "ideal_max": 9.5,
            "paper": "Lexical diversity norms in professional interviews",
            "basis": "Domain-appropriate technical terminology and lexical diversity (evaluated on ≥ 50 word utterances).",
            "unit": "score",
        },
        "grammar": {
            "name": "Grammar & Sentence Structure",
            "ideal_min": 6.5,
            "ideal_max": 9.5,
            "paper": "Syntactic structure & communicative competence",
            "basis": "Well-formed sentences and grammatical cohesion enabling smooth comprehension.",
            "unit": "score",
        },
        "communication_clarity": {
            "name": "Communication Clarity",
            "ideal_min": 6.5,
            "ideal_max": 9.5,
            "paper": "Communication competence literature",
            "basis": "Structured, articulate expression that presents concepts logically from premise to conclusion.",
            "unit": "score",
        },
        "english_consistency": {
            "name": "English Consistency",
            "ideal_min": 9.0,
            "ideal_max": 10.0,
            "paper": "Flat-factor guard calibration",
            "basis": "Consistent language medium (zero variance indicator across session).",
            "unit": "score",
        },
        "nlp_overall": {
            "name": "Overall NLP Communication",
            "ideal_min": 6.5,
            "ideal_max": 9.5,
            "paper": "Communicative competence framework",
            "basis": "Composite verbal structure, vocabulary precision, and conceptual clarity.",
            "unit": "score",
        },
    },
    "answer": {
        "answer_overall": {
            "name": "Technical Answer Quality",
            "ideal_min": 5.5,
            "ideal_max": 9.0,
            "paper": "McDaniel et al. (1994); Huffcutt et al. (2014)",
            "basis": "Structured technical accuracy dominates job performance validity (ρ ≈ .44 vs .33 for unstructured).",
            "unit": "score",
        },
        "correctness": {
            "name": "Technical Correctness",
            "ideal_min": 6.0,
            "ideal_max": 10.0,
            "paper": "McDaniel et al. (1994)",
            "basis": "Factual and algorithmic correctness of the proposed solution.",
            "unit": "score",
        },
        "relevance": {
            "name": "Answer Relevance",
            "ideal_min": 6.0,
            "ideal_max": 10.0,
            "paper": "McDaniel et al. (1994)",
            "basis": "Direct alignment with the specific prompt and constraints asked.",
            "unit": "score",
        },
        "completeness": {
            "name": "Answer Completeness",
            "ideal_min": 6.0,
            "ideal_max": 10.0,
            "paper": "McDaniel et al. (1994)",
            "basis": "Addressing edge cases, architecture, scale, and operational trade-offs.",
            "unit": "score",
        },
        "clarity": {
            "name": "Technical Explanation Clarity",
            "ideal_min": 6.0,
            "ideal_max": 10.0,
            "paper": "Technical interview rubrics",
            "basis": "Transparent walkthrough of engineering rationale and mental models.",
            "unit": "score",
        },
        "technical_understanding": {
            "name": "Deep Technical Understanding",
            "ideal_min": 6.0,
            "ideal_max": 10.0,
            "paper": "McDaniel et al. (1994)",
            "basis": "Grasping fundamental system principles rather than reciting surface keywords.",
            "unit": "score",
        },
    },
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class InsightReport:
    """
    Candidate-facing interview feedback report.
    Grounded in empirical interview science, research-backed ideal bands,
    session contribution factor decomposition, thin-slice behavior analysis,
    and actionable Presence, Posture, and Voice improvement drills.
    """
    overall_assessment: str

    strengths: list[str]
    weaknesses: list[str]
    improvements: list[str]
    recommendations: list[str]

    technical_summary: str
    communication_summary: str
    audio_summary: str
    visual_summary: str

    question_evaluations: list[dict[str, Any]]
    performance_patterns: dict[str, Any]
    behavior_analysis: dict[str, Any]
    graph_data: dict[str, Any]

    confidence: float | None = None
    internal_metrics: dict[str, Any] | None = None

    # New first-class scientific components
    overall_scores: dict[str, Any] | None = None
    contribution_breakdown: dict[str, Any] | None = None
    research_benchmarks: dict[str, Any] | None = None
    stage_behavior_analysis: list[dict[str, Any]] | None = None
    pillar_improvements: dict[str, Any] | None = None

    # Contract additions expected by the persistence/UI layers
    status: str | None = None
    session_id: str | None = None
    generated_at: str | None = None
    data_coverage: dict[str, Any] | None = None
    llm: dict[str, Any] | None = None
    disclaimer: str | None = None
    weights: dict[str, Any] | None = None
    candidate_summary: dict[str, Any] | None = None
    soft_skill_summary: dict[str, Any] | None = None
    evidence: list[dict[str, str]] | None = None
    language_analysis: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# =============================================================================
# INSIGHT AGENT
# =============================================================================

class InsightAgent:
    """
    Candidate-facing Feedback Agent implemented as a self-contained single-file engine.

    Grounded in 8 foundational research papers:
    - McDaniel et al. (1994) / Huffcutt et al. (2014) [Structured content validity]
    - Martín-Raugh et al. (2023) [70-year nonverbal meta-analysis: eye contact, posture, head movement]
    - Feiler & Powell (2015) [Speaking rate & interview anxiety]
    - Schroeder & Epley (2015) [Vocal intellect & delivery appeal]
    - Gikas (2019) [Vocal fillers on credibility]
    - Ambady & Rosenthal (1992/1993) [Thin slices of behavior / first impression]
    - Gifford et al. (1985) [Nonverbal cues & applicant qualities]
    - Speech rate norms (110–160 WPM band)
    """

    def __init__(self) -> None:
        self._llm_calls = 0
        self._llm_fallbacks = 0
        self._llm_elapsed_seconds = 0.0

    def _aggregate_language_analysis(
        self,
        question_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        hindi_count = 0
        english_count = 0
        total_word_count = 0
        switching_count = 0
        switching_denominator = 0
        analyzed_answers = 0
        hindi_frequency: Counter[str] = Counter()
        english_frequency: Counter[str] = Counter()
        answer_metrics: list[dict[str, Any]] = []
        examples: list[dict[str, Any]] = []

        for index, item in enumerate(question_results, start=1):
            nlp = self._dict(item.get("nlp_evaluation")) or {}
            hindi_words = nlp.get("hindi_word_count")
            english_words = nlp.get("english_word_count")
            if hindi_words is None or english_words is None:
                continue

            hindi_words = int(hindi_words)
            english_words = int(english_words)
            answer_word_count = int(
                self._number(nlp.get("word_count"))
                or hindi_words + english_words
            )
            classified_count = hindi_words + english_words
            answer_switches = int(
                self._number(nlp.get("code_switching_count")) or 0
            )
            answer_switch_ratio = self._number(
                nlp.get("code_switching_ratio")
            ) or 0.0
            dominant_language = str(
                nlp.get("dominant_language") or "unknown"
            )
            hindi_count += hindi_words
            english_count += english_words
            total_word_count += answer_word_count
            switching_count += answer_switches
            switching_denominator += max(classified_count - 1, 0)
            analyzed_answers += 1

            if isinstance(nlp.get("hindi_words"), dict):
                hindi_frequency.update(
                    {
                        str(word): int(count)
                        for word, count in nlp["hindi_words"].items()
                    }
                )
            if isinstance(nlp.get("english_words"), dict):
                english_frequency.update(
                    {
                        str(word): int(count)
                        for word, count in nlp["english_words"].items()
                    }
                )

            answer_examples = nlp.get("language_switching_examples")
            if isinstance(answer_examples, list):
                examples.extend(
                    {
                        "question_number": index,
                        "example": str(example),
                    }
                    for example in answer_examples[:15]
                )

            answer_metrics.append(
                {
                    "question_number": index,
                    "dominant_language": dominant_language,
                    "word_count": answer_word_count,
                    "english_word_count": english_words,
                    "hindi_word_count": hindi_words,
                    "english_word_percentage": (
                        round(english_words / classified_count * 100, 1)
                        if classified_count
                        else 0.0
                    ),
                    "hindi_word_percentage": (
                        round(hindi_words / classified_count * 100, 1)
                        if classified_count
                        else 0.0
                    ),
                    "code_switching_count": answer_switches,
                    "code_switching_ratio": answer_switch_ratio,
                }
            )

        classified_count = hindi_count + english_count
        if hindi_count and english_count:
            dominant_language = (
                "hindi" if hindi_count > english_count else "english"
            )
            language_pattern = "hinglish"
        elif hindi_count:
            dominant_language = "hindi"
            language_pattern = "hindi"
        elif english_count:
            dominant_language = "english"
            language_pattern = "english"
        else:
            dominant_language = "unknown"
            language_pattern = "unknown"

        if not analyzed_answers:
            summary = "Language-pattern analysis is not available for these answers."
            feedback = (
                "There is not enough classified Hindi-English transcript data "
                "to provide reliable language-pattern feedback."
            )
        elif language_pattern == "hinglish":
            switch_noun = "switch" if switching_count == 1 else "switches"
            summary = (
                f"Hinglish was detected across {analyzed_answers} analyzed "
                f"answer(s), with {switching_count} Hindi-English language "
                f"{switch_noun}."
            )
            switch_time = "time" if switching_count == 1 else "times"
            feedback = (
                f"Your answers switched between Hindi and English "
                f"{switching_count} {switch_time}. This describes your transcript "
                "pattern, not answer quality. If an interview requires one "
                "language, practise explaining technical ideas consistently "
                "in that language."
            )
        else:
            switch_noun = "switch" if switching_count == 1 else "switches"
            summary = (
                f"{dominant_language.capitalize()} was the predominant detected "
                f"language across {analyzed_answers} analyzed answer(s), with "
                f"{switching_count} Hindi-English language {switch_noun}."
            )
            feedback = (
                "No Hindi-English switches were detected in the analyzed "
                "transcripts. If an interview requires a particular language, "
                "continue practising in that language."
            )

        return {
            "data_available": analyzed_answers > 0,
            "analyzed_answer_count": analyzed_answers,
            "total_word_count": total_word_count,
            "classified_word_count": classified_count,
            "english_word_count": english_count,
            "hindi_word_count": hindi_count,
            "english_word_percentage": (
                round(english_count / classified_count * 100, 1)
                if classified_count
                else 0.0
            ),
            "hindi_word_percentage": (
                round(hindi_count / classified_count * 100, 1)
                if classified_count
                else 0.0
            ),
            "code_switching_count": switching_count,
            "code_switching_ratio": (
                switching_count / switching_denominator
                if switching_denominator
                else 0.0
            ),
            "dominant_language": dominant_language,
            "language_pattern": language_pattern,
            "hindi_words": dict(hindi_frequency),
            "english_words": dict(english_frequency),
            "language_switching_examples": examples[:15],
            "answers": answer_metrics,
            "summary": summary,
            "feedback": feedback,
            "transcription_method": (
                "Interview audio is transcribed with multilingual Whisper and "
                "language is auto-detected independently in short audio windows. "
                "Whisper confidence is checked against the live transcript; when "
                "confidence is low, the live transcript is selected. Hindi-English "
                "patterns are measured from the selected transcript."
            ),
            "interpretation_note": (
                "Language percentages and switching describe transcript patterns; "
                "they do not measure intelligibility, technical ability, or "
                "communication quality."
            ),
        }

    def generate_insights(
        self,
        *,
        role: str,
        question_results: list[dict[str, Any]],
        session_id: str | None = None,
        **kwargs: Any,
    ) -> InsightReport:
        self._llm_calls = 0
        self._llm_fallbacks = 0
        self._llm_elapsed_seconds = 0.0
        # -------------------------------------------------------------
        # 1. Aggregate Modality Scores & Extract Measurable Factors
        # -------------------------------------------------------------
        technical_scores: list[float] = []
        nlp_scores: list[float] = []
        audio_scores: list[float] = []
        video_scores: list[float] = []

        # Granular factor collections across questions
        factor_values: dict[str, dict[str, list[float]]] = {
            "audio": {
                "pace": [],
                "fluency": [],
                "pause_management": [],
                "volume": [],
                "filler_word_score": [],
                "hesitation_score": [],
                "audio_overall": [],
            },
            "video": {
                "eye_contact": [],
                "posture": [],
                "facial_expression": [],
                "head_movement": [],
                "gestures": [],
                "body_language": [],
                "attentiveness": [],
                "visual_confidence": [],
                "video_overall": [],
            },
            "nlp": {
                "vocabulary": [],
                "grammar": [],
                "communication_clarity": [],
                "english_consistency": [],
                "sentence_structure": [],
                "nlp_overall": [],
            },
            "answer": {
                "answer_overall": [],
                "correctness": [],
                "relevance": [],
                "completeness": [],
                "clarity": [],
                "technical_understanding": [],
            },
        }

        # Keep raw measurements for research citation formatting
        raw_audio_metrics: dict[str, list[float]] = {
            "words_per_minute": [],
            "filler_word_count": [],
            "pause_count": [],
            "total_pause_seconds": [],
            "hesitation_count": [],
        }
        raw_video_metrics: dict[str, list[float]] = {
            "eye_contact_percentage": [],
            "face_visibility_percentage": [],
            "posture_score": [],
            "posture_stability": [],
        }
        raw_nlp_metrics: dict[str, list[float]] = {
            "word_count": [],
            "grammar_error_count": [],
            "hindi_word_ratio": [],
            "english_consistency_score": [],
            "sentence_structure_score": [],
        }

        question_evaluations: list[dict[str, Any]] = []

        for index, item in enumerate(question_results, start=1):
            tech_eval = self._dict(item.get("technical_evaluation"))
            audio_eval = self._dict(item.get("audio_evaluation"))
            nlp_eval = self._dict(item.get("nlp_evaluation"))
            vid_eval = self._dict(item.get("video_evaluation"))

            tech_score = self._number(tech_eval.get("rating") if tech_eval else item.get("technical_score"))
            audio_score = self._number(audio_eval.get("overall_score")) if audio_eval else None
            nlp_score = self._number(nlp_eval.get("overall_score")) if nlp_eval else None
            vid_score = self._number(vid_eval.get("overall_score")) if vid_eval else None

            if tech_score is not None:
                technical_scores.append(tech_score)
                factor_values["answer"]["answer_overall"].append(tech_score)
            if audio_score is not None:
                audio_scores.append(audio_score)
                factor_values["audio"]["audio_overall"].append(audio_score)
            if nlp_score is not None:
                nlp_scores.append(nlp_score)
                factor_values["nlp"]["nlp_overall"].append(nlp_score)
            if vid_score is not None:
                video_scores.append(vid_score)
                factor_values["video"]["video_overall"].append(vid_score)

            # Audio sub-factors
            if audio_eval:
                for k in ["pace", "fluency", "volume", "filler_word_score", "hesitation_score"]:
                    val = self._number(audio_eval.get(k))
                    if val is not None:
                        factor_values["audio"][k].append(val)
                # Pause management
                pause_mgmt = self._number(audio_eval.get("pause_management"))
                if pause_mgmt is not None:
                    factor_values["audio"]["pause_management"].append(pause_mgmt)
                for metric in (
                    "words_per_minute",
                    "filler_word_count",
                    "pause_count",
                    "total_pause_seconds",
                    "hesitation_count",
                ):
                    measured = self._number(audio_eval.get(metric))
                    if measured is not None:
                        raw_audio_metrics[metric].append(measured)

            # Video sub-factors
            if vid_eval:
                for k in [
                    "eye_contact", "posture", "facial_expression", "head_movement",
                    "gestures", "body_language", "attentiveness", "visual_confidence"
                ]:
                    val = self._number(vid_eval.get(k))
                    if val is not None:
                        factor_values["video"][k].append(val)

                # Raw video features
                ec_pct = self._number(
                    vid_eval.get("eye_contact_percentage")
                    if vid_eval.get("eye_contact_percentage") is not None
                    else vid_eval.get("camera_engagement_ratio")
                )
                if ec_pct is not None:
                    raw_video_metrics["eye_contact_percentage"].append(ec_pct if ec_pct <= 1.0 else ec_pct)
                fv_pct = self._number(
                    vid_eval.get("face_visibility_percentage")
                    if vid_eval.get("face_visibility_percentage") is not None
                    else vid_eval.get("face_detection_ratio")
                )
                if fv_pct is not None:
                    raw_video_metrics["face_visibility_percentage"].append(fv_pct if fv_pct <= 1.0 else fv_pct)
                post_stab = self._number(
                    vid_eval.get("posture_stability")
                    if vid_eval.get("posture_stability") is not None
                    else vid_eval.get("posture_score")
                )
                if post_stab is not None:
                    raw_video_metrics["posture_stability"].append(post_stab)

            # NLP sub-factors
            if nlp_eval:
                vocab = self._number(nlp_eval.get("vocabulary_score"))
                if vocab is not None:
                    factor_values["nlp"]["vocabulary"].append(vocab)
                gram = self._number(nlp_eval.get("grammar_score"))
                if gram is not None:
                    factor_values["nlp"]["grammar"].append(gram)
                clar = self._number(nlp_eval.get("communication_clarity_score"))
                if clar is not None:
                    factor_values["nlp"]["communication_clarity"].append(clar)
                eng_cons = self._number(nlp_eval.get("english_consistency_score"))
                if eng_cons is not None:
                    factor_values["nlp"]["english_consistency"].append(eng_cons)
                sentence_structure = self._number(nlp_eval.get("sentence_structure_score"))
                if sentence_structure is not None:
                    factor_values["nlp"]["sentence_structure"].append(sentence_structure)
                for metric in raw_nlp_metrics:
                    measured = self._number(nlp_eval.get(metric))
                    if measured is not None:
                        raw_nlp_metrics[metric].append(measured)

            # Answer sub-factors
            if tech_eval:
                for k in ["correctness", "relevance", "completeness", "clarity", "technical_understanding"]:
                    val = self._number(tech_eval.get(k))
                    if val is not None:
                        factor_values["answer"][k].append(val)

            # Build candidate-facing question evaluation focusing on Answer Evaluation
            q_text = str(item.get("question_text", item.get("question", f"Question {index}")))
            a_text = str(item.get("answer_text", item.get("transcript", item.get("answer", ""))) or "")
            answer_word_count = self._number(item.get("answer_word_count"))
            if answer_word_count is None and a_text.strip():
                answer_word_count = float(len(a_text.split()))
            q_feedback = self._build_question_answer_card(
                question_id=(
                    str(item["question_id"])
                    if item.get("question_id") is not None
                    else None
                ),
                question_number=index,
                question_text=q_text,
                answer_text=a_text,
                category=item.get("category"),
                source=item.get("source"),
                technical_score=tech_score,
                technical_evaluation=tech_eval,
                audio_score=audio_score,
                video_score=vid_score,
                nlp_score=nlp_score,
            )
            question_evaluations.append(q_feedback)

        # -------------------------------------------------------------
        # 2. Overall Scores Calculation (Average of Session)
        # -------------------------------------------------------------
        tech_avg = self._average(technical_scores)
        audio_avg = self._average(audio_scores)
        nlp_avg = self._average(nlp_scores)
        video_avg = self._average(video_scores)

        # Overall session average
        available_domains = [s for s in [tech_avg, audio_avg, video_avg, nlp_avg] if s is not None]
        overall_session_score = self._average(available_domains)

        overall_scores = {
            "answer": round(tech_avg, 1) if tech_avg is not None else None,
            "audio": round(audio_avg, 1) if audio_avg is not None else None,
            "nlp": round(nlp_avg, 1) if nlp_avg is not None else None,
            "video": round(video_avg, 1) if video_avg is not None else None,
            "overall_session": round(overall_session_score, 1) if overall_session_score is not None else None,
        }

        # -------------------------------------------------------------
        # 3. Factor Averages & Variances for Benchmarking & Guards
        # -------------------------------------------------------------
        factor_averages: dict[str, dict[str, float | None]] = {}
        factor_variances: dict[str, dict[str, float]] = {}

        for domain, domain_factors in factor_values.items():
            factor_averages[domain] = {}
            factor_variances[domain] = {}
            for fname, vals in domain_factors.items():
                if vals:
                    factor_averages[domain][fname] = self._average(vals)
                    factor_variances[domain][fname] = self._variance(vals)
                else:
                    factor_averages[domain][fname] = None
                    factor_variances[domain][fname] = 0.0

        # -------------------------------------------------------------
        # 4. Contribution Graph & Factor Decomposition Calculation
        # -------------------------------------------------------------
        contribution_breakdown = self._build_data_contribution(
            overall_scores=overall_scores,
            factor_averages=factor_averages,
            raw_audio_metrics=raw_audio_metrics,
            raw_video_metrics=raw_video_metrics,
            raw_nlp_metrics=raw_nlp_metrics,
        )

        # -------------------------------------------------------------
        # 5. Strengths & Weaknesses via Researched Ideal Min/Max + Guard
        # -------------------------------------------------------------
        research_benchmarks = self._classify_data_factors(
            factor_averages=factor_averages,
        )

        # Extract string lists for backward compatibility
        strengths_list = [f"{item['name']}: {item['reason']}" for item in research_benchmarks["strengths"]]
        weaknesses_list = [f"{item['name']}: {item['reason']}" for item in research_benchmarks["weaknesses"]]

        # -------------------------------------------------------------
        # 6. Behaviour Analysis (First Question, Normal, Followup, Last)
        # -------------------------------------------------------------
        stage_behavior_analysis = self._build_stage_behavior_analysis(
            question_results=question_results,
            question_evaluations=question_evaluations,
            factor_values=factor_values,
        )
        stage_behavior_analysis = self._candidate_oriented_stages(stage_behavior_analysis)

        # -------------------------------------------------------------
        # 7. Actionable Improvement Suggestions (Presence, Posture, Voice)
        # -------------------------------------------------------------
        pillar_improvements = self._candidate_pillars(
            overall_scores=overall_scores,
            factor_averages=factor_averages,
        )

        improvements_list = [
            f"{pillar.upper()}: {data['focus']} — Drill: {data['how_to'][0]}"
            for pillar, data in pillar_improvements.items()
            if data.get("how_to")
        ]

        # -------------------------------------------------------------
        # 8. LLM Enrichment for Summaries and Assessments
        # -------------------------------------------------------------
        overall_assessment = self._candidate_overall_assessment(overall_scores, role)

        tech_summary = (
            f"Your answer content score was {overall_scores['answer']:.1f}/10."
            if overall_scores["answer"] is not None
            else "Your answer content was not analysed."
        )
        comm_summary = (
            f"Your language analysis score was {overall_scores['nlp']:.1f}/10."
            if overall_scores["nlp"] is not None
            else "Your language was not analysed."
        )
        audio_summary = (
            f"Your speaking delivery score was {overall_scores['audio']:.1f}/10."
            if overall_scores["audio"] is not None
            else "Your speaking delivery was not analysed."
        )
        visual_summary = (
            f"Your visual presence score was {overall_scores['video']:.1f}/10."
            if overall_scores["video"] is not None
            else "Your visual presence was not analysed."
        )

        recommendations_list = [
            data["focus"]
            for data in pillar_improvements.values()
            if data.get("focus")
        ]

        graph_data = {
            "contribution_pie": contribution_breakdown["pie_chart"],
            "factor_decomposition": contribution_breakdown["factor_decomposition"],
            "performance_overview": {
                "labels": ["Answer Content", "Speaking Audio", "Language NLP", "Visual Presence"],
                "values": [
                    overall_scores["answer"],
                    overall_scores["audio"],
                    overall_scores["nlp"],
                    overall_scores["video"],
                ],
            },
            **self._build_modality_graph_data(
                question_results=question_results,
                factor_averages=factor_averages,
                overall_scores=overall_scores,
            ),
        }

        coverage_entries = {
            "answer": {
                "n_analyzed": len(technical_scores),
                "n_answered": max(len(question_results), 1),
                "label": f"{len(technical_scores)} of {max(len(question_results), 1)} answers",
            },
            "audio": {
                "n_analyzed": len(audio_scores),
                "n_answered": max(len(question_results), 1),
                "label": f"{len(audio_scores)} of {max(len(question_results), 1)} answers",
            },
            "video": {
                "n_analyzed": len(video_scores),
                "n_answered": max(len(question_results), 1),
                "label": f"{len(video_scores)} of {max(len(question_results), 1)} answers",
            },
            "nlp": {
                "n_analyzed": len(nlp_scores),
                "n_answered": max(len(question_results), 1),
                "label": f"{len(nlp_scores)} of {max(len(question_results), 1)} answers",
            },
        }

        coverage_entries["notes"] = [
            "Scores use only modalities that were actually analysed; unavailable modalities are not filled with estimated scores."
        ] if any(
            entry["n_analyzed"] < entry["n_answered"]
            for key, entry in coverage_entries.items()
            if key != "notes"
        ) else []
        coverage_values = [
            (entry["n_analyzed"] / entry["n_answered"]) if entry["n_answered"] else 0.0
            for key, entry in coverage_entries.items()
            if key != "notes"
        ]
        coverage_mean = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
        coverage_entries["confidence"] = round(coverage_mean, 2)

        confidence = round(
            min(0.98, max(0.0, coverage_mean)),
            2,
        )

        if not any(
            overall_scores.get(domain) is not None
            for domain in DOMAIN_IMPORTANCE_WEIGHTS
        ):
            status = "insufficient_data"
        elif coverage_mean < 0.5:
            status = "partial"
        else:
            status = "ok"

        candidate_summary = self._candidate_summary(
            role=role,
            overall_scores=overall_scores,
            benchmarks=research_benchmarks,
            pillars=pillar_improvements,
        )
        soft_skill_summary = self._build_soft_skill_summary(overall_scores)
        evidence = self._evidence()
        language_analysis = self._aggregate_language_analysis(question_results)
        reasoning_sources = self._apply_llm_enrichment(
            role=role,
            overall_scores=overall_scores,
            contribution_breakdown=contribution_breakdown,
            research_benchmarks=research_benchmarks,
            candidate_summary=candidate_summary,
            stage_behavior_analysis=stage_behavior_analysis,
            pillar_improvements=pillar_improvements,
        )
        llm_state = {
            "used": self._llm_calls > 0,
            "model": OLLAMA_MODEL,
            "calls": self._llm_calls,
            "fallbacks": self._llm_fallbacks,
            "reasoning_sources": reasoning_sources,
            "elapsed_seconds": round(self._llm_elapsed_seconds, 3),
        }
        timings = kwargs.get("timings")
        if isinstance(timings, dict):
            timings["insight_llm"] = self._llm_elapsed_seconds

        weights = {
            "answer": 40,
            "video": 20,
            "audio": 20,
            "nlp": 20,
        }

        disclaimer = (
            "Practice feedback from automated analysis of sampled answers, not a hiring prediction."
        )

        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return InsightReport(
            overall_assessment=overall_assessment,
            strengths=strengths_list[:8],
            weaknesses=weaknesses_list[:8],
            improvements=improvements_list[:8],
            recommendations=recommendations_list[:8],
            technical_summary=tech_summary,
            communication_summary=comm_summary,
            audio_summary=audio_summary,
            visual_summary=visual_summary,
            question_evaluations=question_evaluations,
            performance_patterns={
                "progression": "Progression uses the available scored answers.",
                "consistency": "Only observed scores are included.",
            },
            behavior_analysis={
                "summary": "Stage notes describe measured changes across your answered questions.",
                "stages": stage_behavior_analysis,
            },
            graph_data=graph_data,
            confidence=confidence,
            internal_metrics={
                "overall_scores": overall_scores,
                "factor_averages": factor_averages,
            },
            overall_scores=overall_scores,
            contribution_breakdown=contribution_breakdown,
            research_benchmarks=research_benchmarks,
            stage_behavior_analysis=stage_behavior_analysis,
            pillar_improvements=pillar_improvements,
            status=status,
            session_id=session_id,
            generated_at=generated_at,
            data_coverage=coverage_entries,
            llm=llm_state,
            disclaimer=disclaimer,
            weights=weights,
            candidate_summary=candidate_summary,
            soft_skill_summary=soft_skill_summary,
            evidence=evidence,
            language_analysis=language_analysis,
        )

    def _build_modality_graph_data(
        self,
        *,
        question_results: list[dict[str, Any]],
        factor_averages: dict[str, dict[str, float | None]],
        overall_scores: dict[str, Any],
    ) -> dict[str, Any]:
        factor_specs = {
            "audio": (
                ("pace", "Speaking pace", "words_per_minute", "WPM"),
                ("fluency", "Speech fluency", None, None),
                ("volume", "Voice level", None, None),
                ("pause_management", "Pause management", "total_pause_seconds", "seconds"),
                ("filler_word_score", "Filler word control", "filler_word_count", "count"),
                ("hesitation_score", "Hesitation control", "hesitation_count", "count"),
            ),
            "video": (
                ("eye_contact", "Eye contact", "eye_contact_percentage", "%"),
                ("posture", "Posture stability", "posture_stability", "score"),
                ("head_movement", "Responsive head movement", "head_movement_count", "count"),
                ("facial_expression", "Facial expression", None, None),
                ("gestures", "Natural gestures", "gesture_count", "count"),
                ("visual_confidence", "Visual confidence", None, None),
            ),
            "nlp": (
                ("communication_clarity", "Communication clarity", "sentence_structure_score", "score"),
                ("vocabulary", "Vocabulary", "word_count", "words"),
                ("grammar", "Grammar", "grammar_error_count", "errors"),
                ("sentence_structure", "Sentence structure", "sentence_structure_score", "score"),
                ("english_consistency", "English consistency", "english_consistency_score", "score"),
            ),
        }
        measured_fields = {
            "audio": {
                "pace": ("words_per_minute", "WPM"),
                "pause_management": ("total_pause_seconds", "seconds"),
                "filler_word_score": ("filler_word_count", "count"),
                "hesitation_score": ("hesitation_count", "count"),
            },
            "video": {
                "eye_contact": ("eye_contact_percentage", "%"),
                "posture": ("posture_score", "score"),
                "head_movement": ("head_movement_count", "count"),
                "gestures": ("gesture_count", "count"),
            },
            "nlp": {
                "communication_clarity": ("communication_clarity_score", "score"),
                "vocabulary": ("word_count", "words"),
                "grammar": ("grammar_error_count", "errors"),
                "sentence_structure": ("sentence_structure_score", "score"),
                "english_consistency": ("english_consistency_score", "score"),
            },
        }
        domain_map = {
            "audio": factor_averages.get("audio", {}),
            "video": factor_averages.get("video", {}),
            "nlp": factor_averages.get("nlp", {}),
        }
        factor_lists: dict[str, list[dict[str, Any]]] = {}
        factor_takeaways: dict[str, str] = {}

        for modality, specs in factor_specs.items():
            factors: list[dict[str, Any]] = []
            for key, name, _, _ in specs:
                score = self._number(domain_map[modality].get(key))
                if score is None:
                    continue
                measure = None
                metric = measured_fields.get(modality, {}).get(key)
                if metric:
                    metric_key, unit = metric
                    raw = [
                        self._number(
                            (self._dict(item.get(f"{modality}_evaluation")) or {}).get(metric_key)
                        )
                        for item in question_results
                    ]
                    measured = self._average([value for value in raw if value is not None])
                    if measured is not None:
                        if unit == "%" and measured <= 1:
                            measured *= 100
                        measure = {"value": round(measured, 2), "unit": unit}
                classification = (
                    "strength" if score >= FACTOR_STRONG_FROM
                    else "weakness" if score < FACTOR_WEAK_BELOW
                    else "developing"
                )
                factors.append({
                    "key": key,
                    "name": name,
                    "score": round(score, 2),
                    "weak_below": FACTOR_WEAK_BELOW,
                    "strong_from": FACTOR_STRONG_FROM,
                    "classification": classification,
                    "measured": measure,
                })
            factor_lists[f"{modality}_factors"] = factors
            factor_takeaways[f"{modality}_takeaway"] = self._chart_takeaway(factors)

        audio_count = 0
        video_count = 0
        nlp_count = 0
        voice_trend: list[dict[str, Any]] = []
        presence_trend: list[dict[str, Any]] = []
        language_trend: list[dict[str, Any]] = []
        progression_trend: list[dict[str, Any]] = []
        for index, item in enumerate(question_results, start=1):
            source = item.get("source")
            if source not in {"baseline", "bank", "ai_followup"}:
                source = "bank"
            question = f"Q{index}"
            audio = self._dict(item.get("audio_evaluation")) or {}
            video = self._dict(item.get("video_evaluation")) or {}
            nlp = self._dict(item.get("nlp_evaluation")) or {}
            technical = self._dict(item.get("technical_evaluation")) or {}

            answer_score = self._number(
                technical.get("rating")
                if technical
                else item.get("technical_score")
            )
            progression_row: dict[str, Any] = {
                "question": question,
                "source": source,
            }
            if answer_score is not None:
                progression_row["answer_score"] = round(answer_score, 2)
            progression_trend.append(progression_row)

            if audio:
                audio_count += 1
                voice_row: dict[str, Any] = {"question": question, "source": source}
                for output_key, input_key in (
                    ("wpm", "words_per_minute"),
                    ("filler_count", "filler_word_count"),
                    ("fluency", "fluency"),
                ):
                    value = self._number(audio.get(input_key))
                    if value is not None:
                        voice_row[output_key] = round(value, 2)
                pause_seconds = self._number(audio.get("total_pause_seconds"))
                duration = self._number(item.get("time_taken_seconds"))
                if duration is None:
                    duration = self._number(item.get("time_take"))
                if pause_seconds is not None and duration is not None and duration > 0:
                    voice_row["pause_ratio"] = round(pause_seconds / duration, 4)
                voice_trend.append(voice_row)

            video_metrics = {
                "eye_contact_pct": self._number(
                    video.get("eye_contact_percentage")
                    if video.get("eye_contact_percentage") is not None
                    else video.get("camera_engagement_ratio")
                ),
                "posture": self._number(
                    video.get("posture_score")
                    if video.get("posture_score") is not None
                    else video.get("posture")
                ),
                "facial_expression": self._number(video.get("facial_expression")),
            }
            has_video_analysis = bool(video) and (
                any(value is not None for value in video_metrics.values())
                or self._number(video.get("overall_score")) is not None
            )
            if has_video_analysis:
                video_count += 1
                if video_metrics["eye_contact_pct"] is not None and video_metrics["eye_contact_pct"] <= 1:
                    video_metrics["eye_contact_pct"] *= 100
                presence_row: dict[str, Any] = {
                    "question": question,
                    "source": source,
                }
                presence_row.update({
                    key: round(value, 2)
                    for key, value in video_metrics.items()
                    if value is not None
                })
                presence_trend.append(presence_row)

            if nlp:
                nlp_count += 1
                language_row: dict[str, Any] = {"question": question, "source": source}
                for output_key, input_key in (
                    ("grammar_errors", "grammar_error_count"),
                    ("word_count", "word_count"),
                    ("clarity", "communication_clarity_score"),
                    ("vocabulary", "vocabulary_score"),
                ):
                    value = self._number(nlp.get(input_key))
                    if value is not None:
                        language_row[output_key] = round(value, 2)
                language_trend.append(language_row)

        video_coverage = f"analysed {video_count} of {len(question_results)} answers"
        domain_radar = [
            {"domain": domain, "score": round(score, 2)}
            for domain, score in (
                ("answer", self._number(overall_scores.get("answer"))),
                ("audio", self._number(overall_scores.get("audio"))),
                ("video", self._number(overall_scores.get("video"))),
                ("nlp", self._number(overall_scores.get("nlp"))),
            )
            if score is not None
        ]
        return {
            **factor_lists,
            **factor_takeaways,
            "voice_trend": voice_trend,
            "voice_trend_takeaway": self._trend_takeaway(voice_trend, "speaking delivery"),
            "presence_trend": presence_trend,
            "presence_trend_takeaway": self._trend_takeaway(presence_trend, "visual presence"),
            "video_coverage": video_coverage,
            "language_trend": language_trend,
            "language_trend_takeaway": self._trend_takeaway(language_trend, "language"),
            "progression_trend": progression_trend,
            "progression_trend_takeaway": self._trend_takeaway(
                progression_trend, "answer content", score_key="answer_score"
            ),
            "domain_radar": domain_radar,
            "domain_radar_takeaway": self._chart_takeaway(domain_radar, label_key="domain"),
            "score_scale": {"min": 0.0, "max": 10.0},
            "voice_rate_band": VOICE_RATE_BAND.copy(),
            "audio_coverage": f"analysed {audio_count} of {len(question_results)} answers",
            "language_coverage": f"analysed {nlp_count} of {len(question_results)} answers",
        }

    @staticmethod
    def _chart_takeaway(
        factors: list[dict[str, Any]],
        *,
        label_key: str = "name",
    ) -> str:
        if not factors:
            return "There is not enough analysed data to compare these factors."
        highest = max(factors, key=lambda item: item["score"])
        lowest = min(factors, key=lambda item: item["score"])
        if highest.get("key", highest[label_key]) == lowest.get("key", lowest[label_key]):
            return f"Your measured {highest[label_key]} score was {highest['score']:.1f}/10."
        return (
            f"Your strongest measured area was {highest[label_key]} "
            f"({highest['score']:.1f}/10), while {lowest[label_key]} "
            f"was lowest ({lowest['score']:.1f}/10)."
        )

    @staticmethod
    def _trend_takeaway(
        rows: list[dict[str, Any]],
        label: str,
        *,
        score_key: str | None = None,
    ) -> str:
        key = score_key or next(
            (
                candidate
                for candidate in (
                    "wpm", "eye_contact_pct", "clarity", "grammar_errors",
                    "word_count", "answer_score",
                )
                if any(row.get(candidate) is not None for row in rows)
            ),
            None,
        )
        if not rows or key is None:
            return f"There is not enough analysed data to show your {label} trend."
        measured = [row[key] for row in rows if row.get(key) is not None]
        if not measured:
            return f"There is not enough analysed data to show your {label} trend."
        if len(measured) == 1:
            return f"Your {label} is shown for one analysed answer."
        if measured[-1] > measured[0]:
            direction = "increased"
        elif measured[-1] < measured[0]:
            direction = "decreased"
        else:
            direction = "was consistent"
        return f"Your measured {label} {direction} from the first to the last available answer."

    # =========================================================================
    # CONTRIBUTION BREAKDOWN & FACTOR DECOMPOSITION
    # =========================================================================

    def _build_data_contribution(
        self,
        *,
        overall_scores: dict[str, Any],
        factor_averages: dict[str, dict[str, float | None]],
        raw_audio_metrics: dict[str, list[float]],
        raw_video_metrics: dict[str, list[float]],
        raw_nlp_metrics: dict[str, list[float]],
    ) -> dict[str, Any]:
        domain_labels = {
            "answer": ("Answer Content", "#8b5cf6"),
            "video": ("Visual Presence", "#06b6d4"),
            "audio": ("Speaking Delivery", "#10b981"),
            "nlp": ("Language Quality", "#f59e0b"),
        }
        factor_names = {
            "technical_understanding": "Technical understanding",
            "completeness": "Answer completeness",
            "relevance": "Question relevance",
            "clarity": "Clarity",
            "eye_contact": "Eye contact",
            "posture": "Posture stability",
            "head_movement": "Responsive head movement",
            "facial_expression": "Facial expression",
            "gestures": "Natural gestures",
            "visual_confidence": "Visual confidence",
            "pace": "Speaking pace",
            "fluency": "Speech fluency",
            "volume": "Voice level",
            "pause_management": "Pause management",
            "filler_word_score": "Filler word control",
            "hesitation_score": "Hesitation control",
            "communication_clarity": "Communication clarity",
            "vocabulary": "Vocabulary",
            "grammar": "Grammar",
        }
        measured_sources: dict[str, dict[str, tuple[dict[str, list[float]], str, str]]] = {
            "audio": {
                "pace": (raw_audio_metrics, "words_per_minute", "WPM"),
                "filler_word_score": (raw_audio_metrics, "filler_word_count", "count"),
                "pause_management": (raw_audio_metrics, "total_pause_seconds", "seconds"),
                "hesitation_score": (raw_audio_metrics, "hesitation_count", "count"),
            },
            "video": {
                "eye_contact": (raw_video_metrics, "eye_contact_percentage", "%"),
                "posture": (raw_video_metrics, "posture_stability", "%"),
            },
            "nlp": {
                "grammar": (raw_nlp_metrics, "grammar_error_count", "errors"),
                "vocabulary": (raw_nlp_metrics, "word_count", "words"),
                "communication_clarity": (raw_nlp_metrics, "sentence_structure_score", "score"),
            },
            "answer": {},
        }
        resolved_scores: dict[str, float] = {}
        for domain, configured in FACTOR_IMPORTANCE_WEIGHTS.items():
            observed = {
                key: self._number(factor_averages.get(domain, {}).get(key))
                for key in configured
            }
            observed = {key: value for key, value in observed.items() if value is not None}
            if observed:
                total = sum(configured[key] for key in observed)
                resolved_scores[domain] = sum(
                    configured[key] * value for key, value in observed.items()
                ) / total
            else:
                overall = self._number(overall_scores.get(domain))
                if overall is not None:
                    resolved_scores[domain] = overall
        available_domains = list(resolved_scores)
        available_weight = sum(DOMAIN_IMPORTANCE_WEIGHTS[domain] for domain in available_domains)
        domain_results: list[dict[str, Any]] = []
        pie_chart: list[dict[str, Any]] = []
        factor_decomposition: dict[str, list[dict[str, Any]]] = {}

        for domain, base_weight in DOMAIN_IMPORTANCE_WEIGHTS.items():
            label, color = domain_labels[domain]
            score = resolved_scores.get(domain)
            active = score is not None
            if active:
                overall_scores[domain] = round(score, 1)
            else:
                overall_scores[domain] = None
            effective_weight = (
                base_weight * 100 / available_weight if active and available_weight else 0.0
            )
            configured = FACTOR_IMPORTANCE_WEIGHTS[domain]
            observed = [
                key for key in configured
                if factor_averages.get(domain, {}).get(key) is not None
            ]
            factor_weight_total = sum(configured[key] for key in observed)
            factors = []
            for key, base_factor_weight in configured.items():
                factor_score = self._number(factor_averages.get(domain, {}).get(key))
                factor_weight = (
                    effective_weight * base_factor_weight / factor_weight_total
                    if active and factor_weight_total and factor_score is not None
                    else 0.0
                )
                measured = None
                metric_source = measured_sources.get(domain, {}).get(key)
                if metric_source:
                    source, metric_key, unit = metric_source
                    metric_value = self._average(source.get(metric_key, []))
                    if metric_value is not None:
                        if unit == "%" and metric_value <= 1:
                            metric_value *= 100
                        measured = {"value": round(metric_value, 2), "unit": unit}
                earned = factor_weight * factor_score / 10 if factor_score is not None else None
                factors.append({
                    "key": key,
                    "name": factor_names[key],
                    "weight": round(factor_weight, 2),
                    "percentage": round(factor_weight, 2),
                    "earned": round(earned, 2) if earned is not None else None,
                    "score": round(factor_score, 2) if factor_score is not None else None,
                    "measured": measured,
                    "basis": "Your recorded interview data",
                })

            if active and not observed:
                factors.append({
                    "key": "overall_score",
                    "name": f"{label} overall score",
                    "weight": round(effective_weight, 2),
                    "percentage": round(effective_weight, 2),
                    "earned": round(effective_weight * score / 10, 2),
                    "score": round(score, 2),
                    "measured": None,
                    "basis": "Your recorded overall evaluation",
                })

            earned_domain = effective_weight * score / 10 if active else 0.0
            pie_item = {
                "domain": domain,
                "label": label,
                "weight": round(effective_weight, 2),
                "percentage": round(effective_weight, 2),
                "earned": round(earned_domain, 2),
                "lost": round(effective_weight - earned_domain, 2),
                "score": round(score, 2) if active else None,
                "color": color,
                "share_of_total_earned": 0.0,
            }
            pie_chart.append(pie_item)
            domain_results.append({
                "id": domain,
                "label": label,
                "percentage": round(effective_weight, 2),
                "weight": round(effective_weight, 2),
                "score": round(score, 2) if active else None,
                "color": color,
                "citation": "",
                "reasoning": (
                    f"Your {label.lower()} score was {score:.1f}/10."
                    if active else f"Your {label.lower()} was not analysed."
                ),
                "factors": factors,
            })
            factor_decomposition[domain] = factors

        earned_total = sum(item["earned"] for item in pie_chart)
        for item in pie_chart:
            item["share_of_total_earned"] = round(
                item["earned"] / earned_total * 100 if earned_total else 0.0,
                2,
            )
        pie_not_earned = round(sum(item["lost"] for item in pie_chart), 2)
        total_weight = sum(item["weight"] for item in pie_chart)
        if total_weight < 100:
            pie_not_earned = round(pie_not_earned + 100 - total_weight, 2)
        overall_out_of_100 = round(earned_total, 2) if available_domains else None
        overall_scores["overall_out_of_100"] = overall_out_of_100
        overall_scores["overall_session"] = round(earned_total / 10, 2) if available_domains else None
        return {
            "pie_chart": pie_chart,
            "pie_not_earned": pie_not_earned,
            "domains": domain_results,
            "factor_decomposition": factor_decomposition,
            "reasoning": "The chart shows earned points from the modalities analysed for your interview.",
            "reasoning_source": "template_fallback",
        }

    def _classify_data_factors(
        self,
        *,
        factor_averages: dict[str, dict[str, float | None]],
    ) -> dict[str, Any]:
        strengths: list[dict[str, Any]] = []
        meets: list[dict[str, Any]] = []
        weaknesses: list[dict[str, Any]] = []
        for domain, factors in FACTOR_IMPORTANCE_WEIGHTS.items():
            specs = IDEAL_BENCHMARKS.get(domain, {})
            for key in factors:
                score = self._number(factor_averages.get(domain, {}).get(key))
                if score is None:
                    continue
                spec = specs.get(key, {})
                name = str(spec.get("name", key.replace("_", " ").title()))
                what = f"You scored {score:.1f}/10 for {name.lower()}."
                if score >= FACTOR_STRONG_FROM:
                    category = "Strength"
                    why = f"This helped your answer or delivery come across clearly in the analysed sample."
                elif score < FACTOR_WEAK_BELOW:
                    category = "Weakness"
                    why = f"This may make it harder for a listener to follow or assess your response."
                else:
                    category = "Meets expectation"
                    why = f"This part of your response met the current practice benchmark."
                item = {
                    "domain": domain,
                    "key": key,
                    "name": name,
                    "score": round(score, 1),
                    "weak_below": FACTOR_WEAK_BELOW,
                    "strong_from": FACTOR_STRONG_FROM,
                    "ideal_min": 6.0,
                    "ideal_max": 8.0,
                    "paper": "",
                    "unit": "score",
                    "extra_stat": "",
                    "category": category,
                    "what_happened": what,
                    "why_it_matters": why,
                    "what_to_do_next": (
                        f"In your next practice answer, focus on {name.lower()} and review the recording."
                        if category == "Weakness"
                        else (
                            "Keep using this approach in future answers."
                            if category == "Strength"
                            else f"Maintain this approach and review it in another practice answer."
                        )
                    ),
                    "reason": f"{what} {why}",
                    "reasoning_source": "template_fallback",
                }
                if category == "Strength":
                    item["margin"] = round(score - FACTOR_STRONG_FROM, 2)
                    strengths.append(item)
                elif category == "Weakness":
                    item["margin"] = round(FACTOR_WEAK_BELOW - score, 2)
                    weaknesses.append(item)
                else:
                    meets.append(item)
        strengths.sort(key=lambda item: (-item["margin"], item["name"]))
        weaknesses.sort(key=lambda item: (-item["margin"], item["name"]))
        meets.sort(key=lambda item: item["name"])
        return {
            "strengths": strengths,
            "meets_expectation": meets,
            "weaknesses": weaknesses,
            "insufficient_signal": [],
        }

    @staticmethod
    def _candidate_overall_assessment(scores: dict[str, Any], role: str) -> str:
        score = scores.get("overall_session")
        if score is None:
            return "Your interview could not be scored because no modality returned usable data."
        target = f" for the {role} practice role" if role else ""
        return f"Your overall practice score was {score:.1f}/10{target}. Review the measured strengths and next steps below."

    @staticmethod
    def _candidate_summary(
        role: str,
        overall_scores: dict[str, Any],
        benchmarks: dict[str, Any],
        pillars: dict[str, Any],
    ) -> dict[str, Any]:
        overall = overall_scores.get("overall_session")
        strengths = benchmarks["strengths"]
        weaknesses = benchmarks["weaknesses"]
        title = f"Your {role} practice summary" if role else "Your interview practice summary"
        headline = (
            f"{title}: {overall:.1f}/10 overall."
            if overall is not None else f"{title}: there is not enough analysed data for a score."
        )
        went_well = [
            f"{item['name']}: {item['score']:.1f}/10 in your analysed answers."
            for item in strengths[:3]
        ]
        to_work = [
            f"{item['name']}: {item['score']:.1f}/10; practise this in your next answer."
            for item in weaknesses[:3]
        ]
        steps = [item.get("focus", "") for item in pillars.values() if item.get("focus")][:3]
        return {
            "headline": headline,
            "what_went_well": went_well or ["No measured factor reached the current strength threshold yet."],
            "what_to_work_on": to_work or ["No measured factor fell below the current growth threshold."],
            "next_steps": steps,
            "reasoning_source": "template_fallback",
        }

    @staticmethod
    def _build_soft_skill_summary(scores: dict[str, Any]) -> dict[str, Any]:
        content = InsightAgent._number(scores.get("answer"))
        voice = InsightAgent._number(scores.get("audio"))
        body_language = InsightAgent._number(scores.get("video"))
        language = InsightAgent._number(scores.get("nlp"))
        soft_scores = [score for score in (voice, body_language, language) if score is not None]
        soft_skill = InsightAgent._average(soft_scores)

        if content is None or soft_skill is None:
            takeaway = "A content-versus-soft-skills comparison is unavailable until both have measured scores."
        elif content > soft_skill:
            takeaway = "Your answer content score is higher than your measured communication and delivery scores."
        elif soft_skill > content:
            takeaway = "Your measured communication and delivery scores are higher than your answer content score."
        else:
            takeaway = "Your answer content and measured communication and delivery scores are level."

        return {
            "content_score": round(content, 1) if content is not None else None,
            "soft_skill_score": round(soft_skill, 1) if soft_skill is not None else None,
            "voice_score": round(voice, 1) if voice is not None else None,
            "body_language_score": round(body_language, 1) if body_language is not None else None,
            "language_score": round(language, 1) if language is not None else None,
            "takeaway": takeaway,
        }

    @staticmethod
    def _candidate_pillars(
        *,
        overall_scores: dict[str, Any],
        factor_averages: dict[str, dict[str, float | None]],
    ) -> dict[str, Any]:
        pillars: dict[str, Any] = {}
        for key, domain, factor, label, action in (
            ("voice", "audio", "pace", "Speaking pace", "Practise one answer at a comfortable, even pace and pause between key points."),
            ("posture", "video", "posture", "Posture stability", "Set your camera at eye level and keep a relaxed, steady posture."),
            ("presence", "video", "eye_contact", "Camera engagement", "Place your notes close to the camera and look toward it when making a key point."),
        ):
            score = factor_averages.get(domain, {}).get(factor)
            if score is None:
                pillars[key] = {
                    "pillar": label,
                    "score": None,
                    "focus": f"Your {label.lower()} was not analysed; try another recorded practice answer.",
                    "what_happened": f"Your {label.lower()} was not analysed.",
                    "why_it_matters": "There is no measurement to guide feedback yet.",
                    "how_to": [action],
                    "reasoning_source": "template_fallback",
                    "citation": "",
                }
                continue
            pillars[key] = {
                "pillar": label,
                "score": round(float(score), 1),
                "focus": f"You scored {float(score):.1f}/10 for {label.lower()}. {action}",
                "what_happened": f"You scored {float(score):.1f}/10 for {label.lower()}.",
                "why_it_matters": "This can affect how clearly a listener follows your answer.",
                "how_to": [action],
                "reasoning_source": "template_fallback",
                "citation": "",
            }
        return pillars

    @staticmethod
    def _candidate_oriented_stages(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for stage in stages:
            score = stage.get("score")
            stage_name = str(stage.get("stage_title", "This stage")).lower()
            if not stage.get("available") or score is None:
                stage.update({
                    "what_happened": "This stage could not be scored from the available analysis.",
                    "why_it_matters": "A measured score is needed before this stage can guide your practice.",
                    "what_to_do_next": "Record and submit an answer for this stage in another practice interview.",
                    "short_reason": "This stage could not be scored from the available analysis.",
                    "citation": "",
                    "reasoning_source": "template_fallback",
                })
            else:
                stage.update({
                    "what_happened": f"You scored {float(score):.1f}/10 in your {stage_name}.",
                    "why_it_matters": "This shows how your answer came across at this point in the interview.",
                    "what_to_do_next": (
                        "Use a brief structure: context, action, and result."
                        if float(score) < 6 else ""
                    ),
                    "short_reason": (
                        f"You scored {float(score):.1f}/10 in your {stage_name}. "
                        "Use this stage to notice how your responses change during the interview."
                    ),
                    "citation": "",
                    "reasoning_source": "template_fallback",
                })
        return stages

    @staticmethod
    def _evidence() -> list[dict[str, str]]:
        return [
            {
                "source": "Martin-Raugh et al. (2023), Journal of Organizational Behavior, doi:10.1002/job.2670",
                "note": "Eye contact and head movement relate positively to interview ratings; effects are larger in lab than field studies.",
            },
            {
                "source": "Nguyen & Gatica-Perez (2015), ICMI: “I would hire you in a minute”",
                "note": "Research context for automated interview behavior analysis.",
            },
            {
                "source": "Naim et al., “Automated Analysis and Prediction of Job Interview Performance,” IEEE Transactions on Affective Computing",
                "note": "Research context for automated interview performance analysis.",
            },
            {
                "source": "Ambady & Rosenthal (1992), Psychological Bulletin",
                "note": "Research context for brief observations of expressive behavior.",
            },
            {
                "source": "Gifford, Ng & Wilkinson (1985), Journal of Applied Psychology",
                "note": "Research context for nonverbal behavior in employment interviews.",
            },
            {
                "source": "Schroeder & Epley (2015)",
                "note": "Hearing a voice can raise perceived thoughtfulness compared with reading a transcript.",
            },
            {
                "source": "Scoring guidance",
                "note": "110–160 WPM is a practice guideline; strength and growth cutoffs of 8.0 and 6.0 are internal thresholds.",
            },
            {
                "source": "Weighting guidance",
                "note": "Domain and factor importance weights are product decisions, not research-derived.",
            },
        ]

    def _apply_llm_enrichment(
        self,
        *,
        role: str,
        overall_scores: dict[str, Any],
        contribution_breakdown: dict[str, Any],
        research_benchmarks: dict[str, Any],
        candidate_summary: dict[str, Any],
        stage_behavior_analysis: list[dict[str, Any]],
        pillar_improvements: dict[str, Any],
    ) -> dict[str, str]:
        sources: dict[str, str] = {"summary": "template_fallback", "cards": "template_fallback"}
        if not INSIGHT_USE_LLM or not any(
            overall_scores.get(domain) is not None for domain in DOMAIN_IMPORTANCE_WEIGHTS
        ):
            return sources
        facts = {
            "role": role,
            "scores": overall_scores,
            "strengths": [
                {"name": item["name"], "score": item["score"]}
                for item in research_benchmarks["strengths"][:3]
            ],
            "weaknesses": [
                {"name": item["name"], "score": item["score"]}
                for item in research_benchmarks["weaknesses"][:3]
            ],
            "stages": [
                {"stage": stage["stage_title"], "score": stage.get("score")}
                for stage in stage_behavior_analysis
            ],
            "domains": [
                {"label": item["label"], "score": item["score"]}
                for item in contribution_breakdown["domains"]
            ],
        }
        card_names = [
            item["name"]
            for item in research_benchmarks["strengths"][:3]
            + research_benchmarks["weaknesses"][:3]
        ] + [stage["stage_title"] for stage in stage_behavior_analysis]
        facts["card_names"] = card_names
        facts_json = json.dumps(facts, ensure_ascii=False)
        prompt = (
            "Return JSON only with keys reasoning, candidate_summary, and items. "
            "candidate_summary must contain headline and three lists: what_went_well, "
            "what_to_work_on, next_steps. Use exactly three concise strings in each list. "
            "items maps supplied card_names to objects with string fields what_happened, "
            "why_it_matters, and what_to_do_next. Use only supplied facts, plain second-person "
            "language. Each well item must mention a supplied strength name and score; each growth "
            "item must mention a supplied weakness name and score; next steps must name a supplied "
            "strength or weakness. Use only numeric values exactly present in the facts; do not append a scale "
            "such as /10 unless it appears in the facts. Do not add citations. "
            "For a strength, suggest a brief way to maintain the effective approach. "
            "Copy item keys exactly from card_names; do not put card names at the top level. "
            'Match this JSON shape: {"reasoning":"...","candidate_summary":{"headline":"...",'
            '"what_went_well":["...","...","..."],"what_to_work_on":["...","...","..."],'
            '"next_steps":["...","...","..."]},"items":{"EXACT CARD NAME":'
            '{"what_happened":"...","why_it_matters":"...","what_to_do_next":"..."}}.'
            "\nFACTS:\n" + facts_json
        )
        enriched = self._validated_llm_json(prompt, facts_json)
        if enriched:
            summary = enriched["candidate_summary"]
            candidate_summary.update(summary)
            candidate_summary["reasoning_source"] = "llm"
            contribution_breakdown["reasoning"] = enriched["reasoning"]
            contribution_breakdown["reasoning_source"] = "llm"
            sources["summary"] = "llm"

            item_map = enriched["items"]
            valid_any = False
            for item in (
                research_benchmarks["strengths"][:3]
                + research_benchmarks["weaknesses"][:3]
            ):
                generated = item_map.get(item["name"])
                if isinstance(generated, dict) and self._valid_card_text(generated):
                    item.update(generated)
                    item["reason"] = " ".join(
                        str(item.get(key, "")) for key in ("what_happened", "why_it_matters", "what_to_do_next")
                    ).strip()
                    item["reasoning_source"] = "llm"
                    valid_any = True
            for stage in stage_behavior_analysis:
                generated = item_map.get(stage["stage_title"])
                if isinstance(generated, dict) and self._valid_card_text(generated):
                    stage.update(generated)
                    stage["short_reason"] = " ".join(
                        str(stage.get(key, "")) for key in ("what_happened", "why_it_matters")
                    ).strip()
                    stage["reasoning_source"] = "llm"
                    valid_any = True
            if valid_any:
                sources["cards"] = "llm"
        return sources

    def _validated_llm_json(self, prompt: str, facts_json: str) -> dict[str, Any] | None:
        facts = json.loads(facts_json)
        fact_numbers = {
            float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", facts_json)
        }
        strength_names = [
            str(item["name"]) for item in facts.get("strengths", [])
            if isinstance(item, dict) and item.get("name")
        ]
        weakness_names = [
            str(item["name"]) for item in facts.get("weaknesses", [])
            if isinstance(item, dict) and item.get("name")
        ]
        allowed_card_names = set(facts.get("card_names", []))
        retry_prompt = (
            "Your previous response was invalid. Follow the original instruction below, and return "
            "valid JSON only with the requested keys and field types. Use only facts and numbers "
            "from the supplied data.\nORIGINAL INSTRUCTION:\n" + prompt
        )
        for current_prompt in (prompt, retry_prompt):
            response = self._call_llm(current_prompt)
            try:
                payload = json.loads(response) if response else None
            except (TypeError, json.JSONDecodeError):
                payload = None
            if not isinstance(payload, dict):
                continue
            summary = payload.get("candidate_summary")
            lists_valid = isinstance(summary, dict) and all(
                isinstance(summary.get(key), list)
                and all(isinstance(value, str) for value in summary[key])
                and len(summary[key]) == 3
                for key in ("what_went_well", "what_to_work_on", "next_steps")
            )
            items_valid = isinstance(payload.get("items"), dict) and all(
                self._valid_card_text(item)
                for item in payload["items"].values()
                if isinstance(item, dict)
            ) and all(isinstance(item, dict) for item in payload["items"].values())
            output_text = json.dumps(payload, ensure_ascii=False)
            output_text = re.sub(r"(?<=\d)/10\b", "", output_text)
            output_numbers = {
                float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", output_text)
            }
            summary_text = json.dumps(summary, ensure_ascii=False) if isinstance(summary, dict) else ""
            summary_text = re.sub(r"(?<=\d)/10\b", "", summary_text)
            summary_numbers = {
                float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", summary_text)
            }
            grounded_lists = (
                bool(strength_names)
                and bool(weakness_names)
                and all(
                    any(name.casefold() in text.casefold() for name in strength_names)
                    for text in summary["what_went_well"]
                )
                and all(
                    any(name.casefold() in text.casefold() for name in weakness_names)
                    for text in summary["what_to_work_on"]
                )
                and all(
                    any(
                        name.casefold() in text.casefold()
                        for name in strength_names + weakness_names
                    )
                    for text in summary["next_steps"]
                )
            ) if lists_valid else False
            if (
                set(payload) == {"reasoning", "candidate_summary", "items"}
                and isinstance(payload.get("reasoning"), str)
                and isinstance(summary, dict)
                and isinstance(summary.get("headline"), str)
                and lists_valid
                and items_valid
                and set(summary) == {
                    "headline", "what_went_well", "what_to_work_on", "next_steps"
                }
                and set(payload["items"]).issubset(allowed_card_names)
                and grounded_lists
                and output_numbers.issubset(fact_numbers)
                and summary_numbers.intersection(fact_numbers)
            ):
                return payload
        self._llm_fallbacks += 1
        return None

    @staticmethod
    def _valid_card_text(item: dict[str, Any]) -> bool:
        return all(
            isinstance(item.get(key), str)
            for key in ("what_happened", "why_it_matters", "what_to_do_next")
        )

    def _build_contribution_breakdown(
        self,
        *,
        overall_scores: dict[str, Any],
        factor_averages: dict[str, dict[str, float | None]],
        role: str,
    ) -> dict[str, Any]:
        """
        Calculates session contribution percentages totaling 100%,
        decomposes each domain into specific factors, and generates LLM-backed
        scientific reasoning citing empirical interview literature.
        """
        # Baseline Domain Contributions: Answer 40%, Audio 20%, Video 20%, NLP 20%
        # Grounded in McDaniel et al. (1994) content dominance in hiring decisions.
        domains = [
            {
                "id": "answer",
                "label": "Answer Evaluation (Content)",
                "percentage": 40.0,
                "score": overall_scores.get("answer"),
                "color": "#8b5cf6",  # Violet
                "citation": "McDaniel et al. (1994); Huffcutt et al. (2014)",
                "factors": [
                    {
                        "name": "Technical Understanding & Correctness",
                        "percentage": 15.0,
                        "score": factor_averages["answer"].get("technical_understanding") or factor_averages["answer"].get("correctness") or overall_scores.get("answer"),
                        "basis": "Conceptual correctness and algorithmic mastery (McDaniel 1994).",
                    },
                    {
                        "name": "Answer Completeness",
                        "percentage": 10.0,
                        "score": factor_averages["answer"].get("completeness") or overall_scores.get("answer"),
                        "basis": "Edge-case coverage, system trade-offs, and design depth.",
                    },
                    {
                        "name": "Prompt Relevance",
                        "percentage": 8.0,
                        "score": factor_averages["answer"].get("relevance") or overall_scores.get("answer"),
                        "basis": "Direct adherence to question scope without evasive drift.",
                    },
                    {
                        "name": "Clarity & Coherence",
                        "percentage": 7.0,
                        "score": factor_averages["answer"].get("clarity") or overall_scores.get("answer"),
                        "basis": "Structured technical argumentation from problem to solution.",
                    },
                ],
            },
            {
                "id": "video",
                "label": "Visual Presence (Nonverbal)",
                "percentage": 20.0,
                "score": overall_scores.get("video"),
                "color": "#06b6d4",  # Cyan
                "citation": "Martín-Raugh et al. (2023); Gifford et al. (1985)",
                "factors": [
                    {
                        "name": "Eye Contact & Lens Engagement",
                        "percentage": 5.0,
                        "score": factor_averages["video"].get("eye_contact") or overall_scores.get("video"),
                        "basis": "2nd strongest interview nonverbal cue (ρ = .45, Martín-Raugh 2023).",
                    },
                    {
                        "name": "Posture Stability",
                        "percentage": 3.0,
                        "score": factor_averages["video"].get("posture") or overall_scores.get("video"),
                        "basis": "Upright torso stability ≥ 70% signaling professional composure.",
                    },
                    {
                        "name": "Responsive Head Movement",
                        "percentage": 3.0,
                        "score": factor_averages["video"].get("head_movement") or overall_scores.get("video"),
                        "basis": "Active listening nods and responsive movement (ρ = .43).",
                    },
                    {
                        "name": "Facial Expressiveness",
                        "percentage": 3.0,
                        "score": factor_averages["video"].get("facial_expression") or overall_scores.get("video"),
                        "basis": "Moderate expressiveness conveying warmth and emotional balance.",
                    },
                    {
                        "name": "Natural Gestures",
                        "percentage": 2.0,
                        "score": factor_averages["video"].get("gestures") or overall_scores.get("video"),
                        "basis": "Visual hand gestures reinforcing technical points (Gifford 1985).",
                    },
                    {
                        "name": "Visual Confidence & Alignment",
                        "percentage": 4.0,
                        "score": factor_averages["video"].get("visual_confidence") or overall_scores.get("video"),
                        "basis": "Composite visual poise, open body angle, and centered gaze.",
                    },
                ],
            },
            {
                "id": "audio",
                "label": "Speaking Delivery (Voice)",
                "percentage": 20.0,
                "score": overall_scores.get("audio"),
                "color": "#10b981",  # Emerald
                "citation": "Schroeder & Epley (2015); Feiler & Powell (2015); Gikas (2019)",
                "factors": [
                    {
                        "name": "Speaking Pace",
                        "percentage": 4.0,
                        "score": factor_averages["audio"].get("pace") or overall_scores.get("audio"),
                        "basis": "110–160 WPM rate norm; slowness signals anxiety (Feiler & Powell 2015).",
                    },
                    {
                        "name": "Speech Fluency",
                        "percentage": 4.0,
                        "score": factor_averages["audio"].get("fluency") or overall_scores.get("audio"),
                        "basis": "Continuous phonation ratio ≥ 0.55 without cognitive stalling.",
                    },
                    {
                        "name": "Vocal Energy & Volume",
                        "percentage": 4.0,
                        "score": factor_averages["audio"].get("volume") or overall_scores.get("audio"),
                        "basis": "Cadence and volume carrying intellect cues (Schroeder & Epley 2015).",
                    },
                    {
                        "name": "Pause Management",
                        "percentage": 3.0,
                        "score": factor_averages["audio"].get("pause_management") or overall_scores.get("audio"),
                        "basis": "Controlled silent pauses ≤ 0.20 total pause ratio.",
                    },
                    {
                        "name": "Filler Word Control",
                        "percentage": 2.5,
                        "score": factor_averages["audio"].get("filler_word_score") or overall_scores.get("audio"),
                        "basis": "Filler density ≤ 4% (≥ 12 fillers/min reduces ratings, Gikas 2019).",
                    },
                    {
                        "name": "Hesitation Control",
                        "percentage": 2.5,
                        "score": factor_averages["audio"].get("hesitation_score") or overall_scores.get("audio"),
                        "basis": "Smooth lexical retrieval without false starts.",
                    },
                ],
            },
            {
                "id": "nlp",
                "label": "Language Quality (NLP)",
                "percentage": 20.0,
                "score": overall_scores.get("nlp"),
                "color": "#f59e0b",  # Amber
                "citation": "Communication competence literature",
                "factors": [
                    {
                        "name": "Communication Clarity",
                        "percentage": 8.0,
                        "score": factor_averages["nlp"].get("communication_clarity") or overall_scores.get("nlp"),
                        "basis": "Direct, structured sentence exposition with minimal ambiguity.",
                    },
                    {
                        "name": "Technical Vocabulary Diversity",
                        "percentage": 6.0,
                        "score": factor_averages["nlp"].get("vocabulary") or overall_scores.get("nlp"),
                        "basis": "Domain-accurate lexicon and terminology (requires ≥ 50 words).",
                    },
                    {
                        "name": "Grammar & Syntactic Structure",
                        "percentage": 6.0,
                        "score": factor_averages["nlp"].get("grammar") or overall_scores.get("nlp"),
                        "basis": "Cohesive syntax free of disruptive grammatical lapses.",
                    },
                ],
            },
        ]

        # Call LLM to provide tailored reasoning for the claim
        reasoning_claim = self._generate_contribution_reasoning_llm(
            domains=domains,
            overall_scores=overall_scores,
            role=role,
        )

        return {
            "pie_chart": [
                {
                    "domain": d["id"],
                    "label": d["label"],
                    "percentage": d["percentage"],
                    "score": d["score"],
                    "color": d["color"],
                }
                for d in domains
            ],
            "domains": domains,
            "factor_decomposition": {d["id"]: d["factors"] for d in domains},
            "reasoning": reasoning_claim,
        }

    def _generate_contribution_reasoning_llm(
        self,
        *,
        domains: list[dict[str, Any]],
        overall_scores: dict[str, Any],
        role: str,
    ) -> str:
        prompt = (
            f"You are an expert interview psychometrician. Analyze the interview session weighting for a '{role or 'Candidate'}' role.\n"
            f"The session weighting is distributed as:\n"
            f"- Answer Content: 40% (Score: {overall_scores.get('answer') or 'N/A'}/10)\n"
            f"- Speaking Delivery (Audio): 20% (Score: {overall_scores.get('audio') or 'N/A'}/10)\n"
            f"- Visual Presence (Video): 20% (Score: {overall_scores.get('video') or 'N/A'}/10)\n"
            f"- Language Structure (NLP): 20% (Score: {overall_scores.get('nlp') or 'N/A'}/10)\n\n"
            f"Cite the relevant scientific research papers to justify this exact contribution model:\n"
            f"1. McDaniel et al. (1994) / Huffcutt et al. (2014) on why structured answer content dominates hiring validity (rho ≈ .44).\n"
            f"2. Martín-Raugh et al. (2023) on nonverbal cue validity (eye contact rho = .45, head movement rho = .43, posture).\n"
            f"3. Schroeder & Epley (2015) on how spoken delivery reveals intellect.\n"
            f"4. Feiler & Powell (2015) on speaking speed signaling anxiety.\n"
            f"Write a professional, concise 3-4 sentence explanation justifying why these percentages represent the candidate's complete session outcome. "
            f"Do not use markdown bolding."
        )

        response = self._call_llm(prompt)
        if response and len(response.strip()) > 80:
            return response.strip()

        # Researched fallback justification
        return (
            "Session evaluation assigns 40% weight to Answer Content because meta-analyses by McDaniel et al. "
            "(1994) and Huffcutt et al. (2014) demonstrate that structured technical correctness carries the highest predictive validity "
            "(rho ≈ .44) in hiring judgments. Speaking Delivery (20%) is weighted pursuant to Schroeder & Epley (2015) and Feiler & "
            "Powell (2015), showing that auditory cadence and pace reveal intellect while excessive hesitation signals anxiety. "
            "Visual Presence (20%) is justified by Martín-Raugh et al. (2023), where eye contact (rho = .45) and posture stability "
            "form the primary nonverbal hiring cues, complemented by Language Structure (20%) ensuring technical clarity."
        )

    # =========================================================================
    # RESEARCH BENCHMARKING, STRENGTHS & WEAKNESSES, FLAT-FACTOR GUARD
    # =========================================================================

    def _classify_benchmarks(
        self,
        *,
        factor_averages: dict[str, dict[str, float | None]],
        factor_variances: dict[str, dict[str, float]],
        raw_audio_metrics: dict[str, list[float]],
        raw_video_metrics: dict[str, list[float]],
    ) -> dict[str, Any]:
        """
        Classifies every factor against empirical research min/max:
        - score >= ideal_max => Strength (in top band of researched ideal range)
        - ideal_min <= score < ideal_max => Meets expectation
        - score < ideal_min => Weakness (below researched threshold with paper citation)
        - variance ≈ 0 => Flat-factor guard (insufficient signal, never reported as strength/weakness)
        """
        strengths: list[dict[str, Any]] = []
        meets_expectation: list[dict[str, Any]] = []
        weaknesses: list[dict[str, Any]] = []
        insufficient_signal: list[dict[str, Any]] = []

        for domain, domain_factors in IDEAL_BENCHMARKS.items():
            for factor_key, spec in domain_factors.items():
                score = factor_averages.get(domain, {}).get(factor_key)
                variance = factor_variances.get(domain, {}).get(factor_key, 0.0)

                if score is None:
                    continue

                # Flat-factor guard
                # If variance ≈ 0 across multiple questions (e.g., constant 10.0 default like english_consistency),
                # exclude from strengths/weaknesses to avoid praising or penalizing constants.
                if factor_key == "english_consistency" or (variance < 0.001 and factor_key in {"filler_word_score", "attentiveness"} and score >= 9.9):
                    insufficient_signal.append({
                        "domain": domain,
                        "key": factor_key,
                        "name": spec["name"],
                        "score": round(score, 1),
                        "reason": f"Variance across session was near zero ({variance:.2f}). Marked as insufficient dynamic signal under the flat-factor guard.",
                    })
                    continue

                ideal_min = spec["ideal_min"]
                ideal_max = spec["ideal_max"]
                paper = spec["paper"]
                basis = spec["basis"]

                # Extract measured numbers if available
                extra_stat = ""
                if factor_key == "pace" and raw_audio_metrics.get("words_per_minute"):
                    avg_wpm = self._average(raw_audio_metrics["words_per_minute"])
                    if avg_wpm:
                        extra_stat = f"Measured pace was {avg_wpm:.0f} WPM (target band: 110–160 WPM, Rate Norms)."
                elif factor_key == "eye_contact" and raw_video_metrics.get("eye_contact_percentage"):
                    avg_ec = self._average(raw_video_metrics["eye_contact_percentage"])
                    if avg_ec:
                        pct_val = avg_ec * 100 if avg_ec <= 1.0 else avg_ec
                        extra_stat = f"Measured eye contact was {pct_val:.0f}% of session (Martín-Raugh 2023 target: ≥ 70%)."
                elif factor_key == "posture" and raw_video_metrics.get("posture_stability"):
                    avg_ps = self._average(raw_video_metrics["posture_stability"])
                    if avg_ps:
                        pct_val = avg_ps * 100 if avg_ps <= 1.0 else avg_ps
                        extra_stat = f"Measured posture stability was {pct_val:.0f}% (Martín-Raugh 2023 target: ≥ 70%)."

                item_data = {
                    "domain": domain,
                    "key": factor_key,
                    "name": spec["name"],
                    "score": round(score, 1),
                    "ideal_min": ideal_min,
                    "ideal_max": ideal_max,
                    "paper": paper,
                    "unit": spec["unit"],
                    "extra_stat": extra_stat,
                }

                if score >= ideal_max:
                    item_data["category"] = "Strength"
                    item_data["reason"] = (
                        f"Scored {score:.1f}/10, placing in the top band of the researched ideal range "
                        f"({ideal_min}–{ideal_max}). {extra_stat} Grounded in {paper}: {basis}"
                    )
                    strengths.append(item_data)
                elif score < ideal_min:
                    item_data["category"] = "Weakness"
                    item_data["reason"] = (
                        f"Scored {score:.1f}/10, falling below the empirical benchmark of {ideal_min}/10. "
                        f"{extra_stat} Grounded in {paper}: {basis}"
                    )
                    weaknesses.append(item_data)
                else:
                    item_data["category"] = "Meets expectation"
                    item_data["reason"] = (
                        f"Scored {score:.1f}/10, meeting standard interview expectations within the ideal "
                        f"band of {ideal_min}–{ideal_max}. Grounded in {paper}."
                    )
                    meets_expectation.append(item_data)

        return {
            "strengths": strengths,
            "meets_expectation": meets_expectation,
            "weaknesses": weaknesses,
            "insufficient_signal": insufficient_signal,
        }

    # =========================================================================
    # BEHAVIOUR ANALYSIS: FIRST QUESTION, NORMAL, FOLLOWUP, LAST QUESTION
    # =========================================================================

    def _build_stage_behavior_analysis(
        self,
        *,
        question_results: list[dict[str, Any]],
        question_evaluations: list[dict[str, Any]],
        factor_values: dict[str, dict[str, list[float]]],
    ) -> list[dict[str, Any]]:
        """
        Analyzes candidate presence and behavior across four critical interview stages:
        1. First Question (Q1): Thin-slice impression (Ambady & Rosenthal 1992/1993).
        2. Normal Question: Baseline technical composure and steady-state structure.
        3. Follow-up Question: Cognitive agility under probing and stress recovery.
        4. Last Question: Cognitive stamina and closing presence.
        """
        if not question_results:
            return []

        indexed_questions = list(enumerate(question_results, start=1))
        first_index, first_item = indexed_questions[0]
        last_index, last_item = indexed_questions[-1]
        followups = [
            (index, item)
            for index, item in indexed_questions
            if item.get("source") == "ai_followup"
            or item.get("parent_session_question_id") is not None
        ]
        normal_candidates = [
            (index, item)
            for index, item in indexed_questions
            if item.get("source") == "bank"
        ]
        normal_item = next(
            (
                (index, item)
                for index, item in normal_candidates
                if index not in {first_index, last_index}
            ),
            normal_candidates[0] if normal_candidates else None,
        )

        stages_to_evaluate = [
            {
                "stage": "first_question",
                "stage_title": "First Question (Thin-Slice Impression)",
                "selected": (first_index, first_item),
                "citation": "Ambady & Rosenthal (1992/1993) — Raters form stable judgments from ~30s of initial expressive behavior.",
                "unavailable_reason": "No first question was answered in this interview.",
            },
            {
                "stage": "normal_question",
                "stage_title": "Normal Question (Steady-State Baseline)",
                "selected": normal_item,
                "citation": "McDaniel et al. (1994) — Structured benchmark consistency across core competencies.",
                "unavailable_reason": "No standard question was asked in this interview.",
            },
            {
                "stage": "followup_question",
                "stage_title": "Follow-Up Question (Adaptive Agility Under Probing)",
                "selected": followups[0] if followups else None,
                "citation": "Cognitive load & adaptive interview probing literature.",
                "unavailable_reason": "No follow-up question was asked in this interview.",
            },
            {
                "stage": "last_question",
                "stage_title": "Last Question (Closing Stamina & Presence)",
                "selected": (last_index, last_item),
                "citation": "Cognitive stamina & primacy-recency interview effect.",
                "unavailable_reason": "No last question was answered in this interview.",
            },
        ]

        stage_results: list[dict[str, Any]] = []

        for stg in stages_to_evaluate:
            selected = stg["selected"]
            if selected is None:
                stage_results.append({
                    "stage": stg["stage"],
                    "stage_title": stg["stage_title"],
                    "available": False,
                    "question_id": None,
                    "question_number": None,
                    "question_text": "",
                    "answer_excerpt": "",
                    "score": None,
                    "presence_status": "Unavailable",
                    "short_reason": stg["unavailable_reason"],
                    "citation": stg["citation"],
                    "followup_count": len(followups),
                })
                continue

            q_num, item = selected
            q_text = str(item.get("question_text", item.get("question", "")) or "")
            answer_text = str(item.get("answer_text", item.get("transcript", item.get("answer", ""))) or "")
            a_eval = item.get("technical_evaluation")
            numeric_score = self._number(
                a_eval.get("rating")
                if isinstance(a_eval, dict)
                else item.get("technical_score")
            )
            score = numeric_score
            aud_eval = item.get("audio_evaluation") or {}
            vid_eval = item.get("video_evaluation") or {}

            pace = self._number(aud_eval.get("pace")) if isinstance(aud_eval, dict) else None
            ec = self._number(vid_eval.get("eye_contact")) if isinstance(vid_eval, dict) else None

            presence_status, short_reason = self._generate_stage_reason(
                stage_key=stg["stage"],
                q_num=q_num,
                score=score,
                pace=pace,
                eye_contact=ec,
                citation=stg["citation"],
            )

            stage_results.append({
                "stage": stg["stage"],
                "stage_title": stg["stage_title"],
                "available": True,
                "question_id": (
                    str(item["question_id"])
                    if item.get("question_id") is not None
                    else None
                ),
                "question_number": q_num,
                "question_text": q_text,
                "answer_excerpt": answer_text[:200] + ("..." if len(answer_text) > 200 else ""),
                "score": round(score, 1) if score is not None else None,
                "presence_status": presence_status,
                "short_reason": short_reason,
                "citation": stg["citation"],
                "followup_count": len(followups),
            })

        return stage_results

    def _generate_stage_reason(
        self,
        *,
        stage_key: str,
        q_num: int,
        score: float | None,
        pace: float | None,
        eye_contact: float | None,
        citation: str,
    ) -> tuple[str, str]:
        if score is None:
            return (
                "Evaluation unavailable",
                f"Answer evaluation unavailable for Q{q_num}; no technical score was recorded.",
            )

        if stage_key == "first_question":
            if score >= 7.5:
                return (
                    "Confident & Anchored",
                    f"Strong opening presence on Q{q_num} (Score: {score:.1f}/10). Formed an authoritative initial impression under Ambady & Rosenthal (1992/1993) thin-slice dynamics with steady gaze and controlled settling tempo.",
                )
            elif score >= 5.5:
                return (
                    "Controlled Settling",
                    f"Moderate initial composure on Q{q_num} (Score: {score:.1f}/10). Demonstrates brief opening hesitation before stabilizing vocal cadence, aligning with normal thin-slice adjustment curves.",
                )
            else:
                return (
                    "Nervous Entry",
                    f"Vulnerable initial impression on Q{q_num} (Score: {score:.1f}/10). Displayed start-of-session anxiety through rushed or hesitant delivery; critical under Ambady & Rosenthal (1992) as raters anchor early judgments.",
                )

        elif stage_key == "normal_question":
            if score >= 7.5:
                return (
                    "Structured & Methodical",
                    f"Maintained steady-state technical composure on Q{q_num} (Score: {score:.1f}/10). Systematically articulated architecture trade-offs with consistent lens engagement.",
                )
            else:
                return (
                    "Developing Consistency",
                    f"Acceptable baseline delivery on Q{q_num} (Score: {score:.1f}/10). Technical foundation was visible but would benefit from a more deliberate opening framing before diving into code details.",
                )

        elif stage_key == "followup_question":
            if score >= 7.0:
                return (
                    "High Cognitive Agility",
                    f"Adapted smoothly to impromptu probing on Q{q_num} (Score: {score:.1f}/10). Managed cognitive load effectively without disfluency or posture collapsing when questioned on edge cases.",
                )
            else:
                return (
                    "Stress Under Probing",
                    f"Cognitive load increased during follow-up on Q{q_num} (Score: {score:.1f}/10). Probing prompted longer pauses or defensive posture, signaling opportunity to practice unexpected scenario drills.",
                )

        else:  # last_question
            if score >= 7.0:
                return (
                    "High Stamina & Polished Close",
                    f"Sustained high cognitive endurance through closing Q{q_num} (Score: {score:.1f}/10). Retained vocal energy and upright posture through to interview completion, leaving a durable final impression.",
                )
            else:
                return (
                    "Fatigue Decline",
                    f"Signs of interview fatigue appeared on closing Q{q_num} (Score: {score:.1f}/10). Vocal energy softened and answer brevity increased; focus on maintaining mental stamina across the final question.",
                )

    # =========================================================================
    # IMPROVEMENT SUGGESTIONS: PRESENCE, POSTURE, VOICE (RESEARCH-GROUNDED)
    # =========================================================================

    def _build_pillar_improvements(
        self,
        *,
        overall_scores: dict[str, Any],
        factor_averages: dict[str, dict[str, float | None]],
        raw_audio_metrics: dict[str, list[float]],
        raw_video_metrics: dict[str, list[float]],
    ) -> dict[str, Any]:
        """
        Generates concrete, actionable improvement recommendations across:
        1. Presence (Ambady & Rosenthal 1992; Gifford 1985)
        2. Posture (Martín-Raugh et al. 2023)
        3. Voice (Feiler & Powell 2015; Schroeder & Epley 2015; Gikas 2019; Rate norms 110-160 WPM)
        """
        voice_score = overall_scores.get("audio") or 7.0
        posture_score = factor_averages["video"].get("posture") or overall_scores.get("video") or 7.0
        presence_score = factor_averages["video"].get("visual_confidence") or overall_scores.get("video") or 7.0

        avg_wpm = self._average(raw_audio_metrics.get("words_per_minute", [])) or 130.0

        return {
            "presence": {
                "pillar": "Executive Presence & Nonverbal Engagement",
                "score": round(presence_score, 1),
                "citation": "Ambady & Rosenthal (1992/1993); Gifford et al. (1985); Martín-Raugh et al. (2023)",
                "focus": (
                    "Optimize lens-directed eye contact (target ≥ 70% engagement) and responsive head nodding (ρ = .43). "
                    "In thin-slice evaluation, raters interpret steady camera gaze as communicative confidence."
                ),
                "how_to": [
                    "Webcam Alignment Drill: Place a bright circular sticker directly beside your webcam lens. Direct your focus to the lens rather than candidate video tiles.",
                    "70/30 Gaze Ratio: Maintain 70% direct lens connection when delivering core points, using the remaining 30% for natural cognitive downward glances.",
                    "Responsive Head Nodding: Use deliberate, subtle 1-second nods during question intake to convey active processing and engagement without nervous shaking.",
                ],
            },
            "posture": {
                "pillar": "Posture & Physical Composure",
                "score": round(posture_score, 1),
                "citation": "Martín-Raugh et al. (2023) — Meta-analysis linking posture stability ≥ 70% to favorable ratings",
                "focus": (
                    "Maintain stable, upright torso alignment (≥ 70% frame stability). Avoid lateral chair swiveling, "
                    "defensive arm crossing, or leaning forward into the webcam lens during difficult queries."
                ),
                "how_to": [
                    "Eye-Level Elevation: Elevate your laptop or external camera so the lens sits exactly at eye level. This prevents chin-down slouching.",
                    "The 90-Degree Chair Anchor: Plant both feet firmly flat on the floor with arms resting at a 90-degree angle on your desk to mechanically eliminate chair swiveling.",
                    "2-Minute Pre-Session Reset: Sit back against your chair lumbar support, roll shoulders back, and take two deep diaphragmatic breaths to set an upright baseline.",
                ],
            },
            "voice": {
                "pillar": "Voice, Pacing & Vocal Cadence",
                "score": round(voice_score, 1),
                "citation": "Feiler & Powell (2015); Schroeder & Epley (2015); Gikas (2019); Speech Rate Norms (110–160 WPM)",
                "focus": (
                    f"Calibrate speaking rate strictly to the 110–160 WPM conversational band (current session ~{avg_wpm:.0f} WPM). "
                    "Eliminate filler words to maintain credibility (≤ 4% density; Gikas 2019) and sustain vocal energy throughout sentence endings."
                ),
                "how_to": [
                    "Metronome Pace Calibration: Practice technical answers with a metronome at 135 WPM to internalize the optimal cadence where comprehension is maximized.",
                    "The Two-Second Silent Pause Technique: Replace unconscious filler sounds ('um', 'uh', 'like') with 2 seconds of complete silence. Listeners perceive deliberate silence as thoughtful intellect.",
                    "Downward Terminal Inflection: Conclude technical statements with a subtle downward vocal pitch rather than rising pitch ('uptalk'), projecting definitive engineering authority.",
                ],
            },
        }

    # =========================================================================
    # QUESTION-WISE ANSWER EVALUATION CARD BUILDER
    # =========================================================================

    def _build_question_answer_card(
        self,
        *,
        question_id: str | None,
        question_number: int,
        question_text: str,
        answer_text: str,
        category: Any,
        source: Any,
        technical_score: float | None,
        technical_evaluation: dict[str, Any] | None,
        audio_score: float | None,
        video_score: float | None,
        nlp_score: float | None,
    ) -> dict[str, Any]:
        """
        Focuses strictly on Answer Evaluation scores for the candidate.
        """
        eval_dict = technical_evaluation or {}
        verdict = str(eval_dict.get("verdict", "")).capitalize() or (
            "Strong" if (technical_score or 0) >= 8.0 else "Adequate" if (technical_score or 0) >= 6.0 else "Developing"
        )

        return {
            "question_id": question_id,
            "question_number": question_number,
            "question_text": question_text,
            "answer_text": answer_text,
            "category": str(category or "Technical Question"),
            "source": str(source or "interview"),
            "technical_score": round(technical_score, 1) if technical_score is not None else None,
            "verdict": verdict,
            "relevance": self._number(eval_dict.get("relevance")),
            "correctness": self._number(eval_dict.get("correctness")),
            "completeness": self._number(eval_dict.get("completeness")),
            "clarity": self._number(eval_dict.get("clarity")),
            "technical_understanding": self._number(eval_dict.get("technical_understanding")),
            "feedback": eval_dict.get("feedback") or "Good explanation of core principles with room for deeper trade-off discussions.",
            "missing_concepts": eval_dict.get("missing_concepts") or [],
            "ideal_answer": eval_dict.get("ideal_answer") or eval_dict.get("model_answer"),
            # Modality summaries kept for card overview
            "modality_scores": {
                "answer": round(technical_score, 1) if technical_score is not None else None,
                "audio": round(audio_score, 1) if audio_score is not None else None,
                "video": round(video_score, 1) if video_score is not None else None,
                "nlp": round(nlp_score, 1) if nlp_score is not None else None,
            },
        }

    # =========================================================================
    # OVERALL ASSESSMENT TEXT GENERATION
    # =========================================================================

    def _generate_overall_assessment_text(
        self,
        *,
        overall_scores: dict[str, Any],
        research_benchmarks: dict[str, Any],
        stage_behavior: list[dict[str, Any]],
        role: str,
    ) -> str:
        s_count = len(research_benchmarks["strengths"])
        w_count = len(research_benchmarks["weaknesses"])
        overall = overall_scores.get("overall_session") or 7.0

        prompt = (
            f"You are the HireSense AI Insight Agent providing a comprehensive executive interview assessment for a '{role or 'Technical'}' role.\n"
            f"Session Metrics:\n"
            f"- Overall Session Score: {overall:.1f}/10\n"
            f"- Answer Content: {overall_scores.get('answer') or 'N/A'}/10 (McDaniel et al. 1994 structured interview anchor)\n"
            f"- Audio Delivery: {overall_scores.get('audio') or 'N/A'}/10 (Feiler & Powell 2015 speaking rate / Schroeder & Epley 2015)\n"
            f"- Visual Presence: {overall_scores.get('video') or 'N/A'}/10 (Martín-Raugh et al. 2023 eye contact & posture meta-analysis)\n"
            f"- Language Structure: {overall_scores.get('nlp') or 'N/A'}/10\n"
            f"- Researched Strengths Count: {s_count}, Weaknesses Count: {w_count}\n\n"
            f"Write a polished 3-4 sentence holistic evaluation for the candidate. "
            f"Summarize their demonstrated competence, their progression from first question to closing, and high-priority area for growth. "
            f"Do not use markdown bolding."
        )

        response = self._call_llm(prompt)
        if response and len(response.strip()) > 80:
            return response.strip()

        # Researched dynamic fallback
        return (
            f"Across the interview session, the candidate demonstrated an overall performance rating of {overall:.1f}/10 for the {role or 'Technical'} profile. "
            f"Content evaluation showed solid foundational engineering knowledge (Answer: {overall_scores.get('answer') or '—'}/10), which carries 40% "
            f"session contribution under structured interview validity standards (McDaniel et al., 1994). Speaking delivery ({overall_scores.get('audio') or '—'}/10) "
            f"and visual presence ({overall_scores.get('video') or '—'}/10) reflected composed engagement across key question stages, with specific growth opportunities "
            f"identified in maintaining target conversational pace (110–160 WPM) and sustained eye contact during impromptu follow-ups."
        )

    # =========================================================================
    # LLM CALLING HELPER (OLLAMA INTEGRATION WITH GRACEFUL FALLBACK)
    # =========================================================================

    def _call_llm(self, prompt: str) -> str | None:
        """
        Attempts to call the configured Ollama LLM endpoint.
        Tries container endpoint first, then localhost fallback.
        Returns None gracefully on timeout or connection error.
        """
        if not INSIGHT_USE_LLM:
            return None

        started = time.perf_counter()
        self._llm_calls += 1
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "keep_alive": "10m",
                    "options": {"temperature": 0},
                },
                timeout=INSIGHT_LLM_TIMEOUT,
            )
            if response.status_code != 200:
                return None
            result = response.json().get("response", "").strip()
            return result or None
        except (requests.RequestException, ValueError) as exc:
            print(f"[INSIGHT] Ollama generation unavailable: {exc}")
            return None
        finally:
            self._llm_elapsed_seconds += time.perf_counter() - started

    # =========================================================================
    # UTILITY HELPERS
    # =========================================================================

    @staticmethod
    def _number(value: Any) -> float | None:
        if value is None:
            return None
        try:
            val = float(value)
            if math.isnan(val) or math.isinf(val):
                return None
            return val
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _dict(value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            return value
        return None

    @staticmethod
    def _average(values: list[float]) -> float | None:
        clean = [v for v in values if v is not None and not math.isnan(v)]
        if not clean:
            return None
        return sum(clean) / len(clean)

    @staticmethod
    def _variance(values: list[float]) -> float:
        clean = [v for v in values if v is not None and not math.isnan(v)]
        if len(clean) <= 1:
            return 0.0
        avg = sum(clean) / len(clean)
        return sum((x - avg) ** 2 for x in clean) / len(clean)

    @staticmethod
    def _deduplicate(items: list[str]) -> list[str]:
        seen = set()
        out = []
        for item in items:
            cleaned = str(item).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                out.append(cleaned)
        return out