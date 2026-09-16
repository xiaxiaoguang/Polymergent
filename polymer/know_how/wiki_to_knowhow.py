#!/usr/bin/env python3
"""Fetch Wikipedia extracts and write KnowHowLoader markdown.

Default path (no API key): deterministic splitter into short passages.
Optional path: set OPENAI_API_KEY or ANTHROPIC_API_KEY to rewrite passages
with an LLM. Output is always the Polymer know-how layout:

    # Title
    ---
    ## Metadata
    **Short Description**: ...
    ---
    ## Overview
    ...
    ## Section
    brief passage
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "PolymerKnowhowBot/0.2 (educational; know-how corpus)"

DEFAULT_TITLES = [
    # Polymer physics / characterization relationships
    # "Carothers equation",
    # "Flory–Fox equation",
    # "Mark–Houwink equation",
    # "Mayo–Lewis equation",
    # "Williams–Landel–Ferry equation",
    # "Flory–Huggins solution theory",
    # "Glass transition",
    # "Molar mass distribution",
    # "Gelation",
    # "Simplified molecular-input line-entry system",

    # Polymerization mechanisms
    # "Step-growth polymerization",
    # "Free-radical polymerization",
    # "Ring-opening polymerization",
    # "Living polymerization",
    # "Anionic addition polymerization",
    # "Cationic polymerization",
    # "Atom transfer radical polymerization",
    # "Reversible addition−fragmentation chain-transfer polymerization",
    # "Ziegler–Natta catalyst",
    # "Emulsion polymerization",
    "Coordination polymerization",

    # Polymer structure / architecture / properties
    "Copolymer",
    "Block copolymer",
    "Graft polymerization",
    "Star polymer",
    "Dendrimer",
    "Cross-link",
    "Vulcanization",
    "Thermoplastic",
    "Thermosetting polymer",
    "Elastomer",
    "Polymer degradation",
    "Biodegradable polymer",
    "Conducting polymer",
    "Polymer brush",

    # Common industrial polymers
    "Polyethylene",
    "Polypropylene",
    "Polystyrene",
    "Nylon",
    "Polyester",
    "Epoxy",
    "Polyurethane",
    "Silicone",
    "Polyvinyl chloride",
    "Poly(methyl methacrylate)",

    # Organic synthesis: strategy and named reactions
    "Organic synthesis",
    "Total synthesis",
    "Retrosynthetic analysis",
    "Protecting group",
    "Asymmetric synthesis",
    "Green chemistry",
    "Click chemistry",
    "Grignard reaction",
    "Wittig reaction",
    "Diels–Alder reaction",
    "Aldol reaction",
    "Friedel–Crafts reaction",
    "Fischer esterification",
    "Claisen condensation",
    "Suzuki reaction",
    "Heck reaction",
    "Organometallic chemistry",
]


def fetch_extract(title: str, timeout: int = 20) -> tuple[str, str]:
    q = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "exlimit": 1,
            "titles": title,
            "format": "json",
            "redirects": 1,
        }
    )
    req = urllib.request.Request(
        "https://en.wikipedia.org/w/api.php?" + q,
        headers={"User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    page = next(iter(data["query"]["pages"].values()))
    if "extract" not in page:
        raise RuntimeError(f"no extract for {title!r}")
    return page.get("title", title), page["extract"]


def split_passages(text: str, max_chars: int = 420) -> list[tuple[str, str]]:
    """Split wiki extract into (heading, short paragraph) pairs."""
    blocks = re.split(r"\n(?==+ )", text)
    out: list[tuple[str, str]] = []
    current = "Background"
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        m = re.match(r"=+\s*(.+?)\s*=+\s*\n?(.*)", block, re.S)
        if m:
            current = m.group(1).strip()
            body = m.group(2).strip()
        else:
            body = block
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        buf = ""
        for p in paras:
            p = re.sub(r"\s+", " ", p)
            if len(p) > max_chars:
                sentences = re.split(r"(?<=[.!?])\s+", p)
                chunk = ""
                for s in sentences:
                    if len(chunk) + len(s) + 1 <= max_chars:
                        chunk = (chunk + " " + s).strip()
                    else:
                        if chunk:
                            out.append((current, chunk))
                        chunk = s[:max_chars]
                if chunk:
                    out.append((current, chunk))
                continue
            if not buf:
                buf = p
            elif len(buf) + 1 + len(p) <= max_chars:
                buf = buf + " " + p
            else:
                out.append((current, buf))
                buf = p
        if buf:
            out.append((current, buf))
    return out[:24]


def llm_rewrite(title: str, extract: str) -> str | None:
    """Optional rewrite. Returns full markdown or None to fall back."""
    prompt = f"""Rewrite the Wikipedia extract into Polymer know-how markdown.

Rules:
- First line: # {title}
- Then ---
- ## Metadata with **Short Description** (one sentence, <160 chars),
  **Authors**: Wikipedia contributors, **License**: CC BY-SA 4.0,
  **Source**: https://en.wikipedia.org/wiki/{title.replace(" ", "_")}
- Then ---
- ## Overview (2-3 short sentences)
- Then several ## headings. Under each heading, 1-3 brief passages
  (max ~80 words each). No long quotes. Keep equations in $...$ or plain text.
- Do not invent facts not in the extract.

EXTRACT:
{extract[:8000]}
"""
    key = os.getenv("OPENAI_API_KEY")
    if key:
        try:
            import urllib.request as ur

            body = json.dumps(
                {
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                }
            ).encode()
            req = ur.Request(
                "https://api.openai.com/v1/chat/completions",
                data=body,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "User-Agent": UA,
                },
                method="POST",
            )
            with ur.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode())
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            print("LLM failed, falling back:", exc)
            return None
    return None


def render_md(title: str, extract: str, slug: str) -> str:
    rewritten = llm_rewrite(title, extract)
    if rewritten and rewritten.lstrip().startswith("#"):
        return rewritten.strip() + "\n"

    passages = split_passages(extract)
    overview = passages[0][1] if passages else f"Short notes on {title}."
    if len(overview) > 280:
        overview = overview[:277] + "..."
    short = overview if len(overview) <= 160 else overview[:157] + "..."
    wiki = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
    lines = [
        f"# {title}",
        "",
        "---",
        "",
        "## Metadata",
        "",
        f"**Short Description**: {short}",
        "",
        "**Authors**: Wikipedia contributors",
        "",
        "**Version**: 1.0",
        "",
        "**Last Updated**: 2026-09-11",
        "",
        "**License**: CC BY-SA 4.0",
        "",
        "**Commercial Use**: Allowed with attribution",
        "",
        f"**Source**: {wiki}",
        "",
        "---",
        "",
        "## Overview",
        "",
        overview,
        "",
    ]
    seen: set[str] = set()
    for heading, para in passages[1:] if len(passages) > 1 else passages:
        h = heading.strip() or "Notes"
        if h not in seen:
            lines.append(f"## {h}")
            lines.append("")
            seen.add(h)
        lines.append(para)
        lines.append("")
    return "\n".join(lines)


def slugify(title: str) -> str:
    s = title.lower()
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(Path(__file__).parent))
    p.add_argument("--titles", nargs="*", default=DEFAULT_TITLES)
    p.add_argument("--sleep", type=float, default=20)
    p.add_argument("--from-txt-dir", default="", help="Use local TITLE.txt extracts if present")
    args = p.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for title in args.titles:
        slug = slugify(title)
        local = None
        if args.from_txt_dir:
            cand = Path(args.from_txt_dir) / (title.replace(" ", "_") + ".txt")
            if cand.exists():
                raw = cand.read_text(encoding="utf-8")
                local = raw.split("\n", 1)[-1]
        try:
            if local:
                resolved, extract = title, local
            else:
                resolved, extract = fetch_extract(title)
                time.sleep(args.sleep)
        except Exception as exc:
            print("SKIP", title, exc)
            continue
        md = render_md(resolved, extract, slug)
        path = out_dir / f"{slug}.md"
        path.write_text(md, encoding="utf-8")
        print("WROTE", path, "chars", len(md))


if __name__ == "__main__":
    main()