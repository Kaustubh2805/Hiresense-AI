import json
import requests

from app.config import OLLAMA_MODEL, OLLAMA_URL

from app.schemas.evaluation import AnswerEvaluationResult




# =========================================================
# FOLLOW-UP QUESTION GENERATION
# =========================================================

def generate_followup_question(
    question_text: str,
    answer_text: str,
    job_profile: str,
    followup_instruction: str | None = None,
) -> str:

    agent_instruction = (
        followup_instruction.strip()
        if followup_instruction
        else "Choose the most relevant area to probe based on the candidate's answer."
    )

    prompt = f"""
You are an AI interviewer conducting a technical mock interview.

JOB PROFILE:
{job_profile}

ORIGINAL QUESTION:
{question_text}

CANDIDATE'S ANSWER:
{answer_text}

INTERVIEW AGENT INSTRUCTION:
{agent_instruction}

Generate ONE relevant technical follow-up question.

The follow-up must help assess the candidate's understanding
of the original topic while following the Interview Agent's instruction.

Rules:

- Directly relate to the original question and candidate's answer.
- Follow the Interview Agent's instruction when generating the question.
- Do not repeat the original question.
- If the answer is vague, ask for clarification.
- If the answer is incomplete, target the missing concept.
- If the answer is partially correct, investigate the weak area.
- If the answer is correct but basic, test deeper understanding.
- If appropriate, ask for a practical or real-world example.
- Do not provide the answer.
- Do not add explanations.
- Return ONLY the question.
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                },
            },
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        followup = data.get("response", "").strip()

        if not followup:
            raise ValueError(
                "Ollama returned an empty follow-up question."
            )

        return followup

    except requests.RequestException as error:
        raise RuntimeError(
            f"Failed to communicate with Ollama: {error}"
        )
# =========================================================
# ANSWER EVALUATION
# =========================================================

def evaluate_answer(
    question_text: str,
    answer_text: str,
    evaluation_type: str,
) -> AnswerEvaluationResult:

    if evaluation_type == "bank":

        evaluation_instructions = """
Evaluate the candidate's answer strictly against the question.

This is a question from a predefined technical question bank.

The candidate must actually answer what the question asks.

Do NOT award a high score simply because the answer mentions
the correct general topic.

Example:

Question:
"What is a primary key?"

Answer:
"It is something used in a database."

This is incomplete and should receive a low score.

Example:

Question:
"What is a primary key?"

Answer:
"A primary key uniquely identifies each record in a table."

This directly answers the question and should receive a high score.

Evaluation rules:

- Do not infer knowledge that the candidate did not demonstrate.
- Do not give credit for concepts the candidate did not mention.
- Reduce completeness when important concepts are missing.
- Reduce technical_understanding when understanding is superficial.
- A short answer can receive a high score if it completely answers
  the question.
- A long answer should not receive a high score merely because it
  contains many words.
- Correctness measures technical accuracy.
- Relevance measures whether the answer addresses the question.
- Completeness measures whether important required concepts were covered.
- Clarity measures how clearly the answer is expressed.
- Coherence measures whether the explanation is logically structured.
- Technical understanding measures the depth of demonstrated knowledge.

Follow-up decision:

needs_followup=true when:

- The answer is incomplete.
- The answer is vague.
- The answer is partially correct.
- The answer demonstrates only superficial understanding.
- An important concept is missing.
- A follow-up would meaningfully test the candidate's understanding.

needs_followup=false when:

- The answer directly answers the question.
- The answer is technically correct.
- The answer is sufficiently complete.
- The candidate demonstrates adequate or strong understanding.

Do not require an example when the question only asks for a definition.
"""

    else:

        evaluation_instructions = """
Evaluate the candidate's answer to an AI-generated follow-up question.

There may not be one exact expected answer.

Focus on:

- Whether the answer directly addresses the follow-up.
- Relevance.
- Completeness.
- Clarity.
- Coherence.
- Technical understanding.
- Whether the candidate logically builds upon the discussion.

Do not mark an answer incorrect merely because it uses
different wording from an expected answer.

This is already a follow-up question.

Do NOT request another follow-up.

Therefore:
needs_followup must always be false.
"""

    prompt = f"""
You are an expert technical interviewer evaluating a candidate.

{evaluation_instructions}

The candidate may answer in English, Hindi, or Hinglish, including Hindi
written in the Latin alphabet. Evaluate the technical meaning across these
languages; do not treat language choice or English fluency as technical
correctness. If transcription makes the answer unclear, acknowledge that
uncertainty instead of inventing an answer.
Never describe Hindi/Hinglish phrasing as unclear to non-native speakers or
as a weakness. Do not confuse speech-recognition errors with the candidate's
understanding. In hypothesis-testing answers, "galti se reject" means
incorrectly rejecting the null hypothesis (Type I/false positive), and
"reject nahi kar paana" means failing to reject it (the Type II/false-negative
idea when the null hypothesis is false). Credit these meanings when supported
by the candidate's words; if the transcript is uncertain, say so.

QUESTION:
{question_text}

CANDIDATE ANSWER:
{answer_text}

Return ONLY valid JSON.

You MUST include ALL of the following fields:

{{
    "rating": 1,
    "correctness": 0,
    "relevance": 0,
    "completeness": 0,
    "clarity": 0,
    "coherence": 0,
    "technical_understanding": 0,
    "verdict": "weak",
    "feedback": "short feedback",
    "needs_followup": false
}}

Field requirements:

- rating: integer from 1 to 10
- correctness: number from 0 to 10, or null
- relevance: number from 0 to 10
- completeness: number from 0 to 10
- clarity: number from 0 to 10
- coherence: number from 0 to 10
- technical_understanding: number from 0 to 10
- verdict: one of "strong", "adequate", "partial", "weak", "incorrect"
- feedback: one or two short sentences
- needs_followup: true or false

Rating:

1-2 = completely incorrect or irrelevant
3-4 = weak understanding
5-6 = partial/basic understanding
7-8 = good understanding
9-10 = excellent understanding

IMPORTANT:
You MUST include every field.
Do not omit coherence.
Do not include markdown.
Do not include ```json.
Do not include explanations outside the JSON.
"""

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                },
            },
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        raw_result = data.get("response", "").strip()

        if not raw_result:
            raise ValueError(
                "Ollama returned an empty evaluation."
            )

        parsed = json.loads(raw_result)

        # -------------------------------------------------
        # SAFETY DEFAULTS
        # -------------------------------------------------

        # Small models occasionally omit a field.
        # Give the missing dimension a neutral value rather
        # than crashing the interview.

        if "coherence" not in parsed:
            parsed["coherence"] = 0

        if "correctness" not in parsed:
            parsed["correctness"] = None

        if "relevance" not in parsed:
            parsed["relevance"] = 0

        if "completeness" not in parsed:
            parsed["completeness"] = 0

        if "clarity" not in parsed:
            parsed["clarity"] = 0

        if "technical_understanding" not in parsed:
            parsed["technical_understanding"] = 0

        if "needs_followup" not in parsed:
            parsed["needs_followup"] = False

        if "verdict" not in parsed:
            parsed["verdict"] = "weak"

        if "feedback" not in parsed:
            parsed["feedback"] = "The answer could be improved."

        evaluation = AnswerEvaluationResult.model_validate(parsed)

        # -------------------------------------------------
        # AI FOLLOW-UP SAFETY RULE
        # -------------------------------------------------

        if evaluation_type == "ai_followup":
            evaluation.needs_followup = False

        return evaluation

    except requests.RequestException as error:

        raise RuntimeError(
            f"Failed to communicate with Ollama: {error}"
        )

    except (ValueError, json.JSONDecodeError) as error:

        raise RuntimeError(
            f"Invalid evaluation returned by Ollama: {error}"
        )