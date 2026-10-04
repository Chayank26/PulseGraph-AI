# PulseGraph research manuscript

`pulsegraph_paper.tex` is a standalone IEEE conference-style LaTeX manuscript
with 30 numbered references, cited in order of first appearance. The bibliography
is embedded; no `.bib` file, external figures, or application source files are
needed to compile it. The compiled `pulsegraph_paper.pdf` has **14 pages**,
verified with PDFKit on October 5, 2026. The architecture diagram appears on
page 6 and is embedded as editable TikZ source.

## Contents

Abstract; introduction; problem statement and requirements; literature review;
methodology; state representation; extraction, urgency, and routing methods;
system architecture with an embedded TikZ diagram; data contracts and failure
handling; software evaluation and results; illustrative workflow traces; discussion; limitations;
future evaluation plan and detailed prospective protocol; ethics and reproducibility; conclusion; reproduction
appendix; IEEE-style references.

The manuscript describes repository revision `266499b`, inspected on October 4,
2026, after triage Phase 4. It distinguishes implemented functionality,
demonstration nodes, and proposed extensions. Its 121 passing tests are software
verification evidence, not a clinical cohort or diagnostic accuracy result.

## Compile

Upload `pulsegraph_paper.tex` to an Overleaf project, select it as the main
document, and use pdfLaTeX. Alternatively, with a TeX distribution containing
IEEEtran and the packages declared in the file, run from this directory:

```sh
pdflatex -interaction=nonstopmode -halt-on-error pulsegraph_paper.tex
pdflatex -interaction=nonstopmode -halt-on-error pulsegraph_paper.tex
```

Two passes resolve citations and table cross-references. BibTeX is not needed.
The manuscript uses `IEEEtran`, `fontenc`, `inputenc`, `cite`, `amsmath`,
`amssymb`, `booktabs`, `array`, `tabularx`, `xurl`, `hyperref`, `listings`, and `tikz`.
The TikZ libraries are `arrows.meta`, `positioning`, `fit`, and `backgrounds`.

The PDF was compiled with Tectonic 0.17.0 after downloading a temporary compiler.
Citation keys, first-citation order, environment nesting, and brace balance were
checked. The PDF contains 14 nonempty pages; the architecture figure was rendered
and visually inspected. The final build has no overfull-box or unresolved-citation
warnings. Minor underfull spacing warnings and startup font-substitution warnings
remain. A pdfLaTeX build may paginate slightly differently from Tectonic.

With Tectonic installed, the equivalent build command is:

```sh
tectonic --keep-logs pulsegraph_paper.tex
```

## Before submission

Replace the author/affiliation/email placeholders. Complete and verify funding,
conflicts, contributions, and any venue-required AI-assistance declaration.
Check the target venue's length and formatting requirements. Have clinical
coauthors review the clinical descriptions and implementation limitations.
The manuscript does not invent institutional approval or patient experiments.

See `verification.txt` for the test command, observed result, and selected
environment versions. External sources are linked directly in the bibliography.

## Implementation evidence map

| Manuscript topic | Main repository evidence |
| --- | --- |
| State and validation | `src/core/state.py`, `src/core/clinical_parsing.py` |
| Contextual symptom extraction | `src/core/presentation.py`, `tests/test_presentation.py` |
| Limited urgency screen | `src/core/urgency.py`, `src/agents/urgency.py`, `tests/test_urgency.py` |
| Applicability and handoff | `src/core/routing.py`, `src/agents/triage.py`, `tests/test_routing.py` |
| Request resolution | `src/core/data_requests.py`, `src/services/clinical_workflow.py` |
| Execution and persistence | `src/core/graph.py`, `src/core/checkpointer.py`, `src/db/models.py` |
| Imaging demonstration | `src/agents/imaging.py` |
| Keyword differential generation | `src/agents/diagnostic.py` |
| Fixed citation selection | `src/agents/evidence_rag.py` |
| Pharmacology and legacy rule limitations | `src/tools/pharmacology.py`, `src/core/symbolic_rules.py` |
| Planned optional imaging | `docs/triage-roadmap.md` |

All paths in this table are relative to the repository root. Application code
was not changed while preparing this manuscript.
