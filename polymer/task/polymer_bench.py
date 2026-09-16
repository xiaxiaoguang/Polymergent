"""Polymer-agent evaluation tasks in the Polymer task style.

Polymer evaluates biomedical agents on Humanity's Last Exam (HLE) and
LAB-Bench (DbQA, SeqQA). Those corpora are biology-specific. This module
is the polymer analog:

    KnowledgeQA  ~ HLE-style expert multiple choice
    StructQA     ~ LAB-Bench SeqQA (repeat-unit / architecture reasoning)
    ProtocolQA   ~ LAB-Bench ProtocolQA (lab procedure troubleshooting)
    PropQA       ~ structure–property comparison / ranking
    DbQA         ~ identifier / database / informatics facts

Data sources, in load order:
    1. Bundled seed set   data/polymer/seed_tasks.json
    2. Local files under  {path}/polymer/  (json, jsonl, parquet, csv)
    3. Optional Hugging Face datasets if `source` is a hub id

Usage (same shape as polymer.task.hle.humanity_last_exam)::

    from polymer_bench import polymer_bench

    task = polymer_bench(path="./data", dataset="KnowledgeQA")
    ex = task.get_example(0)
    metrics = task.evaluate(["C", "A", ...])
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from polymer.task.base_task import base_task
except ImportError:  # standalone / polymer-agent tree
    from base_task import base_task

np.random.seed(42)

DATASETS = (
    "KnowledgeQA",
    "StructQA",
    "ProtocolQA",
    "PropQA",
    "DbQA",
    "All",
)

ANSWER_TYPES = ("multipleChoice", "exactMatch")

# Maps common external schema names onto the internal category labels.
CATEGORY_ALIASES = {
    "knowledgeqa": "KnowledgeQA",
    "knowledge": "KnowledgeQA",
    "hle": "KnowledgeQA",
    "conceptual": "KnowledgeQA",
    "conknow": "KnowledgeQA",
    "structqa": "StructQA",
    "structure": "StructQA",
    "seqqa": "StructQA",
    "strund": "StructQA",
    "protocolqa": "ProtocolQA",
    "protocol": "ProtocolQA",
    "safe": "ProtocolQA",
    "propqa": "PropQA",
    "property": "PropQA",
    "proppred": "PropQA",
    "propcopr": "PropQA",
    "propcompr": "PropQA",
    "dbqa": "DbQA",
    "database": "DbQA",
    "all": "All",
}

REFRAIN_TEXT = "Insufficient information to answer the question."


def shuffle(x):
    np.random.shuffle(x)
    return x


def _normalize_category(value: str | None) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    key = str(value).strip()
    aliased = CATEGORY_ALIASES.get(key.lower())
    if aliased:
        return aliased
    if key in DATASETS:
        return key
    return key


def _is_present(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    if isinstance(value, np.ndarray):
        return value.size > 0
    try:
        if pd.isna(value):
            return False
    except (ValueError, TypeError):
        pass
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def _first_present(row: dict, keys: list[str], default=None):
    for key in keys:
        if key in row and _is_present(row[key]):
            return row[key]
    return default


def _letter_from_answer(answer) -> str:
    if answer is None or (isinstance(answer, float) and np.isnan(answer)):
        return ""
    text = str(answer).strip()
    if not text:
        return ""
    if text[0].isalpha() and (len(text) == 1 or not text[1].isalpha()):
        return text[0].upper()
    return text


def _split_choices_from_question(question: str) -> tuple[str, list[str]]:
    """Parse HLE-style 'Answer Choices: A. ... B. ...' blocks if present."""
    if "Answer Choices:" not in question:
        return question.strip(), []
    stem, rest = question.split("Answer Choices:", 1)
    options = []
    letters = [f"{chr(ord('A') + i)}." for i in range(26)]
    for i, letter in enumerate(letters):
        if letter not in rest:
            continue
        nxt = letters[i + 1] if i + 1 < len(letters) else None
        parts = rest.split(letter, 1)[1]
        option = parts.split(nxt)[0].strip() if nxt and nxt in parts else parts.strip()
        options.append(option)
    return stem.strip(), options


class polymer_bench(base_task):
    """Polymer evaluation task with the Polymer `base_task` interface."""

    def __init__(
        self,
        path: str = "./data",
        dataset: str = "KnowledgeQA",
        answer_type: str = "multipleChoice",
        source: str | None = None,
        add_refrain: bool = True,
        seed: int = 42,
    ):
        if dataset not in DATASETS:
            raise ValueError(f"dataset must be one of {list(DATASETS)}")
        if answer_type not in ANSWER_TYPES:
            raise ValueError("answer_type must be one of ['exactMatch', 'multipleChoice']")

        self.dataset = dataset
        self.answer_type = answer_type
        self.add_refrain = add_refrain
        self.refrain_text = REFRAIN_TEXT
        np.random.seed(seed)

        df = self._load_frame(path=path, source=source)
        df = self._standardize(df)

        if dataset != "All":
            df = df[df["category"] == dataset]
        if answer_type == "multipleChoice":
            # keep rows that either already have a letter key or have a choice list
            has_choices = df["choices"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)
            has_letter = df["letter_answer"].astype(str).str.fullmatch(r"[A-Za-z]")
            df = df[has_choices | has_letter]
        df = df.reset_index(drop=True)
        if len(df) == 0:
            raise ValueError(
                f"No items left after filtering dataset={dataset!r}, "
                f"answer_type={answer_type!r}. Check path={path!r} / source={source!r}."
            )

        if answer_type == "multipleChoice":
            df = self._materialize_choices(df)

        self._frame = df
        self.query = df["question"].values
        self.options = df["options_letters"].values if "options_letters" in df.columns else [""] * len(df)
        self.answer = df["letter_answer"].values if answer_type == "multipleChoice" else df["ideal"].values
        if "letter_refrain" in df.columns:
            self.refrain_label = df["letter_refrain"].values
        else:
            self.refrain_label = np.array([""] * len(df))
        self.ids = df["id"].astype(str).values
        self.categories = df["category"].values

        if answer_type == "multipleChoice":
            self.prompt = (
                "The following is a multiple choice question about polymer science.\n"
                "Think step by step if needed, then give the final answer.\n\n"
                "Question: {question}\n"
                "Options:\n"
                "{options}\n\n"
                "Put the final answer inside <solution>...</solution>.\n"
                "For multiple choice, the solution body must be a single letter "
                "(A, B, C, ...), for example: <solution>C</solution>.\n"
                "Do not put extra words inside the solution tags."
            )
        else:
            self.prompt = (
                "The following is a polymer science question.\n"
                "Think step by step if needed, then give the exact short final answer.\n\n"
                "Question: {question}\n\n"
                "Put the final answer inside <solution>...</solution>.\n"
                "For a number, output only the number (and unit if asked). "
                "For a ranking, output the ordered list. "
                "Do not put extra commentary inside the solution tags."
            )

    # ------------------------------------------------------------------ loaders
    def _load_frame(self, path: str, source: str | None) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []

        seed_path = self._resolve_seed_path(path)
        if seed_path is not None:
            frames.append(self._read_any(seed_path))

        search_roots = [
            Path(path),
            Path(path) / "polymer",
            Path(__file__).resolve().parent / "data" / "polymer",
        ]
        extra_names = (
            "tasks.json",
            "tasks_v2.json",
            "external_tasks.json",
            "tasks.jsonl",
            "test.json",
            "test.jsonl",
            "test.parquet",
            "polyreal.json",
            "PolyReal.json",
            "polybench.json",
            "polybench.jsonl",
            "polybench.parquet",
        )
        seen = {str(seed_path.resolve())} if seed_path is not None else set()
        for root in search_roots:
            if not root.exists():
                continue
            for name in extra_names:
                candidate = root / name
                if candidate.exists() and str(candidate.resolve()) not in seen:
                    frames.append(self._read_any(candidate))
                    seen.add(str(candidate.resolve()))

        if source:
            frames.append(self._load_source(source))

        if not frames:
            raise FileNotFoundError(
                "No polymer evaluation items found. Expected the bundled seed file "
                "data/polymer/seed_tasks.json or a file under {path}/polymer/."
            )
        return pd.concat(frames, ignore_index=True)

    def _resolve_seed_path(self, path: str) -> Path | None:
        candidates = [
            Path(path) / "polymer" / "seed_tasks.json",
            Path(path) / "seed_tasks.json",
            Path(__file__).resolve().parent / "data" / "polymer" / "seed_tasks.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _read_any(self, file_path: Path) -> pd.DataFrame:
        suffix = file_path.suffix.lower()
        if suffix == ".json":
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and "tasks" in payload:
                return pd.DataFrame(payload["tasks"])
            if isinstance(payload, list):
                return pd.DataFrame(payload)
            return pd.DataFrame([payload])
        if suffix == ".jsonl":
            rows = [json.loads(line) for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            return pd.DataFrame(rows)
        if suffix == ".parquet":
            return pd.read_parquet(file_path)
        if suffix in {".csv", ".tsv"}:
            sep = "\t" if suffix == ".tsv" else ","
            return pd.read_csv(file_path, sep=sep)
        raise ValueError(f"Unsupported file type: {file_path}")

    def _load_source(self, source: str) -> pd.DataFrame:
        """Load a Hugging Face dataset id or a raw file path."""
        src_path = Path(source)
        if src_path.exists():
            return self._read_any(src_path)
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise ImportError(
                "Install `datasets` to load Hugging Face sources, or pass a local file path."
            ) from exc
        # Common polymer hubs. PolyReal publishes a default config; others may need a split name.
        try:
            ds = load_dataset(source, split="train")
        except Exception:
            ds = load_dataset(source)
            split = list(ds.keys())[0]
            ds = ds[split]
        return ds.to_pandas()

    # -------------------------------------------------------------- normalize
    def _standardize(self, df: pd.DataFrame) -> pd.DataFrame:
        records = []
        for _, raw in df.iterrows():
            row = raw.to_dict()
            question = _first_present(row, ["question", "Question", "query", "input", "prompt", "question_text"], "")
            question = str(question).strip()
            stem, parsed_options = _split_choices_from_question(question)
            if parsed_options:
                question = stem

            choices = _first_present(row, ["choices", "options", "Choices", "Options"], None)
            if isinstance(choices, str):
                try:
                    choices = json.loads(choices)
                except json.JSONDecodeError:
                    choices = [c.strip() for c in re.split(r"\n+", choices) if c.strip()]
            if choices is None:
                choices = parsed_options
            if isinstance(choices, np.ndarray):
                choices = choices.tolist()

            ideal = _first_present(row, ["ideal", "Answer", "answer_text", "target", "ground_truth"], None)
            letter = _first_present(row, ["answer", "letter_answer", "label", "target_label"], None)
            letter = _letter_from_answer(letter) if letter is not None else ""

            if choices and letter and letter.isalpha():
                idx = ord(letter.upper()) - ord("A")
                if 0 <= idx < len(choices) and ideal is None:
                    ideal = re.sub(r"^[A-Za-z][.)]\s*", "", str(choices[idx])).strip()

            category = _normalize_category(
                _first_present(row, ["category", "Category", "task", "task_type", "dataset"], self.dataset)
            )
            if category not in DATASETS:
                # PolyReal-style coarse tags
                tag = str(_first_present(row, ["category", "Type", "Topic"], "")).lower()
                if "safe" in tag:
                    category = "ProtocolQA"
                elif "rank" in tag or "性能" in tag:
                    category = "PropQA"
                elif "spectrum" in tag or "table" in tag or "raw" in tag:
                    category = "DbQA"
                else:
                    category = "KnowledgeQA"

            item_id = _first_present(row, ["id", "ID", "uid"], f"{category}_{len(records):04d}")
            records.append(
                {
                    "id": item_id,
                    "category": category,
                    "question": question,
                    "choices": choices if isinstance(choices, list) else [],
                    "ideal": "" if ideal is None else str(ideal).strip(),
                    "letter_answer": letter.upper() if letter and letter.isalpha() else "",
                    "answer_type": _first_present(row, ["answer_type"], "multipleChoice"),
                    "subfield": _first_present(row, ["subfield", "Topic", "Type"], ""),
                    "source": str(_first_present(row, ["source", "Source"], "")),
                    "mm": bool(_first_present(row, ["mm"], False)),
                    "asset": _first_present(row, ["asset"], ""),
                    "difficulty": str(_first_present(row, ["difficulty"], "")),
                    "tolerance_rel": _first_present(row, ["tolerance_rel"], None),
                }
            )
        return pd.DataFrame.from_records(records)

    def _materialize_choices(self, df: pd.DataFrame) -> pd.DataFrame:
        option_blocks = []
        letters = []
        refrains = []
        cleaned_choices = []

        for _, row in df.iterrows():
            raw_choices = list(row["choices"]) if row["choices"] else []
            # Strip any leading "A." prefixes so we can re-letter after shuffle.
            stripped = [re.sub(r"^[A-Za-z][.)]\s*", "", str(c)).strip() for c in raw_choices]
            ideal = row["ideal"]
            letter = row["letter_answer"]

            if not stripped and ideal:
                # exact-match item forced into MC: cannot fabricate distractors safely
                stripped = [ideal]
            if letter and letter.isalpha() and not ideal and stripped:
                idx = ord(letter) - ord("A")
                if 0 <= idx < len(stripped):
                    ideal = stripped[idx]

            if self.add_refrain and REFRAIN_TEXT not in stripped:
                stripped = stripped + [REFRAIN_TEXT]

            ordered = shuffle(stripped.copy()) if len(stripped) > 1 else stripped
            block = "\n".join(f"{chr(ord('A') + i)}. {item}" for i, item in enumerate(ordered))
            if ideal and ideal in ordered:
                ans_letter = chr(ord("A") + ordered.index(ideal))
            elif letter and letter.isalpha() and raw_choices:
                # fall back: find the original lettered choice text in the shuffled list
                orig_idx = ord(letter) - ord("A")
                orig_text = stripped[orig_idx] if orig_idx < len(stripped) else ideal
                ans_letter = chr(ord("A") + ordered.index(orig_text)) if orig_text in ordered else letter
            else:
                ans_letter = letter or ""

            refrain_letter = ""
            if REFRAIN_TEXT in ordered:
                refrain_letter = chr(ord("A") + ordered.index(REFRAIN_TEXT))

            option_blocks.append(block)
            letters.append(ans_letter)
            refrains.append(refrain_letter)
            cleaned_choices.append(ordered)

        df = df.copy()
        df["choices"] = cleaned_choices
        df["options_letters"] = option_blocks
        df["letter_answer"] = letters
        df["letter_refrain"] = refrains
        df["ideal"] = [
            row["ideal"]
            if row["ideal"]
            else (
                cleaned_choices[i][ord(letters[i]) - ord("A")]
                if letters[i] and letters[i].isalpha()
                else ""
            )
            for i, (_, row) in enumerate(df.iterrows())
        ]
        return df

    # ------------------------------------------------------------- public API
    def __len__(self):
        return len(self.query)

    def take(self, n: int, offset: int = 0):
        """Return a shallow view limited to n items starting at offset."""
        end = min(offset + n, len(self.query))
        return self._view(self._frame.iloc[offset:end].reset_index(drop=True))

    def _view(self, frame: pd.DataFrame):
        clone = object.__new__(self.__class__)
        clone.__dict__.update(self.__dict__)
        clone._frame = frame.reset_index(drop=True)
        clone.query = clone._frame["question"].values
        clone.options = (
            clone._frame["options_letters"].values
            if "options_letters" in clone._frame.columns
            else np.array([""] * len(clone._frame))
        )
        if self.answer_type == "multipleChoice":
            clone.answer = clone._frame["letter_answer"].values
        else:
            clone.answer = clone._frame["ideal"].values
        clone.refrain_label = (
            clone._frame["letter_refrain"].values
            if "letter_refrain" in clone._frame.columns
            else np.array([""] * len(clone._frame))
        )
        clone.ids = clone._frame["id"].astype(str).values
        clone.categories = clone._frame["category"].values
        return clone

    def filter_rows(
        self,
        source: str | None = None,
        sources: list[str] | None = None,
        id_prefix: str | None = None,
        subfield: str | None = None,
        mm: bool | None = None,
        difficulty: str | None = None,
        ids: list[str] | None = None,
    ):
        df = self._frame.copy()
        if source:
            col = df["source"] if "source" in df.columns else pd.Series([""] * len(df))
            df = df[col.astype(str).str.contains(source, case=False, na=False)]
        if sources:
            col = df["source"] if "source" in df.columns else pd.Series([""] * len(df))
            df = df[col.astype(str).isin(sources)]
        if id_prefix:
            df = df[df["id"].astype(str).str.startswith(id_prefix)]
        if subfield and "subfield" in df.columns:
            df = df[df["subfield"].astype(str).str.contains(subfield, case=False, na=False)]
        if mm is not None and "mm" in df.columns:
            df = df[df["mm"].astype(bool) == mm]
        if difficulty and "difficulty" in df.columns:
            df = df[df["difficulty"].astype(str).str.lower() == difficulty.lower()]
        if ids:
            df = df[df["id"].astype(str).isin(ids)]
        if len(df) == 0:
            raise ValueError("filter_rows() left 0 items")
        return self._view(df)

    def get_example(self, index=None):
        if index is None:
            index = int(np.random.randint(len(self.query)))
        if self.answer_type == "multipleChoice":
            prompt = self.prompt.format(question=self.query[index], options=self.options[index])
        else:
            prompt = self.prompt.format(question=self.query[index])
        return {
            "id": self.ids[index],
            "category": self.categories[index],
            "prompt": prompt,
            "answer": self.answer[index],
        }

    def get_iterator(self):
        for i in range(len(self.query)):
            yield self.get_example(i)

    def parse_response(self, response: str) -> str:
        """Extract the model answer from a Polymer-style agent reply.

        Priority:
            1. <solution>...</solution>   (A1 default)
            2. unclosed <solution>...     (agent hit stop sequence)
            3. [ANSWER]...[/ANSWER] / <answer>
        """
        if response is None:
            return ""
        text = str(response).strip()
        extracted = None
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
        # strip leftover execute/observation wrappers if the agent dumped a trace
        text = re.sub(r"</?(?:execute|observation|think)[^>]*>", " ", text, flags=re.IGNORECASE)
        text = text.strip()
        if self.answer_type == "multipleChoice":
            # prefer a lone letter on its own line / at start
            lone = re.search(r"^\s*([A-Za-z])\s*[.)]?\s*$", text)
            if lone:
                return lone.group(1).upper()
            letter_match = re.search(r"\b([A-Za-z])\b", text)
            if letter_match:
                return letter_match.group(1).upper()
            if text:
                return text[0].upper()
            return ""
        return text.strip()

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = str(text).strip().lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^a-z0-9.+-]+", " ", text)
        return text.strip()

    @staticmethod
    def parse_rank_list(text: str) -> list[str] | None:
        """Parse an ordered ranking from list / 'a > b > c' / 'a, b, c' forms."""
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

    def looks_like_rank(self, gold: str) -> bool:
        parsed = self.parse_rank_list(gold)
        return bool(parsed and len(parsed) >= 2)

    def _score_one(self, pred: str, gold: str, index: int | None = None) -> float:
        pred_s = "" if pred is None else str(pred).strip()
        gold_s = "" if gold is None else str(gold).strip()
        if not pred_s:
            return 0.0
        if self.answer_type == "multipleChoice":
            return 1.0 if pred_s.upper() == gold_s.upper() else 0.0

        gold_rank = self.parse_rank_list(gold_s)
        pred_rank = self.parse_rank_list(pred_s)
        if gold_rank and len(gold_rank) >= 2:
            if not pred_rank:
                return 0.0
            # order-sensitive: bag-of-letters overlap is not a ranking match
            n = min(len(gold_rank), len(pred_rank))
            if n == 0:
                return 0.0
            exact_prefix = sum(int(gold_rank[i] == pred_rank[i]) for i in range(n))
            if gold_rank == pred_rank:
                return 1.0
            if len(gold_rank) == len(pred_rank):
                return exact_prefix / len(gold_rank)
            return 0.0

        # numeric exact-match with optional relative tolerance stored on the frame
        gold_nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", gold_s)
        pred_nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", pred_s)
        if gold_nums and pred_nums and not gold_rank:
            try:
                pred_n = float(pred_nums[0])
                gold_n = float(gold_nums[0])
                rel = 0.15
                if index is not None and "tolerance_rel" in self._frame.columns:
                    raw = self._frame.iloc[index].get("tolerance_rel")
                    if raw is not None and str(raw) not in {"", "nan", "None"}:
                        rel = float(raw)
                denom = max(abs(gold_n), 1e-12)
                return 1.0 if abs(pred_n - gold_n) / denom <= rel else 0.0
            except (IndexError, ValueError, TypeError):
                pass

        if self._normalize_text(pred_s) == self._normalize_text(gold_s):
            return 1.0
        gold_toks = self._normalize_text(gold_s).split()
        # do not use bag-of-tokens scoring on short golds (rank letters, ids)
        if len(gold_toks) < 8:
            return 0.0
        pred_toks = set(self._normalize_text(pred_s).split())
        gold_set = set(gold_toks)
        overlap = len(gold_set & pred_toks) / len(gold_set)
        return 1.0 if overlap >= 0.5 else overlap

    def evaluate(self, response):
        if len(response) != len(self.answer):
            raise ValueError(
                f"evaluate() expected {len(self.answer)} predictions, got {len(response)}. "
                "Score a subset by slicing the task first or pass only the items you ran."
            )
        parsed = [self.parse_response(item) for item in response]
        scores = [self._score_one(parsed[i], self.answer[i], i) for i in range(len(parsed))]
        parsed_arr = np.array(parsed)
        refrain = self.refrain_label
        covered = parsed_arr != refrain if np.any(refrain != "") else np.ones(len(parsed_arr), dtype=bool)
        out = {
            "n": int(len(scores)),
            "accuracy": float(np.mean(np.array(scores) >= 0.5)) if scores else 0.0,
            "mean_score": float(np.mean(scores)) if scores else 0.0,
        }
        if np.any(refrain != ""):
            out["coverage"] = float(np.mean(covered))
            out["refrain_ratio"] = float(np.mean(parsed_arr == refrain))
            covered_scores = [s for s, c in zip(scores, covered) if c]
            out["precision"] = float(np.mean(np.array(covered_scores) >= 0.5)) if covered_scores else 0.0
        return out

    def evaluate_by_category(self, response):
        parsed = [self.parse_response(item) for item in response]
        rows = []
        for cat in sorted(set(self.categories)):
            idx = np.where(self.categories == cat)[0]
            scores = [self._score_one(parsed[i], self.answer[i], i) for i in idx]
            rows.append(
                {
                    "category": cat,
                    "n": int(len(idx)),
                    "accuracy": float(np.mean(np.array(scores) >= 0.5)) if scores else 0.0,
                    "mean_score": float(np.mean(scores)) if scores else 0.0,
                }
            )
        return rows

    def output_class(self):
        from pydantic import BaseModel, Field

        class MultipleChoiceOutput(BaseModel):
            """Multiple choice output."""

            choice: str | None = Field(
                description=(
                    "Final answer only. For multiple choice this is a single letter "
                    "as it would appear inside <solution>A</solution>."
                )
            )

        class ExactMatchOutput(BaseModel):
            """Short exact-match output."""

            value: str | None = Field(description="Short exact answer string.")

        return MultipleChoiceOutput if self.answer_type == "multipleChoice" else ExactMatchOutput


class polymer_hle(polymer_bench):
    """HLE-style wrapper: expert knowledge questions only."""

    def __init__(self, path: str = "./data", category: str = "KnowledgeQA", answer_type: str = "multipleChoice"):
        super().__init__(path=path, dataset=category if category in DATASETS else "KnowledgeQA", answer_type=answer_type)


class polymer_lab_bench(polymer_bench):
    """LAB-Bench-style wrapper: tool-leaning polymer subtasks."""

    def __init__(self, path: str = "./data", dataset: str = "DbQA"):
        if dataset not in ("DbQA", "StructQA", "ProtocolQA", "PropQA"):
            raise ValueError("dataset must be one of 'DbQA', 'StructQA', 'ProtocolQA', 'PropQA'")
        super().__init__(path=path, dataset=dataset, answer_type="multipleChoice")


if __name__ == "__main__":
    task = polymer_bench(path=str(Path(__file__).resolve().parent / "data"), dataset="All")
    print(f"loaded {len(task)} items")
    print("categories:", task.evaluate_by_category([task.answer[i] for i in range(len(task))]))
    print("--- example 0 ---")
    print(task.get_example(0)["prompt"][:600])
    print("gold:", task.get_example(0)["answer"])