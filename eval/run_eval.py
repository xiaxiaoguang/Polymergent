#!/usr/bin/env python3
"""Config-driven polymer-agent evaluation loop.

New benchmark sources do not require edits here. Register them in
`eval_config.json` (a split + optional source_regex) after
`convert_datasets.py` writes `external_tasks.json`.

Usage
-----
    python run_eval.py --list-splits
    python run_eval.py --list-sources
    python run_eval.py --list-field keywords
    python run_eval.py --mode harness
    python run_eval.py --mode agent --split numeric --n 10
    python run_eval.py --mode llm --split polyreal --n 5
    python run_eval.py --config path/to/eval_config.json --split opc25
    python run_eval.py --filter keywords_in=density,numeric --filter subfield=density
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "eval_config.json"

JUDGE_PROMPT = """You are a strict grading assistant for polymer-science eval items.
Compare GOLD to the model OUTPUT and decide whether the model got the same answer.

Rules:
- Ranking: order matters. ['b','a','c','d'] equals "b > a > c > d" or "b, a, c, d".
  The reverse order is WRONG. Extra words around a clear ranking are OK.
- Numeric: extract the first predicted number. Correct if relative error <= TOLERANCE.
- Multiple choice: only the letter matters.
- Open / protocol: correct only if the OUTPUT covers the same key claims as GOLD.
  Style and length may differ. Do not reward generic safety talk that misses GOLD faults.
- If OUTPUT has no usable answer, score 0.

Return ONLY JSON:
{{"parsed":"<normalized answer you extracted>","equivalent":true_or_false,"score":0.0_to_1.0,"reason":"<one sentence>"}}

CATEGORY: {category}
TOLERANCE: {tolerance}
GOLD: {gold}
OUTPUT:
{output}
"""


# ---------------------------------------------------------------------------
# config / paths
# ---------------------------------------------------------------------------

def load_eval_config(path: Path | None) -> dict:
    candidates = []
    if path:
        candidates.append(Path(path))
    candidates.extend(
        [
            DEFAULT_CONFIG,
            HERE / "eval_config.json",
            Path.cwd() / "eval_config.json",
        ]
    )
    for cand in candidates:
        if cand.is_file():
            return json.loads(cand.read_text(encoding="utf-8")), cand
    return {
        "version": "0.0.0",
        "data": {"candidates": [str(HERE / "data")], "task_files": ["external_tasks.json"]},
        "runtime": {},
        "scoring": {},
        "splits": {
            "all": {"dataset": "All", "answer_type": None, "filters": {}},
        },
    }, None


def resolve_data_dir(cfg: dict, override: str | None) -> Path:
    if override:
        return Path(override)
    candidates = []
    for raw in (cfg.get("data") or {}).get("candidates") or []:
        p = Path(raw)
        if not p.is_absolute():
            candidates.append((HERE / p).resolve())
            candidates.append((Path.cwd() / p).resolve())
        else:
            candidates.append(p)
    candidates.extend([HERE / "data", HERE / "polymer", Path.cwd() / "data"])
    for p in candidates:
        if p.exists():
            return p
    return candidates[0] if candidates else HERE / "data"


def load_env_files() -> list[str]:
    loaded = []
    try:
        from dotenv import load_dotenv
    except ImportError:
        return loaded
    candidates = [Path.cwd() / ".env", HERE / ".env", HERE.parent / ".env"]
    seen = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        load_dotenv(path, override=False)
        loaded.append(str(resolved))
    return loaded


def load_task_classes():
    try:
        from polymer.task.polymer_bench import polymer_bench, polymer_hle, polymer_lab_bench

        origin = "polymer.task.polymer_bench"
    except ImportError:
        from polymer.task.polymer_bench import polymer_bench, polymer_hle, polymer_lab_bench

        origin = "local polymer_bench"
    return polymer_bench, polymer_hle, polymer_lab_bench, origin


# ---------------------------------------------------------------------------
# message / judge helpers (unchanged behaviour)
# ---------------------------------------------------------------------------

def _content_blocks_to_text(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "content") and not isinstance(value, (str, bytes, dict, list, tuple)):
        return _content_blocks_to_text(value.content)
    if isinstance(value, dict):
        for key in ("text", "output_text", "content", "message"):
            if key in value and value[key] is not None and key != "type":
                inner = _content_blocks_to_text(value[key])
                if inner:
                    return inner
        return ""
    if isinstance(value, (list, tuple)):
        parts = [_content_blocks_to_text(v) for v in value]
        return "\n".join(p for p in parts if p)
    return str(value)


def _maybe_literal(text: str):
    raw = str(text).strip()
    if not raw or raw[0] not in "[{":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return None


def _parse_judge_json(text: str) -> dict | None:
    if text is None:
        return None
    candidates = [text]
    flattened = _content_blocks_to_text(text)
    if flattened and flattened not in candidates:
        candidates.append(flattened)
    literal = _maybe_literal(flattened)
    if literal is not None:
        nested = _content_blocks_to_text(literal)
        if nested:
            candidates.append(nested)
        if isinstance(literal, dict) and ("score" in literal or "equivalent" in literal or "parsed" in literal):
            return literal
    for cand in candidates:
        raw = str(cand or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE | re.DOTALL).strip()
        loaded = _maybe_literal(raw)
        if isinstance(loaded, dict) and ("score" in loaded or "equivalent" in loaded or "parsed" in loaded):
            return loaded
        if isinstance(loaded, list):
            inner = _parse_judge_json(_content_blocks_to_text(loaded))
            if inner:
                return inner
        for match in re.finditer(r"\{[^{}]*\}", raw, flags=re.DOTALL):
            blob = match.group(0)
            try:
                data = json.loads(blob)
            except json.JSONDecodeError:
                try:
                    data = ast.literal_eval(blob)
                except (ValueError, SyntaxError):
                    continue
            if isinstance(data, dict) and ("score" in data or "equivalent" in data or "parsed" in data):
                return data
        unescaped = raw.replace('\\"', '"').replace("\\'", "'")
        if unescaped != raw:
            inner = _parse_judge_json(unescaped)
            if inner:
                return inner
    return None


def extract_agent_answer(result):
    if isinstance(result, tuple) and len(result) >= 2:
        return result[1]
    if hasattr(result, "content"):
        return result.content
    return result


def extract_llm_answer(result):
    if result is None:
        return ""
    if hasattr(result, "content"):
        return _content_blocks_to_text(result.content)
    if isinstance(result, tuple) and len(result) >= 2:
        return _content_blocks_to_text(result[1])
    if isinstance(result, dict):
        return _content_blocks_to_text(result)
    return _content_blocks_to_text(result)


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(_as_text(v) for v in value)
    return str(value)


def get_judge_llm(model: str):
    from polymer.config import default_config
    from polymer.llm import get_llm

    load_env_files()
    return get_llm(
        model,
        source=default_config.source,
        base_url=default_config.base_url,
        api_key=default_config.api_key if default_config.api_key else "EMPTY",
        config=default_config,
    )


def judge_one(judge_llm, item: dict, output: str, gold: str, tolerance: float = 0.15) -> dict:
    prompt = JUDGE_PROMPT.format(
        category=item.get("category") or "",
        tolerance=tolerance,
        gold=gold,
        output=(output or "")[:8000],
    )
    raw = judge_llm.invoke(prompt)
    text = extract_llm_answer(raw)
    data = _parse_judge_json(text) or {}
    equivalent = bool(data.get("equivalent"))
    try:
        score = float(data.get("score"))
    except (TypeError, ValueError):
        score = 1.0 if equivalent else 0.0
    score = min(1.0, max(0.0, score))
    return {
        "parsed": data.get("parsed"),
        "equivalent": equivalent,
        "score": score,
        "reason": data.get("reason") or "",
        "raw": str(text)[:2000],
    }


# ---------------------------------------------------------------------------
# split selection from config
# ---------------------------------------------------------------------------

def _series(df: pd.DataFrame, col: str) -> pd.Series:
    if col in df.columns:
        return df[col]
    return pd.Series([""] * len(df), index=df.index)


def _truthy_series(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.fillna(False)
    lowered = s.astype(str).str.strip().str.lower()
    return lowered.isin(["1", "true", "t", "yes", "y"])


def _has_asset(df: pd.DataFrame) -> pd.Series:
    """True when the item is multimodal / needs an image file."""
    mm = pd.Series(False, index=df.index)
    if "mm" in df.columns:
        mm = mm | _truthy_series(df["mm"])
    if "asset" in df.columns:
        asset = df["asset"]
        nonempty = asset.notna() & asset.astype(str).str.strip().ne("") & ~asset.astype(str).str.lower().isin(
            ["none", "null", "nan"]
        )
        mm = mm | nonempty
    return mm


_RESERVED_FILTERS = {"mm", "exclude_asset", "require_asset"}
_FILTER_SUFFIXES = (
    "_not_startswith",
    "_startswith",
    "_has_number",
    "_contains",
    "_regex",
    "_prefix",
    "_only",
    "_all",
    "_in",
    "_eq",
)


def _to_list(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x is not None and str(x).lower() != "nan"]
    if isinstance(v, (tuple, set)):
        return [str(x) for x in v]
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none", "[]"}:
        return []
    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, (list, tuple, set)):
                return [str(x) for x in parsed]
        except (ValueError, SyntaxError):
            pass
    return [s]


def _is_listish(series: pd.Series) -> bool:
    sample = series.dropna().head(32)
    if sample.empty:
        return False
    return any(
        isinstance(v, (list, tuple, set)) or (isinstance(v, str) and v[:1] == "[")
        for v in sample
    )


def _split_filter_key(key: str) -> tuple[str, str]:
    if key in _RESERVED_FILTERS:
        return key, "reserved"
    for suf in _FILTER_SUFFIXES:
        if key.endswith(suf):
            return key[: -len(suf)], suf[1:]
    return key, "eq"


def _as_str_set(raw_val) -> set[str]:
    if isinstance(raw_val, (list, tuple, set)):
        return {str(x) for x in raw_val}
    return {str(raw_val)}


def list_field_values(df: pd.DataFrame, col: str, top_n: int | None = None) -> list[str]:
    """Print distinct values of any column (flattens list columns such as keywords)."""
    if col not in df.columns:
        print(f"{col!r} not in frame; columns={list(df.columns)}")
        return []
    s = _series(df, col)
    if _is_listish(s):
        vals = [x for cell in s.map(_to_list) for x in cell]
    else:
        vals = [str(x) for x in s.tolist() if pd.notna(x) and str(x).lower() not in {"nan", "none"}]
    counts = Counter(vals)
    items = counts.most_common(top_n)
    print(f"unique {col}: {len(counts)}  (from {len(df)} tasks)")
    for k, n in items:
        print(f"  [{n:4d}] {k}")
    return [k for k, _ in items]


def apply_filters(df: pd.DataFrame, filters: dict | None) -> pd.DataFrame:
    """Filter on any task-dict column.

    Key patterns (col is any frame column, e.g. keywords, subfield, unit, source):
      col / col_eq              exact string match (list-col: membership)
      col_in                    scalar in list, or list-col intersects list
      col_all                   list-col contains every given value
      col_only                  list-col set equals given set
      col_regex                 case-insensitive regex on cell / any list item
      col_contains              case-insensitive substring
      col_startswith / col_prefix
      col_not_startswith
      col_has_number            cell contains a digit
    Reserved: mm, exclude_asset, require_asset
    Legacy keys (source_regex, id_prefix, ideal_has_number, ...) keep working.
    """
    if not filters:
        return df
    out = df

    for raw_key, raw_val in filters.items():
        if raw_val is None:
            continue
        col, op = _split_filter_key(str(raw_key))

        if op == "reserved":
            if col == "mm":
                want_mm = bool(raw_val)
                out = out[_has_asset(out) == want_mm] if want_mm else out[~_has_asset(out)]
            elif col == "exclude_asset" and raw_val:
                n_before = len(out)
                out = out[~_has_asset(out)]
                print(f"exclude_asset: dropped {n_before - len(out)} tasks that need images; kept {len(out)}")
            elif col == "require_asset" and raw_val:
                out = out[_has_asset(out)]
            continue

        if col not in out.columns:
            print(f"apply_filters: skip unknown column {col!r} (key={raw_key})")
            continue

        series = _series(out, col)
        listish = _is_listish(series)
        lists = series.map(_to_list) if listish else None
        text = series.astype(str)

        if op == "eq":
            want = str(raw_val)
            if listish:
                out = out[lists.map(lambda xs, w=want: w in xs)]
            else:
                out = out[text == want]
        elif op == "in":
            allowed = _as_str_set(raw_val)
            if listish:
                out = out[lists.map(lambda xs, a=allowed: bool(a.intersection(xs)))]
            else:
                out = out[text.isin(allowed)]
        elif op == "all":
            needed = _as_str_set(raw_val)
            cells = lists if listish else text.map(lambda s: [s])
            out = out[cells.map(lambda xs, n=needed: n.issubset(xs))]
        elif op == "only":
            exact = _as_str_set(raw_val)
            cells = lists if listish else text.map(lambda s: [s])
            out = out[cells.map(lambda xs, e=exact: set(xs) == e)]
        elif op == "regex":
            pat = str(raw_val)
            if listish:
                out = out[lists.map(lambda xs, p=pat: any(re.search(p, x, flags=re.I) for x in xs))]
            else:
                out = out[text.str.contains(pat, case=False, na=False, regex=True)]
        elif op == "contains":
            needle = str(raw_val).lower()
            if listish:
                out = out[lists.map(lambda xs, n=needle: any(n in x.lower() for x in xs))]
            else:
                out = out[text.str.lower().str.contains(re.escape(needle), na=False, regex=True)]
        elif op in {"startswith", "prefix"}:
            pref = str(raw_val)
            out = out[text.str.startswith(pref)]
        elif op == "not_startswith":
            pref = str(raw_val)
            out = out[~text.str.startswith(pref)]
        elif op == "has_number":
            if raw_val:
                out = out[text.str.contains(r"[-+]?\d", regex=True, na=False)]
        else:
            print(f"apply_filters: skip unknown op {op!r} on {col}")

    return out


def apply_sort(df: pd.DataFrame, spec: dict | None) -> pd.DataFrame:
    if not spec:
        return df
    by = spec.get("by")
    ascending = bool(spec.get("ascending", True))
    if by == "question_len":
        key = _series(df, "question").astype(str).str.len()
        return df.assign(_sort_key=key).sort_values("_sort_key", ascending=ascending).drop(columns=["_sort_key"])
    if by and by in df.columns:
        return df.sort_values(by, ascending=ascending)
    return df


def _parse_filter_assignment(item: str) -> tuple[str, object] | None:
    if not item or "=" not in str(item):
        return None
    k, v = str(item).split("=", 1)
    k, v = k.strip(), v.strip()
    if not k:
        return None
    if v.lower() in {"true", "false"}:
        return k, v.lower() == "true"
    listish_key = k.endswith(("_in", "_all", "_only")) or ("," in v and not k.endswith(
        ("_regex", "_contains", "_startswith", "_not_startswith", "_prefix")
    ))
    if listish_key and "," in v:
        return k, [p.strip() for p in v.split(",") if p.strip()]
    if k.endswith(("_in", "_all", "_only")):
        return k, [v] if v else []
    return k, v


def _merge_cli_filters(filters: dict, args) -> dict:
    """Map argparse fields onto generic filter keys. CLI overrides config."""
    filters = dict(filters)
    if getattr(args, "source", None):
        filters["source_regex"] = args.source
    if getattr(args, "id_prefix", None):
        filters["id_prefix"] = args.id_prefix
    if getattr(args, "subfield", None):
        filters["subfield_regex"] = args.subfield
    if getattr(args, "category", None):
        filters["category_regex"] = args.category
    if getattr(args, "keywords", None):
        tags = [t.strip() for t in str(args.keywords).split(",") if t.strip()]
        if tags:
            filters["keywords_in"] = tags
    if getattr(args, "unit", None):
        filters["unit_regex"] = args.unit
    if getattr(args, "noasset", False):
        filters["exclude_asset"] = True
    extra = getattr(args, "filter", None) or []
    if isinstance(extra, str):
        extra = [extra]
    for item in extra:
        parsed = _parse_filter_assignment(item)
        if parsed:
            filters[parsed[0]] = parsed[1]
    return filters


def select_task(polymer_bench, args, cfg: dict):
    splits = cfg.get("splits") or {}
    if args.split not in splits:
        known = ", ".join(sorted(splits))
        raise ValueError(f"unknown split {args.split!r}. Known: {known}")
    spec = splits[args.split]
    dataset = args.dataset or spec.get("dataset") or "All"
    answer_type = args.answer_type if args.answer_type is not None else spec.get("answer_type")
    kwargs = {"path": args.data, "dataset": dataset}
    if answer_type:
        kwargs["answer_type"] = answer_type
    try:
        task = polymer_bench(**kwargs)
    except TypeError:
        task = polymer_bench(path=args.data, dataset=dataset, answer_type=answer_type or "exactMatch")

    if getattr(args, "list_field", None):
        list_field_values(task._frame, args.list_field)

    filters = _merge_cli_filters(spec.get("filters") or {}, args)
    df = apply_filters(task._frame, filters)
    df = apply_sort(df, spec.get("sort"))
    if len(df) == 0:
        raise ValueError(
            f"no items for split={args.split!r} dataset={dataset!r} "
            f"answer_type={answer_type!r} filters={filters}"
        )
    task = task._view(df)
    sources = sorted(set(_series(task._frame, "source").astype(str)))
    print(
        f"selected split={args.split} dataset={dataset} answer_type={answer_type} "
        f"n_available={len(task)} sources={sources[:12]} filters={filters}"
    )
    return task, dataset, answer_type, spec


def list_splits(cfg: dict) -> None:
    print(json.dumps(
        {
            name: {
                "description": spec.get("description"),
                "dataset": spec.get("dataset"),
                "answer_type": spec.get("answer_type"),
                "filters": spec.get("filters") or {},
            }
            for name, spec in (cfg.get("splits") or {}).items()
        },
        indent=2,
    ))


def list_sources(polymer_bench, data_dir: Path) -> None:
    task = polymer_bench(path=str(data_dir), dataset="All")
    df = task._frame
    rows = []
    for source, part in df.groupby(_series(df, "source").astype(str)):
        rows.append(
            {
                "source": source,
                "n": int(len(part)),
                "categories": sorted(set(_series(part, "category").astype(str))),
                "answer_types": sorted(set(_series(part, "answer_type").astype(str))),
            }
        )
    print(json.dumps({"data": str(data_dir), "n_total": int(len(df)), "sources": rows}, indent=2))


# ---------------------------------------------------------------------------
# run modes
# ---------------------------------------------------------------------------

def print_turn(kind, index, total, item, raw_text, parsed, score, seconds, judge=None):
    bar = "=" * 88
    print(f"\n{bar}")
    print(f"[{kind}] {index}/{total}  id={item.get('id')}  category={item.get('category')}  {seconds:.2f}s")
    print(f"gold={item.get('answer')!r}  parsed={parsed!r}  rule_score={score:.3f}  rule_match={score >= 0.5}")
    if judge is not None:
        print(
            f"judge_parsed={judge.get('parsed')!r}  judge_score={judge.get('score')}  "
            f"equivalent={judge.get('equivalent')}  reason={judge.get('reason')}"
        )
    print("-" * 88)
    print("PROMPT")
    print("-" * 88)
    print(item.get("prompt") or "")
    print("-" * 88)
    print("FULL OUTPUT")
    print("-" * 88)
    print(raw_text)
    print(bar, flush=True)


def write_turn_file(dump_dir: Path, kind: str, index: int, item: dict, raw_text: str, parsed: str, score: float):
    dump_dir.mkdir(parents=True, exist_ok=True)
    safe_id = str(item.get("id") or index).replace("/", "_")
    path = dump_dir / f"{kind}_{index:03d}_{safe_id}.txt"
    path.write_text(
        (
            f"id: {item.get('id')}\n"
            f"category: {item.get('category')}\n"
            f"gold: {item.get('answer')}\n"
            f"parsed: {parsed}\n"
            f"rule_score: {score}\n"
            f"{'=' * 88}\nPROMPT\n{'=' * 88}\n"
            f"{item.get('prompt') or ''}\n"
            f"{'=' * 88}\nFULL OUTPUT\n{'=' * 88}\n"
            f"{raw_text}\n"
        ),
        encoding="utf-8",
    )
    return str(path)


def record_turn(kind, index, total, slice_, item, raw, extract_fn, dump_dir: Path | None, judge_llm=None, default_tol=0.15):
    text = _as_text(extract_fn(raw))
    parsed = slice_.parse_response(text)
    gold = item["answer"]
    local_i = index - 1
    score = float(slice_._score_one(parsed, gold, local_i))
    seconds = item.get("_seconds", 0.0)
    judge = None
    if judge_llm is not None:
        tol = default_tol
        if "tolerance_rel" in slice_._frame.columns:
            raw_tol = slice_._frame.iloc[local_i].get("tolerance_rel")
            if raw_tol is not None and str(raw_tol) not in {"", "nan", "None"}:
                tol = float(raw_tol)
        judge = judge_one(judge_llm, item, text, gold, tolerance=tol)
    print_turn(kind, index, total, item, text, parsed, score, seconds, judge=judge)
    dump_path = None
    if dump_dir is not None:
        dump_path = write_turn_file(dump_dir, kind, index, item, text, parsed, score)
        if judge is not None:
            Path(dump_path).write_text(
                Path(dump_path).read_text(encoding="utf-8")
                + (
                    f"{'=' * 88}\nJUDGE\n{'=' * 88}\n"
                    f"{json.dumps(judge, ensure_ascii=False, indent=2)}\n"
                ),
                encoding="utf-8",
            )
    final_score = float(judge["score"]) if judge is not None else score
    return {
        "id": item.get("id"),
        "category": item.get("category"),
        "gold": gold,
        "pred_parsed": parsed,
        "score": final_score,
        "rule_score": score,
        "judge": judge,
        "correct": final_score >= 0.5,
        "seconds": seconds,
        "prompt": item.get("prompt"),
        "output": text,
        "dump_file": dump_path,
    }


def _metrics_from_traces(traces: list[dict]) -> dict:
    if not traces:
        return {"n": 0, "accuracy": 0.0, "mean_score": 0.0}
    scores = [float(t.get("score") or 0.0) for t in traces]
    rule = [float(t.get("rule_score") or 0.0) for t in traces]
    return {
        "n": len(traces),
        "accuracy": float(sum(s >= 0.5 for s in scores) / len(scores)),
        "mean_score": float(sum(scores) / len(scores)),
        "rule_accuracy": float(sum(s >= 0.5 for s in rule) / len(rule)),
        "rule_mean_score": float(sum(rule) / len(rule)),
    }


def run_agent(task, n: int, dump_dir: Path | None, judge_llm, runtime: dict, default_tol: float) -> dict:
    from polymer.agent import A1

    agent = A1(path=runtime.get("agent_root") or ".", llm=runtime.get("agent_llm") or "claude-sonnet-5")
    slice_ = task.take(n)
    preds = []
    traces = []
    t0 = time.time()
    for i, item in enumerate(slice_.get_iterator()):
        t1 = time.time()
        raw = agent.go(item["prompt"])
        item["_seconds"] = round(time.time() - t1, 2)
        text = _as_text(extract_agent_answer(raw))
        preds.append(text)
        traces.append(
            record_turn("agent", i + 1, n, slice_, item, text, lambda x: x, dump_dir, judge_llm, default_tol)
        )
        agent = A1(path=runtime.get("agent_root") or ".", llm=runtime.get("agent_llm") or "claude-sonnet-5")
    return {
        "n": n,
        "seconds": round(time.time() - t0, 2),
        "evaluate": slice_.evaluate(preds),
        "evaluate_judged": _metrics_from_traces(traces),
        "by_category": slice_.evaluate_by_category(preds),
        "traces": traces,
    }


def run_llm(task, n: int, dump_dir: Path | None, judge_llm, runtime: dict, default_tol: float) -> dict:
    from polymer.config import default_config
    from polymer.llm import get_llm

    loaded = load_env_files()
    if loaded:
        print("loaded .env from:", loaded)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY still empty after .env load")

    llm = get_llm(
        runtime.get("baseline_llm") or "claude-sonnet-5",
        stop_sequences=runtime.get("stop_sequences") or ["</execute>", "</solution>"],
        source=default_config.source,
        base_url=default_config.base_url,
        api_key=default_config.api_key if default_config.api_key else "EMPTY",
        config=default_config,
    )
    slice_ = task.take(n)
    preds = []
    traces = []
    t0 = time.time()
    for i, item in enumerate(slice_.get_iterator()):
        t1 = time.time()
        raw = llm.invoke(item["prompt"])
        item["_seconds"] = round(time.time() - t1, 2)
        text = _as_text(extract_llm_answer(raw))
        preds.append(text)
        traces.append(
            record_turn("llm", i + 1, n, slice_, item, text, lambda x: x, dump_dir, judge_llm, default_tol)
        )
    return {
        "n": n,
        "seconds": round(time.time() - t0, 2),
        "evaluate": slice_.evaluate(preds),
        "evaluate_judged": _metrics_from_traces(traces),
        "by_category": slice_.evaluate_by_category(preds),
        "traces": traces,
    }


def should_judge(args, answer_type: str | None, spec: dict, scoring: dict) -> bool:
    if args.no_judge:
        return False
    if args.judge:
        return True
    if spec.get("judge") is not None:
        return bool(spec["judge"])
    key = answer_type or "exactMatch"
    block = scoring.get(key) or scoring.get("exactMatch") or {}
    if "judge_default" in block:
        return bool(block["judge_default"])
    return key != "multipleChoice"


# ---------------------------------------------------------------------------
# cli
# ---------------------------------------------------------------------------

def main() -> None:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", default=str(DEFAULT_CONFIG))
    pre_args, _ = pre.parse_known_args()
    cfg, cfg_path = load_eval_config(Path(pre_args.config) if pre_args.config else None)
    runtime = cfg.get("runtime") or {}
    splits = cfg.get("splits") or {}
    scoring = cfg.get("scoring") or {}

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(cfg_path or DEFAULT_CONFIG))
    parser.add_argument("--mode", choices=["harness", "agent", "llm", "all"], default="harness")
    parser.add_argument("--n", type=int, default=int(runtime.get("default_n") or 10))
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--data", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--dump-dir", default=str(HERE / "results" / "history"))
    parser.add_argument("--split", default=runtime.get("default_split") or "easy", choices=sorted(splits) or None)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--answer-type", dest="answer_type", default=None, choices=["multipleChoice", "exactMatch", "ranking"])
    parser.add_argument("--source", default=None, help="regex override for source column")
    parser.add_argument("--id-prefix", dest="id_prefix", default=None)
    parser.add_argument("--subfield", default=None)
    parser.add_argument("--category", default=None, help="regex on category")
    parser.add_argument("--keywords", default=None, help="comma-separated tags applied as keywords_in")
    parser.add_argument("--unit", default=None, help="regex on unit")
    parser.add_argument(
        "--filter",
        action="append",
        default=[],
        help="generic col op, repeatable: --filter subfield=density --filter keywords_in=density,numeric",
    )
    parser.add_argument(
        "--list-field",
        dest="list_field",
        default=None,
        help="print distinct values of a column (keywords, subfield, unit, ...) then continue",
    )
    parser.add_argument("--judge", action="store_true", default=None)
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument("--noasset", action="store_true", default=False)

    parser.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL", runtime.get("judge_model")))
    parser.add_argument("--agent-llm", default=runtime.get("agent_llm"))
    parser.add_argument("--baseline-llm", default=runtime.get("baseline_llm"))
    parser.add_argument("--agent-root", default=runtime.get("agent_root"))
    parser.add_argument("--list-splits", action="store_true")
    parser.add_argument("--list-sources", action="store_true")
    args = parser.parse_args()

    if args.list_splits:
        list_splits(cfg)
        return

    data_dir = resolve_data_dir(cfg, args.data)
    args.data = str(data_dir)
    env_files = load_env_files()
    polymer_bench, _hle, _lab, origin = load_task_classes()

    if args.list_sources:
        list_sources(polymer_bench, data_dir)
        return

    runtime = dict(runtime)
    if args.agent_llm:
        runtime["agent_llm"] = args.agent_llm
    if args.baseline_llm:
        runtime["baseline_llm"] = args.baseline_llm
    if args.agent_root:
        runtime["agent_root"] = args.agent_root

    dump_dir = Path(args.dump_dir) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(args.out) if args.out else dump_dir / "eval_results.json"

    task, dataset, answer_type, spec = select_task(polymer_bench, args, cfg)
    live_task = task.take(args.n, offset=args.offset)
    use_judge = should_judge(args, answer_type, spec, scoring)
    default_tol = float(runtime.get("default_tolerance_rel") or 0.15)
    judge_llm = None
    if use_judge and args.mode in {"agent", "llm", "all"}:
        try:
            judge_llm = get_judge_llm(args.judge_model)
            print(f"judge enabled model={args.judge_model}")
        except Exception as exc:
            print(f"WARNING: judge LLM failed to load ({exc}); falling back to rule scores")
            judge_llm = None

    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(cfg_path) if cfg_path else None,
        "task_origin": origin,
        "data_path": args.data,
        "split": args.split,
        "split_spec": {
            "description": spec.get("description"),
            "dataset": dataset,
            "answer_type": answer_type,
            "filters": spec.get("filters") or {},
        },
        "dataset": dataset,
        "answer_type": answer_type,
        "judge_model": args.judge_model if judge_llm is not None else None,
        "env_files": env_files,
        "sizes": {
            "selected_available": len(task),
            "run": len(live_task),
            "offset": args.offset,
        },
        "example_id": live_task.get_example(0)["id"] if len(live_task) else None,
        "history_dir": str(dump_dir),
        "runs": {},
        "errors": {},
    }

    if args.mode in {"harness", "all"}:
        gold = list(live_task.answer)
        payload["runs"]["harness"] = {
            "oracle": live_task.evaluate(gold),
            "by_category": live_task.evaluate_by_category(gold),
        }

    if args.mode in {"agent", "all"}:
        try:
            payload["runs"]["agent"] = run_agent(
                live_task, len(live_task), dump_dir / "agent", judge_llm, runtime, default_tol
            )
        except Exception as exc:
            payload["errors"]["agent"] = f"{type(exc).__name__}: {exc}"
            payload["errors"]["agent_trace"] = traceback.format_exc()

    if args.mode in {"llm", "all"}:
        try:
            payload["runs"]["llm"] = run_llm(
                live_task, len(live_task), dump_dir / "llm", judge_llm, runtime, default_tol
            )
        except Exception as exc:
            payload["errors"]["llm"] = f"{type(exc).__name__}: {exc}"
            payload["errors"]["llm_trace"] = traceback.format_exc()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("timestamp_utc", "task_origin", "split", "sizes", "runs", "errors")}, indent=2))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()