#!/usr/bin/env python3
"""Post-process already-downloaded KnowHowLoader markdown files for RETRIEVAL.

Two things were wrong with the raw Wikipedia-derived files:

1. The **Short Description** was a truncated first sentence of the extract,
   not a description of *when an LLM should retrieve this document*. A good
   retrieval description reads like a tool/skill description: what problem
   does this doc help solve, and what concepts/keywords does it cover.

2. The body was a mechanically-chopped Wikipedia extract: long, repetitive,
   and full of prose that doesn't help an LLM that has already retrieved the
   doc and just needs the load-bearing facts (definitions, key equations,
   mechanisms, applications, caveats).

This script fixes both in one Claude call per file:
  - a new **Short Description**, written for a retriever/router deciding
    "does the model need this doc to answer query X" — not a content summary.
  - a condensed body that REPLACES the Overview + section content with a
    denser, shorter version, organized under a small number of headings.

It does not re-download anything — it only rewrites files already on disk.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 post_process_descriptions.py --dir ./knowhow_md

Dry run (prints the new description + condensed body without writing):
    python3 post_process_descriptions.py --dir ./knowhow_md --dry-run

Spot-check a handful before committing to a full run:
    python3 post_process_descriptions.py --dir ./knowhow_md --limit 5 --dry-run

By default a .orig.md backup of each file is written alongside it before
it's overwritten; pass --no-backup to skip that.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = "PolymerKnowhowBot/0.3 (post-process; retrieval description + condense)"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

SHORT_DESC_RE = re.compile(r"^\*\*Short Description\*\*:\s*(.*)$", re.MULTILINE)
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

DESC_TAG = "SHORT_DESCRIPTION"
BODY_TAG = "CONDENSED_BODY"
DESC_RE = re.compile(rf"###{DESC_TAG}###\s*(.*?)\s*###{BODY_TAG}###", re.DOTALL)
BODY_RE = re.compile(rf"###{BODY_TAG}###\s*(.*)", re.DOTALL)


def split_sections(content: str) -> tuple[str, str, str]:
    """Split a rendered know-how file into (title_and_metadata_block, body, title).

    The file layout is:
        # Title
        ---
        ## Metadata
        ...
        ---
        ## Overview
        ...body...
    We keep everything up to and including the second "---" untouched
    (title + metadata), and treat everything after it as replaceable body.
    """
    title = TITLE_RE.search(content)
    title_str = title.group(1).strip() if title else "Unknown"

    parts = content.split("---")
    if len(parts) >= 3:
        head = "---".join(parts[:2]) + "---"
        body = "---".join(parts[2:]).strip()
    else:
        # Unexpected layout: treat whole thing as body, no head to preserve.
        head = content
        body = ""
    return head, body, title_str


def build_prompt(title: str, body: str, desc_max_chars: int, target_words: int) -> str:
    return f"""You are preparing a technical reference file for a retrieval system
that an LLM agent queries while solving problems. The agent sees only the
short description when deciding WHETHER to pull in this document, and sees
the condensed body only after it has decided to retrieve it.

TITLE: {title}

ORIGINAL CONTENT (verbose, from Wikipedia):
---
{body}
---

Produce exactly two things, in this exact format with these exact tags and
nothing else before, between, or after them:

###{DESC_TAG}###
<one sentence, under {desc_max_chars} characters, written for a RETRIEVER
deciding whether to fetch this doc. Do NOT summarize the content. Instead
say what kinds of problems/questions this document helps solve and list the
key concepts, quantities, or terms it covers, so a router can match it
against a user's query. Style example: "Use when computing X or explaining
Y; covers concept A, concept B, equation relating C to D, and term E."
Do not invent facts not in the content.>

###{BODY_TAG}###
<a condensed version of the content, roughly {target_words} words (shorter
than the original by a large margin), organized under 2-5 markdown "##"
headings such as Definition, Key Equations, Mechanism, Applications, or
Limitations (use whichever actually apply; skip ones with nothing to say).
Preserve every formula, named quantity, and specific fact that a model would
need to actually use this knowledge to solve a problem. Drop history,
repetition, tangents, and flowery prose. Terse factual sentences or short
bullet points are fine and preferred over narrative prose. Do not invent
facts not in the original content.>
"""


def call_claude(prompt: str, model: str, api_key: str, max_tokens: int,
                 timeout: int = 90, max_retries: int = 4) -> str:
    body = json.dumps(
        {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
            "User-Agent": UA,
        },
        method="POST",
    )
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            chunks = data.get("content", [])
            text = "".join(c.get("text", "") for c in chunks if c.get("type") == "text")
            return text.strip()
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code == 429 or exc.code >= 500:
                wait = min(2 ** attempt * 2, 30)
                print(f"  retrying after HTTP {exc.code} in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError as exc:
            last_exc = exc
            wait = min(2 ** attempt * 2, 30)
            print(f"  retrying after network error ({exc}) in {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
    raise RuntimeError(f"Claude call failed after {max_retries} attempts: {last_exc}")


def clean_description(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] in "\"'" and text[-1] in "\"'":
        text = text[1:-1].strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "..."
    return text


def parse_response(raw: str) -> tuple[str, str] | None:
    desc_m = DESC_RE.search(raw)
    body_m = BODY_RE.search(raw)
    if not desc_m or not body_m:
        return None
    return desc_m.group(1).strip(), body_m.group(1).strip()


def process_file(path: Path, model: str, api_key: str, desc_max_chars: int,
                  target_words: int, dry_run: bool, backup: bool) -> tuple[bool, str]:
    content = path.read_text(encoding="utf-8")
    head, body, title = split_sections(content)
    if not body:
        return False, "no body content found, skipped"
    if not SHORT_DESC_RE.search(head):
        return False, "no **Short Description** line found in head, skipped"

    prompt = build_prompt(title, body, desc_max_chars, target_words)
    # Budget generously: condensed body target_words * ~1.6 tokens/word + description.
    max_tokens = max(400, int(target_words * 2.2) + 150)
    try:
        raw = call_claude(prompt, model=model, api_key=api_key, max_tokens=max_tokens)
    except Exception as exc:
        return False, f"LLM call failed: {exc}"

    parsed = parse_response(raw)
    if not parsed:
        return False, "could not parse LLM response (missing tags), skipped"
    new_desc, new_body = parsed
    new_desc = clean_description(new_desc, desc_max_chars)
    if not new_desc or not new_body:
        return False, "LLM returned empty description or body, skipped"

    old_desc_m = SHORT_DESC_RE.search(head)
    old_desc = old_desc_m.group(1).strip() if old_desc_m else "(none)"
    old_len = len(body.split())
    new_len = len(new_body.split())

    print(f"  old desc: {old_desc}")
    print(f"  new desc: {new_desc}")
    print(f"  body: {old_len} words -> {new_len} words")

    if dry_run:
        return True, "dry-run (not written)"

    if backup:
        backup_path = path.with_suffix(".orig.md")
        if not backup_path.exists():
            backup_path.write_text(content, encoding="utf-8")

    new_head = SHORT_DESC_RE.sub(
        lambda _: f"**Short Description**: {new_desc}", head, count=1
    )
    new_content = new_head.rstrip("\n") + "\n\n" + new_body.strip() + "\n"
    path.write_text(new_content, encoding="utf-8")
    return True, "updated"
# 
# python post_process.py --no-backup --dir "/home/hcao5/workspace/polymer/polymer/know_how" --model claude-haiku-4-5-20251001

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True, help="Folder containing the .md know-how files")
    p.add_argument("--pattern", default="*.md", help="Glob pattern within --dir (default *.md)")
    p.add_argument("--model", default="claude-haiku-4-5-20251001",
                   help="Anthropic model id. Consider a Sonnet model for better condensation quality.")
    p.add_argument("--desc-max-chars", type=int, default=200,
                   help="Max length enforced on the generated retrieval description")
    p.add_argument("--target-words", type=int, default=250,
                   help="Approximate target word count for the condensed body")
    p.add_argument("--sleep", type=float, default=0.5,
                   help="Seconds to sleep between files (rate-limit friendliness)")
    p.add_argument("--limit", type=int, default=0,
                   help="Only process the first N matching files (0 = all)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print old/new content but do not write files")
    p.add_argument("--no-backup", dest="backup", action="store_false",
                   help="Skip writing a <name>.orig.md backup before overwriting")
    p.set_defaults(backup=True)
    args = p.parse_args()

    # Skip any previously-written backup files if the pattern would catch them.
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    files = sorted(
        f for f in glob.glob(str(Path(args.dir) / args.pattern))
        if not f.endswith(".orig.md")
    )
    if args.limit:
        files = files[: args.limit]
    if not files:
        print(f"No files matched {args.pattern!r} in {args.dir}")
        return

    ok = 0
    skipped = 0
    for i, f in enumerate(files, 1):
        path = Path(f)
        print(f"[{i}/{len(files)}] {path.name}")
        success, msg = process_file(
            path, model=args.model, api_key=api_key,
            desc_max_chars=args.desc_max_chars, target_words=args.target_words,
            dry_run=args.dry_run, backup=args.backup,
        )
        if success:
            ok += 1
        else:
            skipped += 1
            print(f"  SKIP: {msg}")
        if i < len(files):
            time.sleep(args.sleep)

    print(f"\nDone. {ok} updated, {skipped} skipped, {len(files)} total.")
    if ok and not args.dry_run and args.backup:
        print("Originals preserved alongside as <name>.orig.md.")


if __name__ == "__main__":
    main()