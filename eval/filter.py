#!/usr/bin/env python3
"""Filter polymer eval dataset to IDs that appear in filter_report JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def collect_ids_from_report(report: dict) -> set[str]:
    ids: set[str] = set()
    items = report.get("items") or []
    for item in items:
        item_id = item.get("id")
        if item_id:
            ids.add(str(item_id))
    return ids


def collect_ids_from_reports(paths: Iterable[Path]) -> set[str]:
    all_ids: set[str] = set()
    for path in paths:
        report = load_json(path)
        ids = collect_ids_from_report(report)
        print(f"[report] {path}: {len(ids)} ids")
        all_ids |= ids
    return all_ids


def filter_dataset(dataset: dict, keep_ids: set[str]) -> dict:
    tasks = dataset.get("tasks") or []
    kept = [t for t in tasks if str(t.get("id", "")) in keep_ids]
    out = dict(dataset)
    out["tasks"] = kept
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Keep only dataset tasks whose ids appear in filter_report files."
    )
    p.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Source dataset JSON (tasks[] with id like polyreal_1)",
    )
    p.add_argument(
        "--reports",
        required=True,
        nargs="+",
        type=Path,
        help="One or more filter_report JSON files",
    )
    p.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output filtered dataset JSON",
    )
    p.add_argument(
        "--only-failed",
        action="store_true",
        help="Keep only items with passed == false in the reports",
    )
    p.add_argument(
        "--only-passed",
        action="store_true",
        help="Keep only items with passed == true in the reports",
    )
    return p.parse_args()


def collect_ids_filtered(paths: Iterable[Path], only_failed: bool, only_passed: bool) -> set[str]:
    all_ids: set[str] = set()
    for path in paths:
        report = load_json(path)
        items = report.get("items") or []
        n_raw = 0
        n_keep = 0
        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue
            n_raw += 1
            passed = item.get("passed")
            if only_failed and passed is not False:
                continue
            if only_passed and passed is not True:
                continue
            all_ids.add(str(item_id))
            n_keep += 1
        print(f"[report] {path}: raw={n_raw} kept_ids={n_keep}")
    return all_ids


def main() -> None:
    args = parse_args()
    if args.only_failed and args.only_passed:
        raise SystemExit("Use only one of --only-failed / --only-passed")

    if args.only_failed or args.only_passed:
        keep_ids = collect_ids_filtered(args.reports, args.only_failed, args.only_passed)
    else:
        keep_ids = collect_ids_from_reports(args.reports)

    print(f"[union] unique ids from reports: {len(keep_ids)}")

    dataset = load_json(args.dataset)
    n_in = len(dataset.get("tasks") or [])
    filtered = filter_dataset(dataset, keep_ids)
    n_out = len(filtered.get("tasks") or [])
    missing = keep_ids - {str(t.get("id", "")) for t in filtered["tasks"]}

    print(f"[dataset] input tasks={n_in} output tasks={n_out}")
    if missing:
        print(f"[warn] {len(missing)} report ids not found in dataset, e.g. {sorted(missing)[:10]}")

    dump_json(args.out, filtered)
    print(f"[wrote] {args.out}")


if __name__ == "__main__":
    main()