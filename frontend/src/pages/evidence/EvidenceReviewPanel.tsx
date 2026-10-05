import { useEffect, useState } from 'react';
import { apiClient } from '../../api/client';
import type { ClinicalEvidence } from '../../types/clinical';

type Review = { review_id: string; claim: string; document_id: string; verdict: string; rationale: string;
  reviewer: string; recorded_at: string; status: string; stale_reason?: string };

export function EvidenceReviewPanel({ sessionId, evidence, corpusHash, fingerprint, canReview }: {
  sessionId: string; evidence: ClinicalEvidence[]; corpusHash?: string; fingerprint?: string; canReview: boolean;
}) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [selected, setSelected] = useState('');
  const [verdict, setVerdict] = useState('');
  const [rationale, setRationale] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const endpoint = `/clinical/sessions/${sessionId}/evidence-reviews`;
  useEffect(() => {
    let active = true;
    apiClient.get<Review[]>(endpoint).then(r => { if (active) setReviews(r.data); })
      .catch(() => { if (active) setError('Evidence reviews could not be loaded.'); });
    return () => { active = false; };
  }, [endpoint]);
  async function refresh() {
    const response = await apiClient.get<Review[]>(endpoint);
    setReviews(response.data);
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const item = evidence[Number(selected)];
    if (selected === '' || !item || !verdict || !rationale.trim()) return;
    setBusy(true); setError('');
    try {
      await apiClient.post(endpoint, { claim_id: item.claim_id, claim: item.claim,
        document_id: item.document_id, passage_sha256: item.content_sha256,
        corpus_sha256: corpusHash, diagnostic_fingerprint: fingerprint, verdict, rationale });
      await refresh(); setRationale(''); setVerdict('');
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      setError(typeof message === 'string' ? message : 'Review could not be saved. Refresh the session and try again.');
    } finally { setBusy(false); }
  }
  return <section className="border rounded-xl p-4 space-y-3 text-sm">
    <h2 className="font-bold">Clinician evidence judgment</h2>
    <p>Judge only whether the selected passage supports the displayed candidate claim. This records your judgment; it does not change retrieval status or approve the clinical session.</p>
    <form onSubmit={submit} className="space-y-3">
      <label className="block">Candidate and passage
        <select required value={selected} onChange={e => setSelected(e.target.value)} className="block w-full border p-2">
          <option value="">Select a retrieved passage</option>
          {evidence.map((item, index) => <option key={index} value={index}>{item.claim} — {item.title}</option>)}
        </select>
      </label>
      {selected !== '' && evidence[Number(selected)] && <blockquote className="border-l-2 pl-3">{evidence[Number(selected)].snippet}</blockquote>}
      <label className="block">Judgment
        <select required value={verdict} onChange={e => setVerdict(e.target.value)} className="block w-full border p-2">
          <option value="">Choose a judgment</option>
          <option value="DIRECT_SUPPORT">Direct support</option><option value="PARTIAL_SUPPORT">Partial support</option>
          <option value="CONFLICTING">Conflicting evidence</option><option value="INSUFFICIENT_SUPPORT">Insufficient support</option>
        </select>
      </label>
      <label className="block">Rationale<textarea required maxLength={4000} value={rationale} onChange={e => setRationale(e.target.value)} className="block w-full border p-2" /></label>
      <button type="submit" disabled={busy || !canReview || !corpusHash || !fingerprint || !evidence.length} className="border rounded p-2 disabled:opacity-50">Save judgment</button>
      {!canReview && <p>Judgments can be recorded only while the session is waiting for clinician review.</p>}
    </form>
    {error && <p role="alert">{error}</p>}
    <button type="button" disabled={busy} onClick={() => { setError(''); refresh().catch(() => setError('Could not refresh review status.')); }} className="underline">Refresh review status</button>
    {reviews.map(review => <article key={review.review_id} className="border-t pt-2">
      <p>{review.claim} — {review.verdict} ({review.status})</p><p>{review.rationale}</p>
      <p>Clinician: {review.reviewer}; recorded: {review.recorded_at}</p>
      {review.stale_reason && <p>{review.stale_reason}</p>}
    </article>)}
  </section>;
}
