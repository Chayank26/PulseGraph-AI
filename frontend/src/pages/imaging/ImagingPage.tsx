import { Link } from 'react-router-dom';
import { useWorkflow } from '../../context/WorkflowContext';
import './ImagingPage.css';

export const ImagingPage = () => {
  const { session, activePatient } = useWorkflow();
  if (!activePatient || !session) return (
    <section className="bg-white rounded-xl p-8">
      <h1 className="text-xl font-bold">Select a patient to review imaging</h1>
      <Link to="/dashboard" className="underline">Patient directory</Link>
    </section>
  );
  const plan = session.state.presentation?.imaging_plan;
  const labels = {
    NEEDS_DECISION: 'Clinician decision needed', WAITING_FOR_REPORT: 'Waiting for the requested report',
    REPORT_PROVIDED: 'Report provided', SKIPPED: 'Continuing without imaging',
    OVERRIDDEN: 'Continuing with clinician override', REQUIRES_CLINICIAN_ASSESSMENT: 'Clinician assessment required',
  };
  return (
    <div className="imaging-shell space-y-6">
      <header className="imaging-banner">
        <div><h1 className="imaging-banner-title">Imaging assessment</h1>
          <p className="imaging-banner-subtitle">Review the imaging decision and any clinician-supplied report.</p></div>
      </header>
      {!plan ? <p>Imaging has not been assessed in this session.</p> : (
        <section className="bg-white border rounded-xl p-6 space-y-3">
          <h2 className="text-xl font-bold">{labels[plan.status]}</h2>
          <p><strong>Decision:</strong> {plan.decision?.replace(/_/g, ' ') || 'Not confirmed'}</p>
          <p>{plan.reason}</p>
          {plan.modality && <p><strong>Requested study:</strong> {plan.modality} — {plan.anatomy}</p>}
          {plan.study_reference && <p><strong>Study reference:</strong> {plan.study_reference}</p>}
          {plan.report && <section className="bg-stone-50 p-4 rounded-lg">
            <h3 className="font-bold">Clinician-supplied report</h3>
            <p className="whitespace-pre-wrap">{plan.report}</p>
          </section>}
          <p className="text-sm">No automated image interpretation was performed. An absent report is not a normal imaging result.</p>
          {plan.limitations.map(text => <p key={text} className="text-sm text-stone-600">{text}</p>)}
        </section>
      )}
    </div>
  );
};
