# Phase 10 — bounded differential generation

The diagnostic node now consumes a provider-independent JSON proposal contract.
The old two-keyword candidate generator has been removed from production code.
No clinical model was trained, calibrated or independently evaluated in this phase.

## Execution and configuration

Generation defaults to `DIAGNOSTIC_BACKEND=disabled`. In that mode the node returns
no candidates and an explicit ABSTAINED/provider_not_configured result for clinician
review. Existing API-key settings do not implicitly enable generation. Actual .env
configuration was not modified, and no patient data was sent to a model during
implementation. A deployment preference was requested but not supplied.

The supplied adapter targets a locally managed Ollama `/api/chat` endpoint using
non-streaming JSON-schema output. Reference: official Ollama API specification,
https://github.com/ollama/ollama/blob/main/docs/openapi.yaml and structured-output
announcement https://ollama.com/blog/structured-outputs. The adapter supplies
`format`, `stream: false`, separate system/user messages, and output-token limits.

To activate after selecting and independently assessing a locally installed model:

```dotenv
DIAGNOSTIC_BACKEND=ollama
DIAGNOSTIC_ENDPOINT=http://127.0.0.1:11434
DIAGNOSTIC_MODEL=<your-installed-local-model-tag>
DIAGNOSTIC_TIMEOUT_SECONDS=30
MAX_DIAGNOSTIC_CANDIDATES=5
```

Replace the placeholder; this is not a model recommendation. Restart the backend
after configuration. Run the local server separately; the application does not
install, download, start or probe models. Only literal loopback HTTP addresses are
accepted, not arbitrary hosts. Redirects and environment proxies are disabled.
Known cloud-model naming patterns are rejected. Operators must also ensure the
local server itself does not forward requests to a hosted service; a loopback URL
cannot attest to server behavior. Narrative may contain identifiers even though
the structured patient ID and prior review metadata are omitted from the request.

No external-provider adapter or external patient-data transfer is enabled.
`DifferentialProvider.generate(payload, schema)` is the extension point for a
separately configured and tested provider after deployment/data-handling decisions.

## Input and output boundaries

The bounded request includes validated presentation findings with statuses and
source spans, history, allergies, medications, available observations, missing
observation identifiers, calculator context, and imaging status/report. It includes
at most 20 current documents from the existing local evidence collection, each
with its exact version and passage. This is a small evidence-context baseline,
not full medical literature retrieval. Context above 60,000 JSON characters fails
rather than being silently truncated. No valid current documents, no positive
findings, or explicit uncovered presentation produces abstention. Existing urgency,
applicability and handoff routing remains deterministic.

The model may return up to five proposed condition names, positive finding IDs,
absent-finding IDs, missing-observation IDs and document IDs, or abstain with a
bounded reason. It cannot supply probability, workup orders, codes, arbitrary
rationale fields or new observation fields. The validator checks schema, bounds,
uniqueness of candidates/support references, assertion status and reference
membership. The server reconstructs quoted patient evidence, source references
and explanatory text from validated inputs. It never treats missing imaging as
normal imaging. Hypothesis names remain model-generated text.

This checks grounding structure only. It does not prove that a referenced symptom
supports a proposed diagnosis, that an absent symptom contradicts it, that citations
entail it, or that the model selected every relevant missing observation. Findings
and evidence can be clinically irrelevant despite valid IDs. Source snippets remain
context only; clinician evidence judgments stay a separate workflow. Clinical
accuracy and prompt-injection resistance require independent evaluation.

## Failure, audit and review

Provider timeout/error, malformed/oversized output, fabricated IDs, invalid
assertion use or missing/invalid collection produces FAILED with no candidates.
There is no silent keyword fallback. Empty proposals and legitimate abstention
are distinct. Limits include connect/read timeouts, an elapsed-time check between
response chunks, bounded provider response bytes and output JSON size. These are
not a process-level hard deadline. Retry is not automatic.

The result replaces prior differentials; existing reevaluation clears downstream
results and evidence judgments. Provider failures do not leak raw responses or
exception text. Review metadata records generation status/reason, configured model,
backend, prompt version/hash, corpus hash when loaded and response hash when
available. A configured model tag is not a cryptographic model-weight identity;
production reproducibility requires pinning the installed artifact separately.

The diagnostic UI displays generation state, support quotes, absent/conflicting
findings, selected missing observations and source passages. An abstention or failure
continues through the existing clinician-review checkpoint with explicit limitations;
it does not establish a completed clinical diagnosis. A clinician can still review
the available non-diagnostic package. CURRENT identifies input freshness, not
successful generation or clinical validity.

## Verification and remaining work

Tests use an explicit synthetic provider for API workflow fixtures and context tests;
the old symptom mapping survives only in that named test double. Production default
behavior is separately tested to abstain. Tests cover output contract violations,
negated findings, unknown references, duplicate/too-many candidates, absent providers,
provider errors, unsupported presentations, collection failure, context filtering,
transport options, redirects, oversized responses, stale-result replacement and
API persistence. No real model-server inference or browser interaction was run.

Deployment activation and independent clinical/model evaluation remain outstanding.
Phase 11 can add targeted clarification questions on top of the recorded missing
information, with explicit question validation and bounded resumption.

Final verification for this increment: 357 focused tests passed (one existing
Starlette deprecation warning), strict workflow evaluation passed 49/49 and the
frontend production build passed. The workflow evaluation used the production
disabled-provider default; API/context regression tests explicitly inject a
synthetic provider. Neither result measures real model diagnostic performance.
