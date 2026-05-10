from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI, OpenAIError

from .config import get_settings


KEYWORDS = {
    "max": ["maximum", "highest", "peak", "max"],
    "min": ["minimum", "lowest", "least", "min"],
    "status": ["outage", "status", "o/s", "ls/gs", "load shedding", "generation shortfall"],
    "report": ["report", "summary", "brief", "generate"],
}


def select_context(question: str, records: list[dict[str, Any]], limit: int = 180) -> list[dict[str, Any]]:
    q = question.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        haystack = " ".join(
            str(record.get(key) or "")
            for key in ["date", "acc", "transmission_interface", "line_voltage", "line_nomenclature", "disco", "hour", "status"]
        ).lower()
        score = sum(2 for token in re.findall(r"[a-z0-9/.-]+", q) if len(token) > 2 and token in haystack)
        if record["status"] and any(word in q for word in KEYWORDS["status"]):
            score += 5
        if record["load_mw"] is not None and any(word in q for word in KEYWORDS["max"] + KEYWORDS["min"]):
            score += 2
        if score:
            scored.append((score, record))
    if not scored:
        return records[:limit]
    return [record for _, record in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def answer_question(question: str, records: list[dict[str, Any]], mode: str = "answer") -> str:
    settings = get_settings()
    context = select_context(question, records)
    if not settings.openai_api_key:
        return offline_answer(question, context)

    client = OpenAI(api_key=settings.openai_api_key)
    prompt_mode = "generate an operational report" if mode == "report" else "answer the operator's question"
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant for a Nigerian power transmission station. "
                        "Use only the provided databank records. Be precise with dates, line names, voltage levels, "
                        "hours, MW values, and operational statuses. If the data is insufficient, say what is missing. "
                        "Never claim to have written to Google Sheets."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Task: {prompt_mode}\n"
                        f"Question: {question}\n\n"
                        f"Databank records JSON:\n{json.dumps(context, ensure_ascii=True)}"
                    ),
                },
            ],
            timeout=30,
        )
        return response.output_text
    except OpenAIError as error:
        return f"AI request failed: {error}\n\n{offline_answer(question, context)}"


def offline_answer(question: str, records: list[dict[str, Any]]) -> str:
    numeric = [record for record in records if record["load_mw"] is not None]
    if not numeric:
        return (
            "OPENAI_API_KEY is not configured. I found matching operational-status records, "
            "but AI reporting is disabled. Configure the key to generate a full natural-language answer."
        )
    highest = max(numeric, key=lambda item: item["load_mw"])
    lowest = min(numeric, key=lambda item: item["load_mw"])
    return (
        "OPENAI_API_KEY is not configured, so this is a deterministic databank summary.\n\n"
        f"Matching records reviewed: {len(records)}.\n"
        f"Highest load: {highest['load_mw']} MW on {highest['date']} at {highest['hour']} "
        f"for {highest['line_nomenclature']} ({highest['transmission_interface']}, {highest['line_voltage']}).\n"
        f"Lowest load: {lowest['load_mw']} MW on {lowest['date']} at {lowest['hour']} "
        f"for {lowest['line_nomenclature']} ({lowest['transmission_interface']}, {lowest['line_voltage']})."
    )
