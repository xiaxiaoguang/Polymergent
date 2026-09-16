"""PaperTaskExtractor with a cheap metadata gate before any expensive LLM pass.

Design goals
------------
1. Do not chunk a 200k-character PDF into Claude calls by default.
2. Enrich / filter on title + abstract + category + keywords first.
   Those fields already exist in chemrxiv_metadata.csv / Crossref / arXiv-style APIs.
3. Only then run a *single* targeted extraction prompt on the relevant
   perspective + methods-like sections.
4. Optional cheap_llm is used only for keyword/perspective tagging when
   the rule-based tagger is too thin. The main llm is used at most twice
   per accepted paper (extract + optional JSON repair).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter

from polymer.agent.base_agent import base_agent

# ---------------------------------------------------------------------------
# Cheap, no-LLM tagging. These lists are routing features, not a chemistry ontology.
# ---------------------------------------------------------------------------

# Ten data lakes. Each lake becomes one CSV; a paper is a row in every lake it belongs to.
LAKE_TAXONOMY = {
    "electronic_structure": {
        "description": "Quantum chemistry and electronic structure (DFT, wavefunction, orbitals, resonances)",
        "keywords": (
            "dft", "density functional", "hartree", "orbital", "q-chem", "gaussian",
            "orca", "psi4", "vasp", "cp2k", "resonance", "dyson", "basis set", "tddft",
        ),
    },
    "molecular_simulation": {
        "description": "Molecular dynamics, Monte Carlo, free-energy and statistical-mechanics simulations",
        "keywords": (
            "molecular dynamics", "lammps", "gromacs", "openmm", "amber", "ase",
            "free energy", "jarzynski", "umbrella", "force field", "monte carlo",
        ),
    },
    "biomolecular_modeling": {
        "description": "Proteins/nucleic acids: docking, PPI, homology, ADMET on biomolecules",
        "keywords": (
            "docking", "protein", "ligand", "pdb", "ppi", "uniprot", "admet",
            "autodock", "vina", "homology", "binding pose",
        ),
    },
    "materials_solids": {
        "description": "Materials, polymers, crystals, surfaces, batteries, adsorption",
        "keywords": (
            "polymer", "crystal", "mof", "perovskite", "battery", "adsorption",
            "thin film", "band gap", "surface", "alloy", "framework",
        ),
    },
    "ml_datasets_benchmarks": {
        "description": "ML models, datasets, splits, benchmarks, learned molecular/protein representations",
        "keywords": (
            "dataset", "benchmark", "graph neural", "machine learning", "classifier",
            "embedding", "train", "split", "esm", "fingerprint",
        ),
    },
    "spectroscopy_signals": {
        "description": "Spectra and time traces (NMR, EPR/DEER, optical) and their analysis",
        "keywords": (
            "deer", "ridme", "epr", "nmr", "spectrum", "spectroscop", "form factor",
            "pds", "ir spectrum", "raman", "uv-vis",
        ),
    },
    "synthesis_catalysis": {
        "description": "Synthetic methods, catalysts, reaction conditions, yields, substrate scope",
        "keywords": (
            "synthe", "catalyst", "catalysis", "yield", "ligand", "coupling",
            "hydrogenation", "photoredox", "turnover", "substrate scope",
        ),
    },
    "thermochemistry_kinetics": {
        "description": "Thermochemistry, barriers, rates, mechanisms as energy/kinetics results",
        "keywords": (
            "activation energy", "rate constant", "barrier", "enthalpy", "entropy",
            "kinetics", "arrhenius", "transition state", "gibbs",
        ),
    },
    "cheminformatics_databases": {
        "description": "Chemical databases, identifiers, screening libraries, cheminformatics toolkits",
        "keywords": (
            "pubchem", "chembl", "zinc", "smiles", "inchi", "rdkit", "database",
            "library", "descriptor", "qsar",
        ),
    },
    "analytical_characterization": {
        "description": "Experimental characterization of composition/structure/purity (XRD, MS, chromatography, microscopy)",
        "keywords": (
            "xrd", "mass spectrom", "hplc", "gc-ms", "nmr characterization",
            "sem", "tem", "dsc", "tga", "chromatograph",
        ),
    },
}

# Back-compat alias used by enrich_metadata / should_extract
TOPIC_TAXONOMY = LAKE_TAXONOMY
PERSPECTIVES = LAKE_TAXONOMY
ALLOWED_TOPICS = tuple(LAKE_TAXONOMY.keys())
LAKE_IDS = ALLOWED_TOPICS
MAX_LAKES_PER_PAPER = 3

SECTION_HINTS = {
    "methods": re.compile(
        r"(?im)^(#{0,3}\s*)?(materials and methods|methods|experimental(?: section)?|"
        r"computational (?:details|methods)|theoretical methods|"
        r"simulation details|protocol)\b"
    ),
    "data": re.compile(
        r"(?im)^(#{0,3}\s*)?(data availability|code availability|software|"
        r"computational resources)\b"
    ),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _lower(text: str) -> str:
    return _normalize(text).lower()


class PaperTaskExtractor(base_agent):
    """Extract computational tasks / databases / software from papers.

    Call sequence intended for the ChemRxiv lake:

        extractor = PaperTaskExtractor(llm=..., cheap_llm=...)
        meta = extractor.enrich_metadata(row_from_csv)   # no LLM by default
        if extractor.should_extract(meta, perspectives=["computational", "data_software"]):
            log, result = extractor.go(paper_text, metadata=meta)
    """

    def __init__(
        self,
        llm="claude-3-7-sonnet-20250219",
        cheap_llm=None,
        tools=None,
        chunk_size=8000,
        chunk_overlap=200,
        max_extract_chars=24000,
        use_cheap_llm_for_tags=False,
    ):
        super().__init__(llm, cheap_llm, tools)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_extract_chars = max_extract_chars
        self.use_cheap_llm_for_tags = use_cheap_llm_for_tags
        self.log: list[Any] = []
        self.configure()

    def configure(self):
        self.tag_prompt = """Assign this paper to 1-3 data lakes from the closed list.
Do not invent lake ids.

LAKES:
{taxonomy}

Return JSON:
  lakes: [{{"id": "...", "confidence": 0.0-1.0}}]
  keywords: 5-8 short keywords
  extract_worth: true if the paper reports a concrete chemical/computational result

TITLE: {title}
ABSTRACT: {abstract}
CATEGORY: {category}
"""

        self.extraction_prompt = """You write lake records for a chemistry/computational paper.

Each selected lake is a slice of a data lake. For EVERY selected lake, extract
GROUND TRUTH from this paper: systems studied, methods used, numbers if present,
software/databases named. Then write why the paper belongs in that lake.

Rules:
- lake_id MUST be one of the closed list.
- Select 1 to 3 lakes. Prefer candidate lakes: {perspectives}
- related_reason = why this paper belongs in that lake (2-4 sentences).
- ground_truth = facts the paper actually reports (systems, conditions, metrics).
  Do not invent values that are not in the text.
- Do NOT invent fine-grained task names.

LAKES:
{taxonomy}

Return JSON only:
{{
  "lakes": [
    {{
      "lake_id": "materials_solids",
      "confidence": 0.8,
      "related_reason": "...",
      "ground_truth": "...",
      "systems": "what chemical/material/protein system",
      "methods": "named methods",
      "software": "comma-separated canonical names or empty",
      "databases": "comma-separated canonical names or empty"
    }}
  ]
}}

TITLE: {title}
KEYWORDS: {keywords}

SOURCE TEXT:
{source_text}
"""

        self.consolidation_prompt = """Merge partial JSON into {{"lakes": [...]}}.
Each lake_id MUST be one of: {allowed}
At most 3 lakes. Deduplicate by lake_id and keep the richer ground_truth.
JSON only.

PARTIAL EXTRACTS:
{task_lists}
"""

    # ------------------------------------------------------------------
    # Cheap metadata gate (Crossref / ChemRxiv CSV / arXiv-style fields)
    # ------------------------------------------------------------------

    def enrich_metadata(self, row: dict[str, Any]) -> dict[str, Any]:
        """Add keywords + perspective scores from title/abstract/category.

        No LLM unless use_cheap_llm_for_tags=True and the rule tagger
        finds nothing. This is the ChemRxiv analogue of using arXiv
        title/abstract/categories before touching the PDF.
        """
        title = _normalize(str(row.get("title") or ""))
        abstract = _normalize(str(row.get("abstract") or ""))
        category = _normalize(str(row.get("category") or row.get("categories") or ""))
        blob = _lower(" ".join([title, abstract, category]))

        scores: dict[str, int] = {}
        hits: list[str] = []
        for name, spec in PERSPECTIVES.items():
            matched = [kw for kw in spec["keywords"] if kw in blob]
            scores[name] = len(matched)
            hits.extend(matched)

        keywords = self._keywords_from_text(title, abstract, category, hits)
        ranked = sorted(scores, key=lambda k: scores[k], reverse=True)
        perspectives = [name for name in ranked if scores[name] > 0][:MAX_LAKES_PER_PAPER]
        if category and not perspectives:
            cat_l = category.lower()
            if "chem-ph" in cat_l or "atm-clus" in cat_l:
                perspectives.append("electronic_structure")
            elif "mtrl" in cat_l or "cond-mat" in cat_l:
                perspectives.append("materials_solids")
            elif "q-bio" in cat_l:
                perspectives.append("biomolecular_modeling")
            elif "cs." in cat_l or "stat.ml" in cat_l:
                perspectives.append("ml_datasets_benchmarks")

        extract_worth = bool(perspectives) and perspectives != ["numerical_methods"]

        meta = dict(row)
        meta.update(
            {
                "title": title,
                "abstract": abstract,
                "category": category,
                "keywords": keywords,
                "perspective_scores": scores,
                "perspectives": perspectives,
                "extract_worth": extract_worth,
                "tag_source": "rules",
            }
        )

        if (
            self.use_cheap_llm_for_tags
            and self.cheap_llm is not None
            and not perspectives
            and (title or abstract)
        ):
            meta.update(self._llm_tags(title, abstract, category))
            meta["tag_source"] = "cheap_llm"
        return meta

    def should_extract(
        self,
        metadata: dict[str, Any],
        perspectives: list[str] | None = None,
        min_score: int = 1,
    ) -> bool:
        """Return False to skip the expensive full-text LLM call."""
        if metadata.get("extract_worth") is False:
            return False
        wanted = set(perspectives or ALLOWED_TOPICS)
        paper_ps = set(metadata.get("perspectives") or [])
        if paper_ps and wanted.isdisjoint(paper_ps):
            return False
        scores = metadata.get("perspective_scores") or {}
        if wanted and scores:
            return any(scores.get(p, 0) >= min_score for p in wanted) or bool(
                paper_ps & wanted
            )
        return bool(metadata.get("abstract") or metadata.get("title"))

    def _keywords_from_text(
        self, title: str, abstract: str, category: str, hits: list[str]
    ) -> list[str]:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-+]{3,}", f"{title} {abstract} {category}")
        stop = {
            "this", "that", "with", "from", "using", "were", "been", "have",
            "which", "their", "into", "also", "than", "such", "these", "those",
            "based", "study", "paper", "results", "shown", "using", "method",
        }
        counts: dict[str, int] = {}
        for tok in tokens:
            key = tok.lower()
            if key in stop:
                continue
            counts[key] = counts.get(key, 0) + 1
        ranked = sorted(counts, key=lambda k: (-counts[k], k))
        merged: list[str] = []
        for item in list(dict.fromkeys(hits)) + ranked:
            if item not in merged:
                merged.append(item)
            if len(merged) >= 12:
                break
        return merged

    def _llm_tags(self, title: str, abstract: str, category: str) -> dict[str, Any]:
        prompt = self.tag_prompt.format(
            taxonomy=self._taxonomy_block(),
            title=title[:500],
            abstract=abstract[:4000],
            category=category[:200],
        )
        raw = self._invoke_text(self.cheap_llm, prompt)
        parsed = self._parse_json(raw) or {}
        keywords = parsed.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        topics = []
        for item in parsed.get("lakes") or parsed.get("topics") or parsed.get("perspectives") or []:
            tid = item.get("id") if isinstance(item, dict) else item
            if tid in ALLOWED_TOPICS and tid not in topics:
                topics.append(tid)
        return {
            "keywords": keywords[:12],
            "perspectives": topics[:MAX_LAKES_PER_PAPER],
            "topics": parsed.get("lakes") or parsed.get("topics") or [
                {"id": t, "confidence": 0.5} for t in topics[:MAX_LAKES_PER_PAPER]
            ],
            "extract_worth": bool(parsed.get("extract_worth", True)),
            "tag_reason": parsed.get("reason", ""),
        }

    # ------------------------------------------------------------------
    # Text reduction: keep abstract + methods-like windows only
    # ------------------------------------------------------------------

    def select_source_text(self, paper_text: str, metadata: dict[str, Any] | None = None) -> str:
        """Prefer methods / computational-details windows over the full PDF."""
        text = paper_text or ""
        parts: list[str] = []
        if metadata:
            if metadata.get("title"):
                parts.append(f"TITLE: {metadata['title']}")
            if metadata.get("abstract"):
                parts.append(f"ABSTRACT: {metadata['abstract']}")
            if metadata.get("keywords"):
                parts.append("KEYWORDS: " + ", ".join(metadata["keywords"]))

        windows = self._section_windows(text)
        if not windows:
            windows = [text[: self.max_extract_chars]]
        budget = self.max_extract_chars
        for window in windows:
            if budget <= 0:
                break
            parts.append(window[:budget])
            budget -= len(window[:budget])
        return "\n\n".join(parts)[: self.max_extract_chars]

    def _section_windows(self, text: str) -> list[str]:
        if not text:
            return []
        lines = text.splitlines()
        starts: list[int] = []
        acc = 0
        line_offsets = []
        for line in lines:
            line_offsets.append(acc)
            acc += len(line) + 1
        joined_starts = []
        for i, line in enumerate(lines):
            if SECTION_HINTS["methods"].search(line) or SECTION_HINTS["data"].search(line):
                joined_starts.append(line_offsets[i])
        if not joined_starts:
            return []
        windows = []
        span = max(self.chunk_size * 3, 6000)
        for start in joined_starts:
            windows.append(text[start : start + span])
        return windows[:3]

    # ------------------------------------------------------------------
    # LLM extraction (1 call in the common path)
    # ------------------------------------------------------------------

    def process_paper(
        self,
        paper_text: str,
        metadata: dict[str, Any] | None = None,
        perspectives: list[str] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        metadata = metadata or self.enrich_metadata({"abstract": paper_text[:2000]})
        focus = perspectives or metadata.get("perspectives") or list(ALLOWED_TOPICS)
        source = self.select_source_text(paper_text, metadata)

        if len(source) <= self.chunk_size * 2:
            raw = self._extract_once(source, metadata, focus)
            return self._ensure_schema(self._parse_json(raw))

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_text(source)[:4]
        chunk_results = [self._extract_once(chunk, metadata, focus) for chunk in chunks]
        if len(chunk_results) == 1:
            return self._ensure_schema(self._parse_json(chunk_results[0]))
        return self._consolidate_tasks(chunk_results)

    def _extract_once(
        self, source_text: str, metadata: dict[str, Any], perspectives: list[str]
    ) -> str:
        prompt = self.extraction_prompt.format(
            taxonomy=self._taxonomy_block(),
            perspectives=", ".join(perspectives),
            title=metadata.get("title", ""),
            keywords=", ".join(metadata.get("keywords") or []),
            source_text=source_text,
        )
        return self._invoke_text(self.llm, prompt)

    def _process_chunk(self, chunk_text: str) -> str:
        return self._extract_once(chunk_text, {}, list(ALLOWED_TOPICS)[:3])

    def _consolidate_tasks(self, chunk_results: list[str]) -> dict[str, list[dict[str, Any]]]:
        all_tasks = "\n\n===== CHUNK SEPARATOR =====\n\n".join(chunk_results)
        prompt = self.consolidation_prompt.format(
            allowed=", ".join(ALLOWED_TOPICS),
            task_lists=all_tasks[:60000],
        )
        response = self._invoke_text(self.llm, prompt)
        return self._ensure_schema(self._parse_json(response))

    def go(
        self,
        paper_text: str,
        metadata: dict[str, Any] | None = None,
        perspectives: list[str] | None = None,
        skip_if_unmatched: bool = True,
    ):
        self.log = []
        meta = metadata or self.enrich_metadata({"abstract": (paper_text or "")[:3000]})
        self.log.append(("user", f"perspectives={meta.get('perspectives')} keywords={meta.get('keywords')}"))

        if skip_if_unmatched and not self.should_extract(meta, perspectives=perspectives):
            empty = {"lakes": [], "tasks": [], "databases": [], "software": [], "skipped": True, "metadata": meta}
            self.log.append(("assistant", "skipped_by_metadata_gate"))
            return self.log, empty

        results = self.process_paper(paper_text, metadata=meta, perspectives=perspectives)
        results["metadata"] = {
            "doi": meta.get("doi"),
            "title": meta.get("title"),
            "keywords": meta.get("keywords"),
            "perspectives": meta.get("perspectives"),
            "tag_source": meta.get("tag_source"),
        }
        self.log.append(("assistant", json.dumps(results, indent=2)[:8000]))
        return self.log, results

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _invoke_text(self, model, prompt: str) -> str:
        message = model.invoke(prompt)
        content = getattr(message, "content", message)
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                return first.get("text") or json.dumps(first)
            return getattr(first, "text", str(first))
        return str(content)

    def _parse_json(self, text: str | None) -> dict[str, Any] | None:
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    return None
            brace = re.search(r"\{[\s\S]*\}", text)
            if brace:
                try:
                    return json.loads(brace.group(0))
                except json.JSONDecodeError:
                    return None
        return None

    def _taxonomy_block(self) -> str:
        return "\n".join(
            f"- {tid}: {spec['description']}" for tid, spec in TOPIC_TAXONOMY.items()
        )

    def _ensure_schema(self, result: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
        if not isinstance(result, dict):
            return {"lakes": [], "topics": [], "tasks": [], "databases": [], "software": []}
        raw_lakes = result.get("lakes") or result.get("topics") or []
        lakes: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw_lakes:
            if isinstance(item, str):
                lake_id = item
                item = {}
            else:
                lake_id = str(item.get("lake_id") or item.get("id") or item.get("task_name") or "")
            if lake_id not in ALLOWED_TOPICS or lake_id in seen:
                continue
            seen.add(lake_id)
            lakes.append(
                {
                    "lake_id": lake_id,
                    "confidence": item.get("confidence", ""),
                    "related_reason": item.get("related_reason") or item.get("rationale") or "",
                    "ground_truth": item.get("ground_truth") or item.get("description") or item.get("example") or "",
                    "systems": item.get("systems", ""),
                    "methods": item.get("methods", ""),
                    "software": item.get("software", ""),
                    "databases": item.get("databases", ""),
                }
            )
        result["lakes"] = lakes[:MAX_LAKES_PER_PAPER]
        result["topics"] = result["lakes"]
        result["tasks"] = [
            {"task_name": lake["lake_id"], "description": lake["related_reason"], "example": lake["ground_truth"]}
            for lake in result["lakes"]
        ]
        result.setdefault("databases", [])
        result.setdefault("software", [])
        return result

    def save_results(self, results: dict[str, list[dict[str, Any]]], output_path: str):
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {output_path}")

    def result_formatting(self, output_class, task_intention):
        format_check_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are evaluateGPT, tasked with extract and parse the task output based on the history of an agent. "
                        "Review the entire history of messages provided. "
                        "Here is the task output requirement: \n"
                        f"'{task_intention.replace('{', '{{').replace('}', '}}')}'.\n"
                    ),
                ),
                ("placeholder", "{messages}"),
            ]
        )
        checker_llm = format_check_prompt | self.llm.with_structured_output(output_class)
        result = checker_llm.invoke({"messages": [("user", str(self.log))]}).dict()
        return result


def enrich_metadata_csv(input_csv: str, output_csv: str) -> str:
    """Batch-tag a ChemRxiv metadata CSV with keywords/perspectives. No LLM."""
    import pandas as pd

    extractor = PaperTaskExtractor.__new__(PaperTaskExtractor)
    extractor.use_cheap_llm_for_tags = False
    extractor.cheap_llm = None

    df = pd.read_csv(input_csv)
    rows = []
    for rec in df.to_dict(orient="records"):
        tagged = PaperTaskExtractor.enrich_metadata(extractor, rec)
        rec = dict(rec)
        rec["keywords"] = "|".join(tagged.get("keywords") or [])
        rec["perspectives"] = "|".join(tagged.get("perspectives") or [])
        rec["extract_worth"] = tagged.get("extract_worth")
        rec["perspective_scores"] = json.dumps(tagged.get("perspective_scores") or {})
        rows.append(rec)
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    out.to_csv(output_csv, index=False)
    return output_csv