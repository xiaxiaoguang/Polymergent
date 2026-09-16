# Polymer know-how pack

Markdown here is loaded by `loader.py` (KnowHowLoader).

Skipped filenames: README.md, QUICK_START.md, and ALL-CAPS stems.

## Files

| File | Role |
|---|---|
| loader.py | KnowHowLoader |
| wiki_to_knowhow.py | Wikipedia extract → this markdown layout |
| carothers_equation.md | step-growth DP |
| glass_transition_fox_wlf.md | Fox / Flory–Fox / WLF |
| mayo_lewis_copolymerization.md | F1, azeotrope, CTA |
| rop_smiles_conventions.md | dummy SMILES + lactone opening |
| mark_houwink_mwd.md | [η], Mn/Mw/Mz |

## Generate more from Wikipedia

```bash
python wiki_to_knowhow.py --out . --sleep 1.2
# or from cached extracts
python wiki_to_knowhow.py --from-txt-dir ../knowhow_wiki --titles Polymer Polymerization
```

Set `OPENAI_API_KEY` to let the script rewrite passages with an LLM. Without a key it splits the extract into short passages and wraps Metadata/Overview.

## Agent use

Retrieve summaries first (`get_document_summaries`), then one document body. Do not paste full know-how into every tool call.
