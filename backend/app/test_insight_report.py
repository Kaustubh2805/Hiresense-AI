import json

from app.agents import insight_agent as insight_module
from app.agents.insight_agent import DOMAIN_IMPORTANCE_WEIGHTS, InsightAgent


def test_strength_and_weakness_thresholds_use_measured_factors_only() -> None:
    report = InsightAgent()._classify_data_factors(
        factor_averages={
            "answer": {
                "technical_understanding": 8.0,
                "completeness": 5.9,
                "relevance": None,
            }
        }
    )

    assert [item["key"] for item in report["strengths"]] == ["technical_understanding"]
    assert [item["key"] for item in report["weaknesses"]] == ["completeness"]
    assert all(item["key"] != "relevance" for item in report["strengths"] + report["weaknesses"])


def test_contribution_weights_renormalize_only_available_modalities() -> None:
    result = InsightAgent()._build_data_contribution(
        overall_scores={"answer": 8.0, "audio": 0.0, "video": None, "nlp": 6.0},
        factor_averages={
            "answer": {
                "technical_understanding": 8.0,
                "completeness": None,
                "relevance": 8.0,
                "clarity": None,
            },
            "audio": {
                "pace": 0.0,
                "fluency": None,
                "volume": None,
                "pause_management": None,
                "filler_word_score": None,
                "hesitation_score": None,
            },
            "video": {},
            "nlp": {},
        },
        raw_audio_metrics={},
        raw_video_metrics={},
        raw_nlp_metrics={},
    )

    active = [item for item in result["pie_chart"] if item["weight"] > 0]
    inactive_video = next(item for item in result["pie_chart"] if item["domain"] == "video")
    zero_audio = next(item for item in result["pie_chart"] if item["domain"] == "audio")
    answer_missing = next(
        item for item in result["factor_decomposition"]["answer"]
        if item["key"] == "completeness"
    )
    audio_zero = next(
        item for item in result["factor_decomposition"]["audio"]
        if item["key"] == "pace"
    )

    assert sum(item["weight"] for item in active) == 100
    assert inactive_video["score"] is None
    assert inactive_video["weight"] == 0
    assert zero_audio["score"] == 0
    assert zero_audio["earned"] == 0
    assert answer_missing["score"] is None
    assert answer_missing["weight"] == 0
    assert answer_missing["earned"] is None
    assert audio_zero["score"] == 0
    assert audio_zero["earned"] == 0
    for domain in active:
        factor_total = sum(
            item["earned"] or 0
            for item in result["factor_decomposition"][domain["domain"]]
        )
        assert abs(factor_total - domain["earned"]) < 0.02


def test_no_modalities_returns_insufficient_data(monkeypatch) -> None:
    monkeypatch.setattr(insight_module, "INSIGHT_USE_LLM", False)
    timings = {}
    report = InsightAgent().generate_insights(role="", question_results=[], timings=timings)

    assert report.status == "insufficient_data"
    assert report.overall_scores["overall_session"] is None
    assert report.candidate_summary["headline"].endswith("not enough analysed data for a score.")
    assert timings["insight_llm"] == 0


def test_pillar_does_not_reuse_domain_score_for_unmeasured_factor() -> None:
    pillars = InsightAgent._candidate_pillars(
        overall_scores={"audio": 7.0, "video": 8.0},
        factor_averages={"audio": {}, "video": {"eye_contact": 8.0}},
    )

    assert pillars["posture"]["score"] is None
    assert pillars["presence"]["score"] == 8.0
    assert pillars["voice"]["score"] is None


def test_language_analysis_aggregates_only_persisted_metrics() -> None:
    report = InsightAgent()._aggregate_language_analysis(
        [
            {
                "nlp_evaluation": {
                    "word_count": 6,
                    "hindi_word_count": 2,
                    "english_word_count": 4,
                    "dominant_language": "english",
                    "code_switching_count": 1,
                    "code_switching_ratio": 0.2,
                    "hindi_words": {"mujhe": 1, "hai": 1},
                    "english_words": {"python": 1, "use": 1},
                    "language_switching_examples": ["project -> aur"],
                }
            },
            {"nlp_evaluation": {"word_count": 4}},
        ]
    )

    assert report["data_available"] is True
    assert report["analyzed_answer_count"] == 1
    assert report["total_word_count"] == 6
    assert report["english_word_percentage"] == 66.7
    assert report["hindi_word_percentage"] == 33.3
    assert report["code_switching_count"] == 1
    assert report["dominant_language"] == "english"
    assert "switched between Hindi and English 1 time." in report["feedback"]
    assert report["language_switching_examples"] == [
        {"question_number": 1, "example": "project -> aur"}
    ]
    assert "intelligibility" in report["interpretation_note"]


def test_report_uses_observed_scores_and_candidate_facing_feedback(monkeypatch) -> None:
    monkeypatch.setattr(insight_module, "INSIGHT_USE_LLM", False)
    report = InsightAgent().generate_insights(
        role="Software Engineer",
        question_results=[{
            "question_text": "How would you design a cache?",
            "answer_text": "I would use a cache with an eviction policy.",
            "technical_evaluation": {
                "rating": 7.0,
                "technical_understanding": 8.5,
                "completeness": 5.0,
                "relevance": 8.0,
                "clarity": 7.0,
                "correctness": 8.0,
            },
            "audio_evaluation": {
                "overall_score": 6.0,
                "pace": 0.0,
                "fluency": 7.0,
                "volume": 7.0,
                "pause_management": 6.0,
                "filler_word_score": 7.0,
                "hesitation_score": 6.0,
                "words_per_minute": 0,
            },
            "video_evaluation": {
                "overall_score": 8.0,
                "eye_contact": 8.0,
                "posture": 8.0,
                "head_movement": 7.0,
                "facial_expression": 7.0,
                "gestures": 7.0,
                "visual_confidence": 8.0,
            },
            "nlp_evaluation": {
                "overall_score": 7.0,
                "vocabulary_score": 7.0,
                "grammar_score": 7.0,
                "communication_clarity_score": 7.0,
                "word_count": 11,
                "sentence_structure_score": 7.0,
            },
        }],
    )
    visible_copy = " ".join(
        report.strengths
        + report.weaknesses
        + report.improvements
        + report.recommendations
        + [report.overall_assessment]
        + [report.candidate_summary["headline"]]
        + report.candidate_summary["what_went_well"]
        + report.candidate_summary["what_to_work_on"]
    ).lower()

    assert report.status == "ok"
    assert report.overall_scores["answer"] > 0
    assert any("Answer Completeness".lower() in item for item in report.weaknesses)
    assert report.soft_skill_summary["content_score"] is not None
    assert report.soft_skill_summary["soft_skill_score"] is not None
    assert "not researched" not in visible_copy
    assert "citation" not in visible_copy
    assert len(report.graph_data["progression_trend"]) == 1
    json.dumps(report.to_dict()["graph_data"], allow_nan=False)


def test_invalid_and_invented_llm_payload_get_one_retry(monkeypatch) -> None:
    monkeypatch.setattr(insight_module, "INSIGHT_USE_LLM", True)
    agent = InsightAgent()
    responses = iter([
        "not json",
        '{"reasoning":"score 99","candidate_summary":{"headline":"x","what_went_well":[],"what_to_work_on":[],"next_steps":[]},"items":{}}',
    ])
    calls = []

    def fake_call(prompt: str) -> str:
        calls.append(prompt)
        return next(responses)

    agent._call_llm = fake_call
    facts = '{"score": 8.0}'
    result = agent._validated_llm_json("first", facts)

    assert result is None
    assert len(calls) == 2
    assert agent._llm_fallbacks == 1


def test_llm_payload_accepts_supplied_score_formatted_out_of_ten(monkeypatch) -> None:
    monkeypatch.setattr(insight_module, "INSIGHT_USE_LLM", True)
    agent = InsightAgent()
    agent._call_llm = lambda prompt: (
        '{"reasoning":"Your measured score is 8.0/10.",'
        '"candidate_summary":{"headline":"Your score is 8.0/10.",'
        '"what_went_well":["Answer Relevance is 8.0/10.","Answer Relevance is 8.0/10.",'
        '"Answer Relevance is 8.0/10."],'
        '"what_to_work_on":["Answer Completeness is 5.0/10.","Answer Completeness is 5.0/10.",'
        '"Answer Completeness is 5.0/10."],'
        '"next_steps":["Practise Answer Completeness.","Practise Answer Relevance.",'
        '"Review Answer Completeness."]},"items":{}}'
    )

    facts = (
        '{"score":8.0,"strengths":[{"name":"Answer Relevance","score":8.0}],'
        '"weaknesses":[{"name":"Answer Completeness","score":5.0}],"card_names":[]}'
    )
    result = agent._validated_llm_json("prompt", facts)

    assert result is not None
    assert agent._llm_fallbacks == 0


def test_importance_weights_cover_all_domains() -> None:
    assert sum(DOMAIN_IMPORTANCE_WEIGHTS.values()) == 100


def test_modality_graph_data_tracks_questions_and_omits_missing_metrics() -> None:
    agent = InsightAgent()
    questions = [
        {
            "source": "baseline",
            "time_taken_seconds": 20,
            "audio_evaluation": {
                "words_per_minute": 0,
                "filler_word_count": 0,
                "total_pause_seconds": 0,
                "fluency": 0,
            },
            "video_evaluation": None,
            "nlp_evaluation": {
                "grammar_error_count": 0,
                "word_count": 0,
                "communication_clarity_score": 0,
                "vocabulary_score": 0,
                "sentence_structure_score": 0,
                "english_consistency_score": 0,
            },
            "technical_evaluation": {"rating": 0},
        },
        {
            "source": "bank",
            "time_taken_seconds": 30,
            "audio_evaluation": None,
            "video_evaluation": {
                "overall_score": 7.0,
                "eye_contact": 8.0,
                "eye_contact_percentage": 0,
                "posture": 7.0,
                "posture_score": 7.0,
                "facial_expression": 6.0,
            },
            "nlp_evaluation": None,
            "technical_evaluation": None,
        },
        {
            "source": "ai_followup",
            "time_taken_seconds": 40,
            "audio_evaluation": {
                "words_per_minute": 120,
                "filler_word_count": 2,
                "total_pause_seconds": 4,
                "fluency": 8,
            },
            "video_evaluation": None,
            "nlp_evaluation": {
                "grammar_error_count": 1,
                "word_count": 12,
                "communication_clarity_score": 7,
                "vocabulary_score": 6,
                "sentence_structure_score": 7,
                "english_consistency_score": 8,
            },
            "technical_evaluation": {"rating": 8},
        },
    ]
    factors = {
        "audio": {
            "pace": 0,
            "fluency": 4,
            "volume": None,
            "pause_management": 7,
            "filler_word_score": 8,
            "hesitation_score": None,
        },
        "video": {
            "eye_contact": 8,
            "posture": 7,
            "head_movement": None,
            "facial_expression": 6,
            "gestures": None,
            "visual_confidence": None,
        },
        "nlp": {
            "communication_clarity": 0,
            "vocabulary": 6,
            "grammar": 4,
            "sentence_structure": 7,
            "english_consistency": 8,
        },
    }
    result = agent._build_modality_graph_data(
        question_results=questions,
        factor_averages=factors,
        overall_scores={"answer": 0, "audio": 4, "video": 7, "nlp": 6},
    )

    assert len(result["audio_factors"]) == 4
    assert len(result["video_factors"]) == 3
    assert len(result["nlp_factors"]) == 5
    assert len(result["voice_trend"]) == 2
    assert len(result["presence_trend"]) == 1
    assert len(result["language_trend"]) == 2
    assert len(result["progression_trend"]) == 3
    assert result["audio_factors"][0]["score"] == 0
    assert result["audio_factors"][0]["measured"] == {"value": 60.0, "unit": "WPM"}
    assert result["voice_trend"][0]["wpm"] == 0
    assert result["voice_trend"][0]["filler_count"] == 0
    assert result["voice_trend"][0]["pause_ratio"] == 0
    assert result["voice_trend"][1]["wpm"] == 120
    assert result["voice_trend"][1]["pause_ratio"] == 0.1
    assert result["presence_trend"][0]["eye_contact_pct"] == 0
    assert result["language_trend"][0]["word_count"] == 0
    assert "grammar_errors" not in result["language_trend"][0] or result["language_trend"][0]["grammar_errors"] == 0
    assert result["language_trend"][1]["grammar_errors"] == 1
    assert "answer_score" not in result["progression_trend"][1]
    assert result["progression_trend"][0]["answer_score"] == 0
    assert result["video_coverage"] == "analysed 1 of 3 answers"
    assert "volume" not in {item["key"] for item in result["audio_factors"]}
    json.dumps(result, allow_nan=False)


def test_no_video_graph_reports_zero_coverage_without_fake_points() -> None:
    result = InsightAgent()._build_modality_graph_data(
        question_results=[
            {"source": "baseline", "video_evaluation": None},
            {"source": "bank", "video_evaluation": None},
        ],
        factor_averages={"audio": {}, "video": {}, "nlp": {}},
        overall_scores={"answer": 0, "audio": None, "video": None, "nlp": 0},
    )

    assert result["video_factors"] == []
    assert result["presence_trend"] == []
    assert result["video_coverage"] == "analysed 0 of 2 answers"
    assert result["domain_radar"] == [
        {"domain": "answer", "score": 0},
        {"domain": "nlp", "score": 0},
    ]
