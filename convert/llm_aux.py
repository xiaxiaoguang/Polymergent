"""Optional LLM assistance for ambiguous semantic task labels."""

from __future__ import annotations

import json
import re
from typing import Any

ALLOWED_FAMILIES = {
    "PropertyPrediction",
    "MaterialIdentification",
    "SynthesisProtocol",
    "StructureReasoning",
    "ReactionAndDesign",
    "KnowledgeReasoning",
}
PROPERTY_SUBCLASSES = {
    "thermal_phase_property",
    "electronic_energy_property",
    "optical_dielectric_property",
    "transport_barrier_property",
    "mechanical_physical_property",
    "solution_interaction_property",
    "other_property",
}


def _parse_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def enrich_tasks(
    tasks: list[dict[str, Any]],
    *,
    limit: int = 100,
    model: str | None = None,
) -> int:
    """Use polymer.llm only for ambiguous non-numeric labels.

    The import is intentionally lazy. Normal dataset conversion remains offline and
    never requires provider credentials.
    """
    try:
        from polymer.llm import get_llm
    except ImportError as exc:
        raise RuntimeError(
            "LLM enrichment requires the workspace polymer package on PYTHONPATH."
        ) from exc

    candidates = []
    for task in tasks:
        keywords = task.get("keywords") or []
        family = keywords[0] if keywords else ""
        subclass = keywords[1] if len(keywords) > 1 else ""
        if task.get("answer_type") == "numeric":
            continue
        if family in {"knowledge_reasoning", "property_prediction"} and (
            not subclass or subclass == "other_property"
        ):
            candidates.append(task)
        if len(candidates) >= limit:
            break
    if not candidates:
        return 0

    llm = get_llm(model=model) if model else get_llm()
    changed = 0
    for task in candidates:
        prompt = (
            "Classify this polymer evaluation task. Return JSON only with keys "
            "task_family, subclass, difficulty. Do not change the answer.\n"
            "Allowed task_family: MaterialIdentification, SynthesisProtocol, "
            "StructureReasoning, ReactionAndDesign, KnowledgeReasoning.\n"
            "For PropertyPrediction, subclass must be one of: "
            + ", ".join(sorted(PROPERTY_SUBCLASSES))
            + ". For other task families, subclass may be an empty string.\n"
            "difficulty must be an integer from 1 to 4.\n\n"
            + json.dumps(
                {
                    "category": task.get("category"),
                    "subfield": task.get("subfield"),
                    "question": task.get("question"),
                },
                ensure_ascii=False,
            )
        )
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        parsed = _parse_json(str(content))
        if not parsed:
            continue
        family = parsed.get("task_family")
        subclass = parsed.get("subclass") or ""
        difficulty = parsed.get("difficulty")
        family_keyword = re.sub(r"(?<!^)(?=[A-Z])", "_", str(family or "")).lower()
        allowed_family_keywords = {
            re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower(): value
            for value in ALLOWED_FAMILIES
        }
        if family_keyword not in allowed_family_keywords:
            continue
        if family_keyword == "property_prediction" and subclass not in PROPERTY_SUBCLASSES:
            continue
        if not isinstance(difficulty, int) or difficulty not in {1, 2, 3, 4}:
            continue
        task["difficulty"] = difficulty
        task["keywords"] = [family_keyword]
        if subclass:
            task["keywords"].append(subclass)
        changed += 1
    return changed
