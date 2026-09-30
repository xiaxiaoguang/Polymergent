#!/usr/bin/env python3
"""
Visualize agent evaluation results.

Expected layout (root = the folder you pass in):
    root/agent_name/task_name/experiment_index/eval_results.json
(eval_results.json may also sit one level deeper, e.g. experiment_index/llm/eval_results.json;
the script searches recursively.)

Usage:
    python viz_results.py /path/to/history
    python viz_results.py /path/to/history --section evaluate_judged --out ./viz_out
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Fixed categorical hue order (validated for CVD-safe adjacency; see the
# dataviz skill's palette.md). Color encodes *run type* only -- "llm" vs
# "agent" (the thing the project is actually comparing) -- each getting the
# next hue in this fixed order, never cycled/re-picked. It does NOT encode
# which company/model (deepseek, gpt, ...) produced the run, so a given run
# type is the same color everywhere: every task, every company.
CATEGORICAL_PALETTE = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
]

# Preferred order for the two run types this project cares about; any other
# run name found in the data is appended after these, in sorted order.
RUN_TYPE_ORDER = ["llm", "agent"]


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in rgb))


def shade(hex_color: str, factor: float) -> str:
    """Blend hex_color toward white (factor > 0) or black (factor < 0)."""
    r, g, b = _hex_to_rgb(hex_color)
    target = (255, 255, 255) if factor >= 0 else (0, 0, 0)
    f = abs(factor)
    blended = (r + (target[0] - r) * f, g + (target[1] - g) * f, b + (target[2] - b) * f)
    return _rgb_to_hex(blended)


def build_run_color_map(runs):
    """run type ("llm", "agent", ...) -> fixed hex, same everywhere.

    llm/agent are the two things this project compares, so color is keyed
    on run type alone -- not on company/agent name -- and stays identical
    across every company and every task.
    """
    ordered = [r for r in RUN_TYPE_ORDER if r in runs]
    ordered += sorted(r for r in runs if r not in RUN_TYPE_ORDER)
    if len(ordered) > len(CATEGORICAL_PALETTE):
        print(f"[warn] {len(ordered)} run types but only {len(CATEGORICAL_PALETTE)} "
              "distinct hues are validated as CVD-safe; hues will repeat.",
              file=sys.stderr)
    return {r: CATEGORICAL_PALETTE[i % len(CATEGORICAL_PALETTE)] for i, r in enumerate(ordered)}


def load_rows(root: Path, section: str) -> pd.DataFrame:
    rows = []
    for f in sorted(root.rglob("eval_results.json")):
        rel = f.parent.relative_to(root).parts
        agent = rel[0] if len(rel) > 0 else "?"
        task = rel[1] if len(rel) > 1 else "?"
        experiment = rel[2] if len(rel) > 2 else "?"
        try:
            data = json.loads(f.read_text())
        except Exception as e:  # noqa: BLE001
            print(f"[warn] cannot read {f}: {e}", file=sys.stderr)
            continue

        runs = data.get("runs", {}) or {}
        for run_name, run in runs.items():  # e.g. "llm", "agent"
            if not isinstance(run, dict):
                continue
            sec = run.get(section)
            if not isinstance(sec, dict):
                continue
            rows.append(
                {
                    "agent": agent,
                    "task": task,
                    "experiment": experiment,
                    "run": run_name,
                    "n": sec.get("n", run.get("n")),
                    "accuracy": sec.get("accuracy"),
                    "mean_score": sec.get("mean_score"),
                    "seconds": run.get("seconds"),
                    "timestamp_utc": data.get("timestamp_utc"),
                    "path": str(f),
                }
            )
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["agent", "task", "run"], dropna=False)
    out = g.agg(
        experiments=("experiment", "nunique"),
        accuracy_mean=("accuracy", "mean"),
        accuracy_std=("accuracy", "std"),
        score_mean=("mean_score", "mean"),
        score_std=("mean_score", "std"),
    ).reset_index()
    return out.fillna({"accuracy_std": 0.0, "score_std": 0.0})


def plot_summary(summary: pd.DataFrame, out_path: Path, section: str):
    """Grouped bars: x = (agent, task) combo, one bar per run type, colored
    only by run type (llm vs agent) -- that color is the same for every
    company/task; company/task is just the x-axis grouping, not a color."""
    groups = list(summary[["agent", "task"]].drop_duplicates()
                  .sort_values(["agent", "task"]).itertuples(index=False, name=None))
    runs = sorted(summary["run"].unique())
    color_map = build_run_color_map(runs)

    x = np.arange(len(groups))
    n = max(len(runs), 1)
    w = min(0.8 / n, 0.32)

    fig, (ax_acc, ax_score) = plt.subplots(2, 1, figsize=(max(8, 1.4 * len(groups) * n + 2), 9),
                                            sharex=True)

    for ax, col_mean, col_std, ylabel, show_legend in (
        (ax_acc, "accuracy_mean", "accuracy_std", "accuracy", True),
        (ax_score, "score_mean", "score_std", "mean_score", False),
    ):
        for i, run in enumerate(runs):
            offset = (i - (n - 1) / 2) * w
            sub = summary[summary["run"] == run].set_index(["agent", "task"])
            heights = [sub[col_mean].get(g, np.nan) for g in groups]
            errs = [sub[col_std].get(g, 0.0) for g in groups]
            bars = ax.bar(x + offset, heights, w, yerr=errs, capsize=2,
                           color=color_map[run], label=run if show_legend else None)
            for b, h in zip(bars, heights):
                if not np.isnan(h):
                    ax.annotate(f"{h:.2f}", (b.get_x() + b.get_width() / 2, h),
                                ha="center", va="bottom", fontsize=7,
                                xytext=(0, 2), textcoords="offset points")
        ax.set_ylim(0, 1.1)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.3)

    ax_score.set_xticks(x)
    ax_score.set_xticklabels([f"{a}\n{t}" for a, t in groups], fontsize=8)
    ax_score.set_xlabel("agent / task")
    ax_acc.set_title(f"Accuracy & mean score  (section: {section})\n"
                      "bars = mean over experiments, whiskers = std -- "
                      "color = run type (llm vs agent) only")
    ax_acc.legend(title="run", fontsize=8, title_fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def plot_table(df: pd.DataFrame, out_path: Path, title: str):
    cols = ["agent", "task", "experiment", "run", "n", "accuracy", "mean_score", "seconds"]
    t = df[cols].copy()
    for c in ("accuracy", "mean_score", "seconds"):
        t[c] = t[c].map(lambda v: "" if pd.isna(v) else f"{v:.3f}")

    color_map = build_run_color_map(df["run"].unique())
    # pale tint of the same run-type color used in the chart, so rows
    # visually match their bars; text stays plain ink, color only marks identity.
    row_colors = [shade(color_map[r], 0.82) for r in df["run"]]

    fig_h = max(2.0, 0.35 * (len(t) + 2))
    fig, ax = plt.subplots(figsize=(12, fig_h))
    ax.axis("off")
    tbl = ax.table(cellText=t.values, colLabels=cols, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.auto_set_column_width(list(range(len(cols))))
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor("#e8e8e8")
        else:
            cell.set_facecolor(row_colors[r - 1])
    ax.set_title(title, fontsize=11, pad=10)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Visualize eval_results.json files.")
    ap.add_argument("root", type=Path, help="Root folder: agent/task/experiment/eval_results.json")
    ap.add_argument("--section", default="evaluate",
                    choices=["evaluate", "evaluate_judged"],
                    help="Which metrics block to read from runs.<name> (default: evaluate)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output folder (default: <root>/viz_output)")
    args = ap.parse_args()

    root = args.root.expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"Not a directory: {root}")
    out = (args.out or root / "viz_output").expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    df = load_rows(root, args.section)
    if df.empty:
        sys.exit(f"No eval_results.json with runs.*.{args.section} found under {root}")

    df = df.sort_values(["agent", "task", "run", "experiment"]).reset_index(drop=True)
    summary = summarize(df)

    df.to_csv(out / "results_all.csv", index=False)
    summary.to_csv(out / "results_summary.csv", index=False)
    plot_summary(summary, out / "results_chart.png", args.section)
    plot_table(df, out / "results_table.png", f"All experiments (section: {args.section})")

    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(df.drop(columns=["path", "timestamp_utc"]).to_string(index=False))
        print("\nSummary:")
        print(summary.round(4).to_string(index=False))
    print(f"\nSaved to: {out}")


if __name__ == "__main__":
    main()