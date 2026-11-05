import json
import re

import httpx

from app.config import ENABLE_LLM_GRAMMAR, OLLAMA_MODEL, OLLAMA_URL


class GrammarAnalysisError(Exception):
    """Raised when grammar analysis cannot be completed."""


GRAMMAR_PROMPT = """Review only clear, observable English grammar issues in this interview answer.
Do not judge intelligence, personality, accent, nationality, or technical ability.
Do not mark normal conversational language, Indian English variation, or technical terms.
Return JSON only with grammar_score (1-10), error_count, errors[{text,correction,category,explanation}], and summary.
Include at most five specific errors. Do not invent errors. Keep the summary short.

Transcript:
"""


def _extract_json(text: str) -> dict:
    """
    Extract the first JSON object from an Ollama response.
    """
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(
        r"\{.*\}",
        text,
        flags=re.DOTALL,
    )

    if not match:
        raise GrammarAnalysisError(
            "Ollama did not return a JSON object."
        )

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise GrammarAnalysisError(
            "Ollama returned invalid JSON."
        ) from exc


def _validate_result(result: dict) -> dict:
    """
    Validate and normalize the grammar-analysis result.
    """
    grammar_score = result.get("grammar_score")

    if not isinstance(grammar_score, (int, float)):
        raise GrammarAnalysisError(
            "Grammar analysis did not return a valid score."
        )

    grammar_score = int(
        max(1, min(10, round(grammar_score)))
    )

    errors = result.get("errors")

    if not isinstance(errors, list):
        errors = []

    normalized_errors = []

    for error in errors:
        if not isinstance(error, dict):
            continue

        normalized_errors.append(
            {
                "text": str(
                    error.get("text", "")
                ),
                "correction": str(
                    error.get("correction", "")
                ),
                "category": str(
                    error.get(
                        "category",
                        "other",
                    )
                ),
                "explanation": str(
                    error.get(
                        "explanation",
                        "",
                    )
                ),
            }
        )
        if len(normalized_errors) == 5:
            break

    summary = str(
        result.get(
            "summary",
            "",
        )
    )

    return {
        "grammar_score": grammar_score,
        "error_count": len(
            normalized_errors
        ),
        "errors": normalized_errors,
        "summary": summary,
    }


def analyze_grammar(
    transcript_text: str,
    *,
    timeout_seconds: float = 60.0,
    deterministic_score: int | float | None = None,
) -> dict:
    """
    Analyze grammar using the local Ollama model.

    The model provides linguistic reasoning while this service
    validates and normalizes its output before returning it.
    """
    if not transcript_text or not transcript_text.strip():
        return {
            "grammar_score": 5,
            "error_count": 0,
            "errors": [],
            "summary": "No transcript was available for grammar analysis.",
        }

    if not ENABLE_LLM_GRAMMAR or len(transcript_text.split()) < 15:
        return {
            "grammar_score": (
                int(max(1, min(10, round(deterministic_score))))
                if deterministic_score is not None
                else 5
            ),
            "error_count": 0,
            "errors": [],
            "summary": (
                "Deterministic grammar score used; LLM analysis is disabled."
                if not ENABLE_LLM_GRAMMAR
                else "Answer was too short for contextual grammar analysis."
            ),
        }

    prompt = (
        GRAMMAR_PROMPT
        + transcript_text.strip()
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": "30m",
        "options": {
            "num_predict": 300,
            "temperature": 0,
        },
    }

    try:
        response = httpx.post(
            OLLAMA_URL,
            json=payload,
            timeout=timeout_seconds,
        )
    except httpx.RequestError as exc:
        raise GrammarAnalysisError(
            f"Could not connect to Ollama: {exc}"
        ) from exc

    if response.status_code != 200:
        raise GrammarAnalysisError(
            "Ollama returned HTTP "
            f"{response.status_code}: "
            f"{response.text[:500]}"
        )

    try:
        response_data = response.json()
    except ValueError as exc:
        raise GrammarAnalysisError(
            "Ollama returned a non-JSON HTTP response."
        ) from exc

    model_output = response_data.get(
        "response",
        "",
    )

    if not model_output:
        raise GrammarAnalysisError(
            "Ollama returned an empty response."
        )

    result = _extract_json(model_output)

    return _validate_result(result)