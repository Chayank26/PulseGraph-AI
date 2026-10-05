# Phase 9A — bounded, traceable passage retrieval

The live evidence node now searches `src/data/evidence.json` using deterministic
case-folded candidate-name token overlap with curated topic terms. It ranks by
overlap count, breaks ties by document ID, and returns at most three passages per
candidate. This is a small local retrieval baseline, not vector search, live PubMed
search, claim entailment, or diagnostic validation.

Two short excerpts were checked against official source records on October 5,
2026: NICE NG158 recommendation 1.1.17 and the AHA 2021 chest-pain summary. URLs,
source labels, verification dates, excerpts and topic terms are committed together.
The AHA document is an official summary, not a full guideline. Whitespace in the
NICE excerpt is normalized. No source is treated as clinical approval of PulseGraph.

Each result records candidate association, document ID, source version, verification
date, retrieval time and passage SHA-256. Audit and presentation metadata record
the corpus version/hash, retrieval method and every candidate's outcome. Historical
results retain their exact excerpts and provenance when the collection changes.
Hashing provides content identity, not proof of authenticity or clinical correctness.

Statuses distinguish related context, insufficient support, no candidates, and
an unavailable collection. Missing files, invalid schemas and duplicate IDs fail
closed. Matching documents outside their verification/review interval are excluded.
The initial 90-day review interval is an engineering maintenance policy, not a
claim that documents remain medically current for that period. A stale item is
not automatically superseded; nothing is fetched at runtime. Retrieval remains
functional without network access and sends no patient data externally.

Related passages always have RELATED_CONTEXT_ONLY status. Direct/partial support
and conflicting-evidence classifications are deliberately not inferred. Even if
one candidate has a match, the per-candidate record preserves unsupported others.
No match does not mean that no relevant medical literature exists. No candidate
means no query was attempted. An expired/invalid collection does not block clinical
review, but its limitations remain visible; approval is still clinician review,
not automated evidence validation.

Diagnostic invalidation clears evidence and marks its review stale. Generated
evidence metadata is excluded from the clinical-input fingerprint, preserving
approval compatibility. New optional schema fields allow old stored results to
load as UNASSESSED. Previously saved demonstration citations are not rewritten.

Validation: 316 selected tests passed and frontend production build passed.
Tests cover provenance, invalid/missing collections, duplicate IDs, no candidates,
unmatched candidates, mixed coverage, review dates, invalidation, API persistence
and approval. Browser interaction and clinical retrieval quality were not evaluated.

Next Phase 9B: controlled source ingestion/update tooling, provenance checks and
reviewable diffs; expand the collection under source/licensing constraints; define
claim-support review contracts and independently annotated retrieval evaluation.
Model-based support checking must not equate topical similarity with entailment.
