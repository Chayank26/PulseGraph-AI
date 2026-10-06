# Consolidated review and versioned approval — Phase 15

GET `/api/clinical/sessions/{id}/review` now reads a single graph checkpoint and
returns the clinical package plus an opaque `review_version`, `can_approve` and
`at_review_checkpoint`. The version hashes the session identity, checkpoint config
and displayed clinical payload. It changes when an evidence judgment or workflow
update creates a new checkpoint, even if diagnostic input fingerprints are unchanged.
Only the session owner may retrieve this package or approve, reject or reassess it.

Approval must submit the loaded version:

```json
{"review_version":"<64-character version from GET review>","notes":"Clinician notes"}
```

Missing or mismatched versions return HTTP 409 without approving. Existing human
review checkpoint and diagnostic freshness checks still apply. Approval records the
version, authenticated doctor ID and server timestamp in checkpoint state, persisted
result approval JSON and an audit event. Invalidation clears the current approval
record. This is an authenticated software record, not a cryptographic signature.

The workspace loads and displays the actual versioned package instead of combining
independently polled summaries. It includes all scores and differential proposals,
urgency, presentation/handoff information, imaging, evidence judgments, medication
coverage, symbolic limitations and recorded approval. There is no prechecked review
acknowledgement. A failed action clears the displayed package and requires reload;
approval never silently fetches a newer version on the clinician's behalf. Session
changes cancel stale reads. Missing lists are not described as negative findings.

The export node remains a stub. Its audit metadata now says NOT_IMPLEMENTED, and
approval wording does not claim external EHR delivery. The historical `ehr_exported`
step identifier is retained for compatibility. The review page no longer opens the
simulated export modal. No database migration is required.

Verification: 440 selected regression tests and frontend build passed. Tests cover
missing versions, changed evidence, reassessment, owner access, persisted approval
identity/version and repeated approval rejection. Older infrastructure test callers
were migrated to submit a loaded version but were not run as part of this focused
suite. No browser usability or independent clinical evaluation was performed.

## Remaining Phase 16 work

The check is optimistic, not a database/checkpoint atomic compare-and-swap. Concurrent
process mutations between validation and checkpoint update remain an unresolved
race requiring shared transaction/serialization design and recovery tests. This
phase does not claim exactly-once approval or delivery. Audit synchronization can
still duplicate rows. Independent review annotations, human factors and real
PostgreSQL crash/concurrency experiments remain outstanding.

Phase 16B1 update: application service operations now share a per-session PostgreSQL
advisory lock, including evidence updates and approval version validation. This closes
ordinary interleaving through those methods while the lock connection remains alive.
It does not make application/checkpoint commits atomic or fence a worker whose lock
connection is lost. See `../evaluation/session-serialization.md` for verified scope.
