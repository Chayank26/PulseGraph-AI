import { Link } from 'react-router-dom';
import { useWorkflow } from '../../context/WorkflowContext';

export const TriageHandoffBanner = () => {
  const { session } = useWorkflow();
  if (session?.status !== 'REQUIRES_CLINICIAN_ASSESSMENT') return null;
  return (
    <section role="status" className="border-2 border-amber-600 bg-amber-50 rounded-xl p-4 mb-4">
      <h3 className="font-bold">Clinician assessment required</h3>
      <p className="text-sm">Automated assessment has stopped. Review the unresolved assessment below.</p>
      {session.state.presentation?.routing?.handoff_reasons.map(reason => <p key={reason} className="text-sm mt-1">{reason}</p>)}
      {session.state.presentation?.imaging_plan?.status === 'REQUIRES_CLINICIAN_ASSESSMENT' && (
        <p className="text-sm mt-1">{session.state.presentation.imaging_plan.reason} <Link to="/imaging" className="underline">Review imaging decision</Link></p>
      )}
      <Link to="/triage" className="text-sm underline">Review triage assessment and limitations</Link>
    </section>
  );
};
