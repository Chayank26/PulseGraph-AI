# Phase 16B2: stable-checkpoint projection recovery

Application request/result/audit records are projections of the graph checkpoint.
Response handling now writes the updated checkpoint before marking the database
request resolved. A failed checkpoint write therefore leaves the database response
pending. Synchronization writes the checkpoint's actual request status, answer and
original timestamps, including resolved requests; it no longer recreates them as
new pending requests.

Audit synchronization assigns a deterministic checkpoint_event_id using the event
position and serialized event. Repeated synchronization checks that identity within
the session before inserting. This is idempotent under the session-operation lock,
not a database unique constraint or tamper-evident audit. Historical duplicate rows
are retained, not destructively rewritten. Original checkpoint event times are used.

## Recovery API

POST `/api/clinical/sessions/{session_id}/recover` requires the session owner and
acquires the existing per-session lock. It accepts no patient answers or approval
instructions. At a stable questionnaire/review interruption or recognized terminal
outcome, it reconciles session status, requests, audit and results from the checkpoint.
It returns PROJECTIONS_RECONCILED and clinical_actions_replayed=false. Repeating the
operation is supported; no model or graph node is invoked.

Missing checkpoints, internal mid-transition nodes, interrupted approval and unknown
terminal outcomes return HTTP 409. The endpoint does not reconstruct graph state from
application records or infer that a stored approval intention completed. This API is
an explicit operator/clinician recovery action, not automatic background recovery.
It currently has no dedicated frontend button. Existing JSON storage is reused.

## Real PostgreSQL experiment

`scripts.evaluate_postgres_recovery` accepts PULSEGRAPH_TEST_DATABASE_URL only for a
PostgreSQL database named pulsegraph_recovery_test. Use an isolated disposable database:
the script creates synthetic tables/records and does not remove them itself.

Three fresh Python processes use PostgresSaver with the same database/thread:

1. Execute until a data-request interruption, then inject failure at the result write
   after earlier projection commits.
2. Reconstruct the service, recover the pending request, verify repeat recovery does
   not duplicate audit rows, resolve applicability and inject failure before final
   projection synchronization.
3. Reconstruct again, reconcile the terminal handoff, verify requests remain resolved
   and repeated recovery does not add audit rows.

All three stages passed on an ephemeral PostgreSQL 16 container. The container was
stopped and removed. The committed postgres-recovery-report.json records backend,
stage exit codes and untested claims. These are controlled exception injections and
fresh-process reconstruction, not abrupt power-loss or mid-transaction crash tests.
No live clinical/model provider was used.

451 selected regression tests passed, followed by six focused recovery tests after
two additional refusal checks. The focused recovery checks include owner access,
checkpoint-write failure, interrupted-approval refusal and stable repeated sync.
No frontend code changed.

## Remaining Phase 16B3 boundaries

Application/checkpoint writes are still not atomic. Internal node interruption needs
an explicit replay/reconciliation protocol and tests before recovery can resume it.
Loss of the advisory-lock connection while a worker continues needs fencing. Direct
writes outside the service lock are not protected; no database uniqueness constraint
prevents duplicate events from such writers. Legacy duplicate audit rows remain.
Approval/evidence races across full independent services, interrupted approval
persistence, process-kill/power-loss tests and independent clinical evaluation remain
outstanding. These limits must not be hidden behind a general 'recovery passed' claim.

Phase 16B3A update: attributable, current interrupted approvals at human_review or
before the export stub can now return to fresh review through explicit owner recovery.
Other mid-transition cases remain refused. See `approval-recovery.md`.
