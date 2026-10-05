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

## Phase 9B1 — controlled update reports and claim-review contract

Run `venv/bin/python -m scripts.review_evidence path/to/proposed.json` to compare
a proposed collection against the active collection. `--current` selects another
baseline. The command is read-only: it prints added/removed/changed records with
full before/after content and both file hashes. Exit 1 indicates invalid input,
stale dates, malformed topics, non-HTTPS sources or changed content without a
version change. Exit 0 means technical validation only. It does not confirm source
identity, passage accuracy, currency, licensing or clinical correctness.

Update procedure: prepare a separate proposed JSON; verify each passage, date,
version and source URL against the original publisher; check permission to include
it; inspect the report; replace the active file through ordinary reviewed source
control. Do not extend review dates without checking the source. No automatic
fetch, overwrite, publication or clinical approval is performed. The active seed
collection remains unchanged in this increment.

`ClaimReview` records an exact claim, document ID, corpus and passage hashes,
reviewer attribution, date, rationale and one of DIRECT_SUPPORT, PARTIAL_SUPPORT,
CONFLICTING or INSUFFICIENT_SUPPORT. Validation rejects changed claims, changed
collections, missing/changed passages and out-of-date reviews. These are recorded
judgments, not computed entailment. Reviewer names are unverified strings in this
offline contract, explicitly reported as unauthenticated. A valid record therefore
cannot upgrade live retrieval output or authorize clinical use. The live workflow
continues to label all matches RELATED_CONTEXT_ONLY.

Tests exercise all four verdicts with synthetic judgments, binding/staleness,
source removal, review-date expiry, version requirements, and CLI no-write/error
behavior. These are contract tests, not an independently annotated support-quality
benchmark. Phase 9B2 remains: authenticated review workflow, controlled ingestion,
expanded source coverage and independent claim-support/retrieval evaluation.

## Phase 9B2 — authenticated session judgments and retrieval benchmark

The evidence page now offers a passage/candidate selector, a judgment with no
preselected answer, and a required rationale. POST and GET
`/api/clinical/sessions/{session_id}/evidence-reviews` require the authenticated
session owner. The server supplies reviewer identity and timestamp; request bodies
cannot supply them. Submission is allowed only at the human-review checkpoint.
Missing sessions return 404, ownership failures 403, malformed payloads 422, and
stale/unavailable sources or wrong workflow checkpoints 409.

Each judgment binds the candidate ID/text, document ID, corpus/passage hashes and
diagnostic input fingerprint. The service checks those bindings against current
graph state and the active local collection, including source review dates. A
judgment is a clinician's recorded opinion, not a model verification or clinical
session approval. Automated evidence items remain RELATED_CONTEXT_ONLY.

Judgments are stored under presentation.evidence_review.clinician_reviews in the
existing JSON result field and checkpoint, with corresponding audit entries.
Revisions append records; the dedicated GET endpoint returns CURRENT, SUPERSEDED
or STALE after checking bindings against the current state/source. Do not treat
raw records from the general results endpoint as a freshness decision. Missing
checkpoints or sources are reported as stale. Reevaluation clears current judgments
with other derived results; prior records remain in the audit history. Old stored
sessions require no schema migration. New reviews cannot be added after approval.

Run `venv/bin/python -m scripts.evaluate_evidence` for a reproducible ten-case
synthetic retrieval regression report, including corpus and fixture hashes. The
committed report is docs/evaluation/evidence-report.json. Cases cover two topics,
case folding, unsupported topics, source-date boundaries, and documented synonym
and negation limitations. Matching the expected failure-to-recognize a synonym is
a software contract pass, not clinical success. No independent clinician-annotated
support benchmark or sensitivity/specificity estimate is claimed.

Verification: 330 focused tests passed, including owner enforcement, identity
spoof rejection, wrong checkpoint, malformed rationale/verdict, stale claims and
hashes, missing/changed collections, revision history, reevaluation, persistence,
and compatibility with approval. Frontend production build passed. Browser
interaction, production authentication infrastructure, PostgreSQL recovery and
concurrent submissions were not exercised. Existing checkpoint/database writes
remain separate transactions; this change does not add cross-store atomicity or
idempotent submission. Concurrent writers require the later infrastructure phase.

The local two-source collection is unchanged. The update-report workflow is still
manual, with no automated source fetch or content expansion. Qualified clinical
annotation and source review remain external prerequisites. Next engineering phase
is Phase 10: bounded differential-agent contracts and grounded generation, with
provider/data-handling choices made before using external model services.
