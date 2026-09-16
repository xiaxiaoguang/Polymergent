# Polymer know-how sources (downloadable)

License note: Wikipedia/Wikibooks/Wikimedia text is CC BY-SA. Cite and keep attribution.
Do not scrape paywalled textbooks into the agent corpus.

## A. Wikipedia pages that map onto current tools

Fetch as plain text (already started under `knowhow_wiki/`):

```
https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&redirects=1&titles=TITLE
```

Or one-article PDF:

```
https://en.wikipedia.org/api/rest_v1/page/pdf/Carothers_equation
```

| Page | URL | Tools it supports |
|---|---|---|
| Polymer | https://en.wikipedia.org/wiki/Polymer | overview |
| Polymer chemistry | https://en.wikipedia.org/wiki/Polymer_chemistry | overview |
| Polymer science | https://en.wikipedia.org/wiki/Polymer_science | overview |
| Polymerization | https://en.wikipedia.org/wiki/Polymerization | synthesis |
| Step-growth polymerization | https://en.wikipedia.org/wiki/Step-growth_polymerization | Carothers, PDI, gel |
| Chain-growth polymerization | https://en.wikipedia.org/wiki/Chain-growth_polymerization | FRP rate, Mayo CTA |
| Free-radical polymerization | https://en.wikipedia.org/wiki/Free-radical_polymerization | `free_radical_steady_state_rp` |
| Ring-opening polymerization | https://en.wikipedia.org/wiki/Ring-opening_polymerization | lactone openers |
| Carothers equation | https://en.wikipedia.org/wiki/Carothers_equation | `carothers_*` |
| Glass transition | https://en.wikipedia.org/wiki/Glass_transition | Tg tools |
| Flory–Fox equation | https://en.wikipedia.org/wiki/Flory%E2%80%93Fox_equation | Fox + Flory–Fox |
| Williams–Landel–Ferry equation | https://en.wikipedia.org/wiki/Williams%E2%80%93Landel%E2%80%93Ferry_equation | `wlf_shift_factor` |
| Mark–Houwink equation | https://en.wikipedia.org/wiki/Mark%E2%80%93Houwink_equation | MH tools |
| Mayo–Lewis equation | https://en.wikipedia.org/wiki/Mayo%E2%80%93Lewis_equation | copolymer tools |
| Molar mass distribution | https://en.wikipedia.org/wiki/Molar_mass_distribution | histogram averages |
| Flory–Huggins solution theory | https://en.wikipedia.org/wiki/Flory%E2%80%93Huggins_solution_theory | mixing ΔG |
| Gelation | https://en.wikipedia.org/wiki/Gelation | Flory–Stockmayer |
| Copolymer | https://en.wikipedia.org/wiki/Copolymer | Mayo–Lewis |
| Ceiling temperature | https://en.wikipedia.org/wiki/Ceiling_temperature | `ceiling_temperature_k` |
| Polyester | https://en.wikipedia.org/wiki/Polyester | ROP / step-growth |
| SMILES | https://en.wikipedia.org/wiki/Simplified_molecular-input_line-entry_system | conventions tools |
| Simplified molecular-input line-entry system | same | conventions |

Also useful: Condensation polymer, Addition polymer, Dispersity, Intrinsic viscosity, Reactivity ratio.

## B. Bulk Wikipedia (actually downloadable)

1. Per-article text: MediaWiki API (used above). Rate-limit; set a real User-Agent; sleep 1s.
2. Per-article PDF: `https://en.wikipedia.org/api/rest_v1/page/pdf/{Title_with_underscores}`
3. Offline snapshot (best for a local know-how box):
   - Kiwix library: https://library.kiwix.org
   - English Wikipedia no pictures is the practical size class (`wikipedia_en_all_nopic` ~ tens of GB; `wikipedia_en_top` is smaller).
   - Reader: https://www.kiwix.org
4. Full XML dumps (huge): https://dumps.wikimedia.org/enwiki/
   Prefer `pages-articles-multistream.xml.bz2` + index. See https://en.wikipedia.org/wiki/Wikipedia:Database_download
5. Wikimedia Commons polymer diagrams: https://commons.wikimedia.org/wiki/Category:Polymer_chemistry

Starter extracts already saved:
`/home/workdir/artifacts/knowhow_wiki/` (Polymer, Polymer chemistry, Polymer science, Polymerization). Remaining titles hit HTTP 429; retry with delay.

## C. Wikibooks (CC BY-SA, downloadable)

- Soft-matter / polymer intro: https://en.wikibooks.org/wiki/Introduction_to_Biological_Systems_and_Soft_Condensed_Matter
- Materials Science: https://en.wikibooks.org/wiki/Introduction_to_Materials_Science
- Print/PDF via: `https://en.wikibooks.org/api/rest_v1/page/pdf/{Title}`

## D. Open course PDFs (check license page before ingesting)

These are public course notes, not Wikipedia, but they fill the “textbook” gap:

- YCMOU M.Sc. Polymer Chemistry SLM (ISBN 978-81-19453-09-2):  
  https://ycmou.ac.in/wp-content/uploads/custom-assets/ebooks/CHE507%20Polymer%20Chemistry.pdf
- FHSST Chemistry ch.10 Organic Macromolecules (GFDL):  
  http://cdimage.debian.org/mirror/gnu.org/savannah/fhsst/Chemistry_Matter_and_Materials_Ch10_Organic_Macromolecules.pdf

Internet Archive listings for Seymour/Stevens *Polymer Chemistry* exist but are **access-restricted** — do not use those files as a free corpus.

## E. Suggested ingest order for the agent

1. Wikipedia extracts for every equation tool (Carothers, Fox, Mayo–Lewis, MH, WLF, Flory–Huggins, gelation).
2. ROP + polyester + SMILES pages for the convention tools.
3. One open textbook PDF (YCMOU or FHSST) as narrative tutorial.
4. Optional later: Kiwix `wikipedia_en_top_nopic` ZIM if you want offline search.

Keep each article as `{title}.txt` with the first line `# Title` so a retriever can chunk by heading.
