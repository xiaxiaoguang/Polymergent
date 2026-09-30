"""Parse model output and score against gold."""

from __future__ import annotations

import json
import re


def parse_response(response: str, answer_type: str) -> str:
    if response is None:
        return ""
    text = str(response).strip()
    patterns = (
        r"<solution>\s*(.*?)\s*</solution>",
        r"<solution>\s*(.*?)\s*$",
        r"\[ANSWER\]\s*(.*?)\s*\[/ANSWER\]",
        r"<answer>\s*(.*?)\s*</answer>",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            if extracted:
                text = extracted
                break
    text = re.sub(r"</?(?:execute|observation|think)[^>]*>", " ", text, flags=re.IGNORECASE).strip()
    if answer_type == "multipleChoice":
        lone = re.search(r"^\s*([A-Za-z])\s*[.)]?\s*$", text)
        if lone:
            return lone.group(1).upper()
        letter_match = re.search(r"\b([A-Za-z])\b", text)
        if letter_match:
            return letter_match.group(1).upper()
        return text[0].upper() if text else ""
    return text.strip()


def normalize_text(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9.+-]+", " ", text)
    return text.strip()


def parse_rank_list(text: str) -> list[str] | None:
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None
    try:
        loaded = json.loads(raw)
        if isinstance(loaded, (list, tuple)) and loaded:
            return [str(x).strip().lower() for x in loaded if str(x).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    cleaned = raw.replace("→", ">").replace("->", ">").replace("≥", ">").replace(">=", ">")
    if ">" in cleaned:
        chain = re.search(r"([A-Za-z0-9_]+(?:\s*>\s*[A-Za-z0-9_]+)+)", cleaned)
        if chain:
            parts = [p.strip().lower() for p in chain.group(1).split(">") if p.strip()]
            if len(parts) >= 2:
                return parts
    quoted = re.findall(r"['\"]([A-Za-z0-9_]+)['\"]", raw)
    labelish = [q.lower() for q in quoted if len(q) <= 12 and q.lower() not in {"type", "text", "label", "value"}]
    if len(labelish) >= 2:
        return labelish
    letters = re.findall(r"(?<![A-Za-z])([A-Da-d])(?![A-Za-z])", raw)
    if len(letters) >= 2:
        return [c.lower() for c in letters]
    return None


def score_one(pred: str, gold: str, answer_type: str = "exactMatch", tolerance_rel: float = 0.15) -> float:
    pred_s = "" if pred is None else str(pred).strip()
    gold_s = "" if gold is None else str(gold).strip()
    if not pred_s:
        return 0.0
    if answer_type == "multipleChoice":
        return 1.0 if pred_s.upper() == gold_s.upper() else 0.0
    gold_rank = parse_rank_list(gold_s)
    pred_rank = parse_rank_list(pred_s)
    if gold_rank and len(gold_rank) >= 2:
        if not pred_rank:
            return 0.0
        n = min(len(gold_rank), len(pred_rank))
        exact_prefix = sum(int(gold_rank[i] == pred_rank[i]) for i in range(n))
        if gold_rank == pred_rank:
            return 1.0
        if len(gold_rank) == len(pred_rank):
            return exact_prefix / len(gold_rank)
        return 0.0
    gold_nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", gold_s)
    pred_nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", pred_s)
    if gold_nums and pred_nums and not gold_rank:
        try:
            pred_n = float(pred_nums[0])
            gold_n = float(gold_nums[0])
            denom = max(abs(gold_n), 1e-12)
            return 1.0 if abs(pred_n - gold_n) / denom <= tolerance_rel else 0.0
        except (IndexError, ValueError, TypeError):
            pass
    if normalize_text(pred_s) == normalize_text(gold_s):
        return 1.0
    gold_toks = normalize_text(gold_s).split()
    if len(gold_toks) < 8:
        return 0.0
    overlap = len(set(gold_toks) & set(normalize_text(pred_s).split())) / len(set(gold_toks))
    return 1.0 if overlap >= 0.5 else overlap
