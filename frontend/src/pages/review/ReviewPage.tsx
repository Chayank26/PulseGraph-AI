import React, { useEffect, useState } from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { clinicalSessionsApi } from '../../api/clinicalSessions';
import { Link } from 'react-router-dom';
import './ReviewPage.css';

type Package = Record<string, unknown> & {session_id: string; review_version: string; can_approve: boolean; at_review_checkpoint: boolean; recovery_required: boolean};
const sections = [
  ['demographics', 'Patient and recorded history'], ['vitals', 'Observations'], ['urgency', 'Urgency assessment'],
  ['presentation', 'Presentation, coverage and limitations'], ['risk_scores', 'All calculated scores'],
  ['differentials', 'All differential proposals'], ['imaging_data', 'Supplied imaging report'],
  ['evidence', 'Evidence and provenance'], ['safety_flags', 'Medication alerts'],
  ['medication_reconciliation', 'Medication history review'], ['symbolic_overrides', 'Symbolic outputs'],
  ['approval', 'Recorded approval'], ['limitations', 'Approval limitations'],
];
function Details({value}: {value: unknown}): React.ReactNode {
  if (value == null) return <p>Not available.</p>;
  if (Array.isArray(value)) return value.length ? <ul className="space-y-3">{value.map((item,i) => <li className="border-l pl-3" key={i}><Details value={item} /></li>)}</ul> : <p>No entries. This does not establish a negative finding.</p>;
  if (typeof value === 'object') return <dl className="space-y-2">{Object.entries(value).filter(([key]) => !['input_fingerprint','assessment_fingerprint','prompt_sha256','response_sha256','corpus_sha256'].includes(key)).map(([key,item]) => <div key={key}><dt className="font-semibold">{key.replaceAll('_',' ')}</dt><dd className="pl-3 break-words"><Details value={item} /></dd></div>)}</dl>;
  return <span>{String(value)}</span>;
}

export const ReviewPage: React.FC = () => {
  const {session, approveSession, rejectSession, reevaluateSession} = useWorkflow();
  const [review,setReview] = useState<Package|null>(null);
  const [notes,setNotes] = useState('');
  const [acknowledged,setAcknowledged] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [reload,setReload] = useState(0);
  const id=session?.session_id;
  useEffect(() => {
    let cancelled=false;
    setReview(null); setAcknowledged(false); setError(''); setNotes('');
    if (id) clinicalSessionsApi.getReviewPackage(id).then(data => {if(!cancelled) setReview(data);})
      .catch(() => {if(!cancelled) setError('Unable to load the review package.');});
    return () => {cancelled=true;};
  },[id,session?.status,reload]);
  if (!session) return <div className="review-card">Select a patient to review. <Link to="/dashboard">Patient directory</Link></div>;
  const current=review?.session_id===id;
  const canAct=current && review?.at_review_checkpoint && !busy;
  async function act(action: 'approve'|'reject'|'reevaluate') {
    if(!review || !current) return;
    setBusy(true);setError('');
    try {
      if(action==='approve') await approveSession(notes,review.review_version);
      else if(action==='reject') await rejectSession(notes);
      else await reevaluateSession(notes);
      setReload(n=>n+1);
    } catch {
      setAcknowledged(false);
      setReview(null);
      setError('The action was not completed. Reload the package and review it again; it may have changed.');
    } finally {setBusy(false);}
  }
  async function recoverApproval() {
    if (!id || !current) return;
    setBusy(true); setError(''); setAcknowledged(false);
    try {
      await clinicalSessionsApi.recoverSession(id);
      setReload(n=>n+1);
    } catch {
      setError('Recovery could not complete. Reload to check the current state; operator assistance may be required.');
      setReview(null);
    } finally {setBusy(false);}
  }
  return <div className="review-shell font-sans">
    <header className="review-banner"><div><h1 className="review-banner-title">Clinician review</h1>
      <p>Review the full assessment and its limitations before recording your decision.</p><p>Session status: {session.status}</p></div></header>
    {error && <p role="alert">{error}</p>}
    <button disabled={busy} onClick={()=>setReload(n=>n+1)} className="underline">Reload review package</button>
    {!current && !error && <p>Loading review package…</p>}
    {current && review && <>
      {review.recovery_required && <section className="review-card" role="alert">
        <h2 className="font-bold">Approval was interrupted</h2>
        <p>Return this session to review. The previous approval intent stays in the audit history; you must review and approve a new version.</p>
        <button disabled={busy} className="border rounded p-3" onClick={recoverApproval}>Return to fresh review</button>
      </section>}
      <p className="text-sm">Review version: {review.review_version.slice(0,12)}. Approval is tied to this loaded package.</p>
      <div className="review-grid">{sections.map(([key,title]) => <section className="review-card text-sm" key={key}>
        <h2 className="font-bold text-lg">{title}</h2><Details value={review[key]} />
      </section>)}</div>
      <section className="review-card space-y-3">
        <h2 className="font-bold">Clinician decision</h2>
        <p>Approval records your review. It does not certify clinical validity or deliver records to an external EHR.</p>
        {!review.can_approve && <p>This assessment is not currently eligible for approval. Complete pending requests or resolve stale assessment inputs.</p>}
        <label>Review notes or reassessment instructions<textarea className="block w-full border p-3" value={notes} onChange={e=>setNotes(e.target.value)} /></label>
        <label className="block"><input type="checkbox" checked={acknowledged} onChange={e=>setAcknowledged(e.target.checked)} /> I reviewed this package, including incomplete assessments and coverage limitations.</label>
        <div className="flex gap-4 flex-wrap">
          <button disabled={!canAct || !review.can_approve || !acknowledged} onClick={()=>act('approve')} className="border rounded p-3 disabled:opacity-40">Record approval</button>
          <button disabled={!canAct || !notes.trim()} onClick={()=>act('reevaluate')} className="border rounded p-3 disabled:opacity-40">Request reassessment</button>
          <button disabled={!canAct} onClick={()=>act('reject')} className="border rounded p-3 disabled:opacity-40">Reject and take over</button>
        </div>
      </section>
    </>}
  </div>;
};
