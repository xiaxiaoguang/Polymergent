"""Corrected polymer-agent evaluation loop.

Bugs in the original snippet
----------------------------
1. `A1.go()` returns `(log, final_text)`, so `[1]` is valid on the *agent*.
   `A1` has no `.invoke()`. `.invoke()` belongs to the raw LLM from `get_llm`.
2. `get_llm(...)` was stored as `agent2` then never used; `agent.invoke(...)`
   would raise AttributeError.
3. `dataset="All"` + `exactMatch` is ~1.1k items. Running the full agent twice
   is not a debug loop. Slice with `.take(n)`.
4. `path="./data"` only works if that directory contains `polymer/seed_tasks.json`
   and/or `polymer/external_tasks.json`.
5. `polymer.task.polymer_bench` exists only after you copy `polymer_bench.py`
   into the Polymer tree. This script falls back to the local module.
6. Raw LLM `.invoke(prompt)` returns an AIMessage; use `.content`, not `[1]`.
7. Scoring long exactMatch answers by letter-parsing always yields ~0.
   `polymer_bench.evaluate` now uses numeric tolerance / token overlap.

Usage
-----
    python run_eval.py --mode harness          # no API, records oracle/parse tests
    python run_eval.py --mode agent --n 10     # requires Polymer + API keys
    python run_eval.py --mode llm --n 10       # raw LLM baseline, no tools
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
# here put where your evaluate data is
_DATA_CANDIDATES = [
    Path("/home/hcao5/workspace/datasets/polymer/data"),
    HERE / "data",
]
DATA_DIR = next((p for p in _DATA_CANDIDATES if p.exists()), HERE / "data")

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


def _content_blocks_to_text(value) -> str:
    """Flatten OpenAI / Grok / Anthropic / LangChain message payloads to text."""
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
    if not raw:
        return None
    if raw[0] not in "[{":
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
    """Accept judge JSON from Anthropic strings, OpenAI/Grok content blocks, or Python reprs."""
    if text is None:
        return None
    candidates = [text]
    flattened = _content_blocks_to_text(text)
    if flattened and flattened not in candidates:
        candidates.append(flattened)
    literal = _maybe_literal(flattened if isinstance(text, str) else flattened)
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
        # smallest object that looks like the judge schema
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
        # escaped JSON inside a string field: {\"parsed\": ...}
        unescaped = raw.replace('\\"', '"').replace("\\'", "'")
        if unescaped != raw:
            inner = _parse_judge_json(unescaped)
            if inner:
                return inner
    return None


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


def load_env_files() -> list[str]:
    """Load .env the same way A1 does, plus the script directory.

    A1 is the only Polymer entry that calls load_dotenv. get_llm() does not.
    ChatAnthropic also ignores the api_key= argument and reads ANTHROPIC_API_KEY
    from os.environ. So llm-mode must populate the environment before get_llm().
    """
    loaded = []
    try:
        from dotenv import load_dotenv
    except ImportError:
        return loaded
    candidates = [
        Path.cwd() / ".env",
        HERE / ".env",
        HERE.parent / ".env",
    ]
    seen = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        # override=False keeps a real shell export if one already exists
        load_dotenv(path, override=False)
        loaded.append(str(resolved))
    return loaded


def load_task_classes():
    try:
        from polymer.task.polymer_bench import polymer_bench, polymer_hle, polymer_lab_bench

        origin = "polymer.task.polymer_bench"
    except ImportError:
        from polymer_bench import polymer_bench, polymer_hle, polymer_lab_bench

        origin = "local polymer_bench"
    return polymer_bench, polymer_hle, polymer_lab_bench, origin


def extract_agent_answer(result):
    """A1.go returns str in some forks and (log, text) in upstream Polymer."""
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


def print_turn(kind: str, index: int, total: int, item: dict, raw_text: str, parsed: str, score: float, seconds: float, judge: dict | None = None):
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


def record_turn(kind, index, total, slice_, item, raw, extract_fn, dump_dir: Path | None, judge_llm=None):
    text = _as_text(extract_fn(raw))
    parsed = slice_.parse_response(text)
    gold = item["answer"]
    local_i = index - 1
    score = float(slice_._score_one(parsed, gold, local_i))
    seconds = item.get("_seconds", 0.0)
    judge = None
    if judge_llm is not None:
        tol = 0.15
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


def run_harness(task_mcq, task_open) -> dict:
    """Deterministic checks that do not need an LLM."""
    records = {}

    gold_mcq = list(task_mcq.answer)
    records["mcq_oracle"] = {
        "evaluate": task_mcq.evaluate(gold_mcq),
        "by_category": task_mcq.evaluate_by_category(gold_mcq),
    }

    tagged = [f"reasoning...\n[ANSWER]{a}[/ANSWER]" for a in gold_mcq]
    records["mcq_tagged_parse"] = {
        "evaluate": task_mcq.evaluate(tagged),
        "parsed_head": [task_mcq.parse_response(x) for x in tagged[:5]],
    }

    wrong = ["Z"] * len(task_mcq)
    records["mcq_all_wrong"] = task_mcq.evaluate(wrong)

    gold_open = list(task_open.answer)
    records["open_oracle"] = {
        "evaluate": task_open.evaluate(gold_open),
        "by_category": task_open.evaluate_by_category(gold_open),
    }

    noisy = [f"The answer is approximately {a}" for a in gold_open]
    records["open_noisy_wrap"] = task_open.evaluate(noisy)

    length_mismatch_error = None
    try:
        task_mcq.evaluate(["A"])
    except ValueError as exc:
        length_mismatch_error = str(exc)
    records["length_guard"] = length_mismatch_error
    return records


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


def run_agent(task, n: int, dump_dir: Path | None, judge_llm=None) -> dict:
    from polymer.agent import A1

    agent = A1(path="/home/hcao5/workspace/datasets", llm="claude-sonnet-5")
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
        traces.append(record_turn("agent", i + 1, n, slice_, item, text, lambda x: x, dump_dir, judge_llm=judge_llm))
    return {
        "n": n,
        "seconds": round(time.time() - t0, 2),
        "evaluate": slice_.evaluate(preds),
        "evaluate_judged": _metrics_from_traces(traces),
        "by_category": slice_.evaluate_by_category(preds),
        "traces": traces,
    }


def run_llm(task, n: int, dump_dir: Path | None, judge_llm=None) -> dict:
    from polymer.config import default_config
    from polymer.llm import get_llm

    loaded = load_env_files()
    if loaded:
        print("loaded .env from:", loaded)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY still empty after .env load")

    llm = get_llm(
        "claude-sonnet-5",
        stop_sequences=["</execute>", "</solution>"],
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
        traces.append(record_turn("llm", i + 1, n, slice_, item, text, lambda x: x, dump_dir, judge_llm=judge_llm))
    return {
        "n": n,
        "seconds": round(time.time() - t0, 2),
        "evaluate": slice_.evaluate(preds),
        "evaluate_judged": _metrics_from_traces(traces),
        "by_category": slice_.evaluate_by_category(preds),
        "traces": traces,
    }


HARD_SPLITS = {
    "easy": {
        "dataset": "KnowledgeQA",
        "answer_type": "multipleChoice",
        "filters": {},
    },
    "protocol": {
        "dataset": "ProtocolQA",
        "answer_type": "exactMatch",
        "filters": {},
    },
    "rank": {
        "dataset": "PropQA",
        "answer_type": "exactMatch",
        "filters": {"source": "PolyReal"},
    },
    "numeric": {
        "dataset": "PropQA",
        "answer_type": "exactMatch",
        "filters": {"source": "POINT2|PolymerAgent"},
    },
    "hard": {
        "dataset": "All",
        "answer_type": "exactMatch",
        "filters": {},
        "exclude_easy_knowledge": True,
    },
}


def select_task(polymer_bench, args):
    split = HARD_SPLITS.get(args.split)
    dataset = args.dataset or (split["dataset"] if split else "KnowledgeQA")
    answer_type = args.answer_type or (split["answer_type"] if split else "multipleChoice")
    task = polymer_bench(path=args.data, dataset=dataset, answer_type=answer_type)

    filters = dict(split["filters"]) if split else {}
    if args.source:
        filters["source"] = args.source
    if args.id_prefix:
        filters["id_prefix"] = args.id_prefix
    if args.subfield:
        filters["subfield"] = args.subfield

    df = task._frame
    if filters.get("source"):
        pat = filters["source"]
        if "source" not in df.columns:
            raise ValueError("source column missing after load")
        mask = df["source"].astype(str).str.contains(pat, case=False, na=False, regex=True)
        df = df[mask]
    if filters.get("id_prefix"):
        df = df[df["id"].astype(str).str.startswith(filters["id_prefix"])]
    if filters.get("subfield") and "subfield" in df.columns:
        df = df[df["subfield"].astype(str).str.contains(filters["subfield"], case=False, na=False)]
    if split and split.get("exclude_easy_knowledge"):
        keep = df["category"].isin(["ProtocolQA", "PropQA", "DbQA"])
        # keep only long / sourced hard items, not 1-line seed facts
        sourced = df["source"].astype(str).isin(
            [
                "PolyReal",
                "POINT2_Tg",
                "PolymerAgent_Egb",
                "PolymerAgent_Eea",
                "PolymerAgent_EPS",
                "PolymerAgent_Xc",
                "PolymerAgent_Ei",
                "PolymerAgent_Nc",
                "PolymerAgent_Egc",
                "PolymerAgent_OPV",
            ]
        )
        df = df[keep & sourced]
    if args.split == "rank":
        # PolyReal rankings store ordered lists in ideal
        df = df[df["ideal"].astype(str).str.startswith("[")]
    if args.split == "numeric":
        df = df[df["ideal"].astype(str).str.contains(r"[-+]?\d", regex=True, na=False)]
        df = df[~df["ideal"].astype(str).str.startswith("[")]
    if args.split == "protocol":
        # the long inspection items are the hard ones
        df = df.sort_values("question", key=lambda s: s.astype(str).str.len(), ascending=False)

    if len(df) == 0:
        raise ValueError(
            f"no items for split={args.split!r} dataset={dataset!r} answer_type={answer_type!r} filters={filters}"
        )
    task = task._view(df)
    print(
        f"selected split={args.split} dataset={dataset} answer_type={answer_type} "
        f"n_available={len(task)} sources={sorted(set(task._frame.get('source', pd.Series()).astype(str)))[:8]}"
    )
    return task, dataset, answer_type


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["harness", "agent", "llm", "all"], default="harness")
    parser.add_argument("--n", type=int, default=10, help="items per live model run")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--data", default=str(DATA_DIR))
    parser.add_argument("--out", default=str(HERE / "results" / "eval_results.json"))
    parser.add_argument(
        "--dump-dir",
        default=str(HERE / "results" / "history"),
        help="Write one prompt+output text file per item",
    )
    parser.add_argument(
        "--split",
        choices=["easy", "protocol", "rank", "numeric", "hard"],
        default="easy",
        help="easy=KnowledgeQA MCQ; protocol=lab safety; rank=PolyReal ordered lists; numeric=Tg/Egc/...; hard=all of those",
    )
    parser.add_argument("--dataset", default=None, help="override: KnowledgeQA|StructQA|ProtocolQA|PropQA|DbQA|All")
    parser.add_argument("--answer-type", dest="answer_type", default=None, choices=["multipleChoice", "exactMatch"])
    parser.add_argument("--source", default=None, help="regex on source column, e.g. PolyReal or POINT2|PolymerAgent")
    parser.add_argument("--id-prefix", dest="id_prefix", default=None)
    parser.add_argument("--subfield", default=None)
    parser.add_argument(
        "--judge",
        action="store_true",
        default=None,
        help="Force cheap LLM judge on each output (default: on for exactMatch splits)",
    )
    parser.add_argument("--no-judge", action="store_true", help="Disable LLM judge")
    parser.add_argument(
        "--judge-model",
        default=os.environ.get("JUDGE_MODEL", "claude-3-5-haiku-20241022"),
        help="Cheap grader model. Default claude-3-5-haiku-20241022",
    )
    args = parser.parse_args()
    dump_dir = Path(args.dump_dir) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.out = str(dump_dir) + "/eval_results.json"
    env_files = load_env_files()
    polymer_bench, polymer_hle, polymer_lab_bench, origin = load_task_classes()
    task, dataset, answer_type = select_task(polymer_bench, args)
    live_task = task.take(args.n, offset=args.offset)
    use_judge = False
    if args.no_judge:
        use_judge = False
    elif args.judge:
        use_judge = True
    else:
        use_judge = answer_type == "exactMatch" or args.split in {"rank", "numeric", "protocol", "hard"}
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
        "task_origin": origin,
        "data_path": args.data,
        "split": args.split,
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
            payload["runs"]["agent"] = run_agent(live_task, len(live_task), dump_dir / "agent", judge_llm=judge_llm)
        except Exception as exc:
            payload["errors"]["agent"] = f"{type(exc).__name__}: {exc}"
            payload["errors"]["agent_trace"] = traceback.format_exc()

    if args.mode in {"llm", "all"}:
        try:
            payload["runs"]["llm"] = run_llm(live_task, len(live_task), dump_dir / "llm", judge_llm=judge_llm)
        except Exception as exc:
            payload["errors"]["llm"] = f"{type(exc).__name__}: {exc}"
            payload["errors"]["llm_trace"] = traceback.format_exc()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("timestamp_utc", "task_origin", "sizes", "runs", "errors")}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()