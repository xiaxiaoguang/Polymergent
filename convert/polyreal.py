"""PolyReal json / jsonl -> polymer_bench tasks."""

from __future__ import annotations

import json
from pathlib import Path

from .common import STRUCT_RE, as_list, as_str, iter_files, make_task

POLYREAL_CAT = {
    "qa": "KnowledgeQA",
    "rank": "PropQA",
    "safe": "ProtocolQA",
    "spectrum": "DbQA",
    "table": "DbQA",
    "raw": "DbQA",
}


def load_records(path: Path) -> list[dict]:
    if path.suffix.lower() == ".jsonl":
        recs = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    recs.append(json.loads(line))
        return recs
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "records", "items"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def convert_polyreal(raw_dir: Path) -> list[dict]:
    root = raw_dir / "polyreal"
    candidates = [root / "PolyReal.json", root / "data" / "train.jsonl"]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        extras = iter_files(root, ("*.json", "*.jsonl"))
        path = extras[0] if extras else None
    if path is None:
        return []
    rows = []
    for rec in load_records(path):
        src_cat = str(rec.get("category") or rec.get("Type") or "qa").lower()
        if src_cat not in POLYREAL_CAT:
            src_cat = str(rec.get("category") or "qa").lower()
        answer = rec.get("Answer")
        if answer is None:
            answer = rec.get("answer")
        topic = as_str(rec.get("Topic") or rec.get("Type"))
        family = POLYREAL_CAT.get(src_cat, "KnowledgeQA")
        question = as_str(rec.get("Question") or rec.get("question"))
        if family == "KnowledgeQA" and STRUCT_RE.search(topic + " " + question):
            family = "StructQA"
        rid = rec.get("id")
        rows.append(
            make_task(
                tid=f"polyreal_{rid}",
                source="PolyReal",
                source_id=str(rid),
                category=family,
                subfield=topic,
                answer_type="ranking" if src_cat == "rank" else "exactMatch",
                question=question,
                ideal=as_str(answer),
                keywords=as_list(rec.get("Keywords") or rec.get("Key_Points")),
                mm=bool(rec.get("mm")),
                asset=as_str(rec.get("Path")),
                license_note="PolyReal (Liu et al., arXiv:2604.02934). Use the official dataset license.",
                extra={"polyreal_category": src_cat},
            )
        )
    return rows
