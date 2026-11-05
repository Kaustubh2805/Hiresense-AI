from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import OLLAMA_MODEL, OLLAMA_URL
from app.services.skills_taxonomy import SKILLS_TAXONOMY, find_skills


logger = logging.getLogger(__name__)


class Experience(BaseModel):
    title: str = ""
    company: str = ""
    duration: str = ""
    highlights: list[str] = Field(default_factory=list)


class ResumeParse(BaseModel):
    experiences: list[Experience] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    summary: str = ""
    total_years_experience: float = 0
    skills: list[str] = Field(default_factory=list)


def _estimate_years(text: str) -> float:
    years = [int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", text)]
    if len(years) < 2:
        return 0.0
    return round(max(0, min(50, max(years) - min(years))), 1)


def _heuristic_parse(text: str) -> ResumeParse:
    sections: dict[str, list[str]] = {}
    current_section = "summary"
    section_names = {
        "experience": ("experience", "work experience", "employment", "professional experience"),
        "education": ("education", "academic background"),
        "projects": ("projects", "personal projects"),
        "summary": ("summary", "profile", "objective", "about me"),
    }

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = re.sub(r"[^a-z ]", "", line.lower()).strip()
        matched_section = next(
            (key for key, headings in section_names.items() if normalized in headings),
            None,
        )
        if matched_section:
            current_section = matched_section
            sections.setdefault(current_section, [])
        else:
            sections.setdefault(current_section, []).append(line)

    experience_lines = sections.get("experience", [])
    experiences: list[Experience] = []
    for line in experience_lines:
        if re.search(r"\b(?:19|20)\d{2}\b", line):
            experiences.append(
                Experience(
                    title=line[:120],
                    duration=line[:120],
                )
            )

    summary_lines = sections.get("summary", [])
    summary = " ".join(summary_lines[:4])[:600]
    education = [line[:200] for line in sections.get("education", [])[:12]]
    return ResumeParse(
        experiences=experiences,
        education=education,
        summary=summary,
        total_years_experience=_estimate_years(text),
        skills=find_skills(text),
    )


def _parse_with_ollama(text: str) -> ResumeParse | None:
    prompt = (
        "Parse this resume into JSON with experiences [{title,company,duration,highlights}], "
        "education (strings), summary, total_years_experience (number), and skills (strings). "
        "Use only evidence in the resume. Return JSON only.\n\n"
        f"Resume:\n{text[:6000]}"
    )
    try:
        response = httpx.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "keep_alive": "30m",
                "options": {"temperature": 0, "num_predict": 900},
            },
            timeout=60,
        )
        response.raise_for_status()
        result = json.loads(response.json().get("response", ""))
        return ResumeParse.model_validate(result)
    except (httpx.HTTPError, ValueError, ValidationError, TypeError) as exc:
        logger.warning("Resume structured parse unavailable; using heuristic parser: %s", exc)
        return None


def parse_resume(text: str) -> dict[str, Any]:
    parsed = _parse_with_ollama(text)
    parse_quality = "full" if parsed is not None else "basic"
    if parsed is None:
        parsed = _heuristic_parse(text)

    deterministic = find_skills(text)
    taxonomy_by_alias = {
        alias.casefold(): canonical
        for canonical, aliases in SKILLS_TAXONOMY.items()
        for alias in (canonical, *aliases)
    }
    validated_llm_skills = [
        taxonomy_by_alias[skill.strip().casefold()]
        for skill in parsed.skills
        if skill.strip().casefold() in taxonomy_by_alias
    ]
    parsed.skills = list(dict.fromkeys([*deterministic, *validated_llm_skills]))
    return {
        **parsed.model_dump(),
        "parse_quality": parse_quality,
    }


def extract_resume_text(data: bytes, extension: str) -> str:
    if extension == ".pdf":
        from io import BytesIO
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if extension == ".docx":
        from io import BytesIO
        from docx import Document

        document = Document(BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError("Only PDF and DOCX resumes are supported.")
