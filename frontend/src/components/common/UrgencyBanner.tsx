import { useWorkflow } from '../../context/WorkflowContext';

export const UrgencyBanner = () => {
  const { session } = useWorkflow();
  const assessment = session?.state.urgency;
  if (!assessment) return null;
  const urgent = assessment.status === 'URGENT_REVIEW';
  return (
    <section role={urgent ? 'alert' : 'status'} className={`border-2 rounded-xl p-4 mb-4 ${urgent ? 'border-red-700 bg-red-50 text-red-950' : 'border-amber-600 bg-amber-50 text-amber-950'}`}>
      <h3 className="font-bold">{urgent ? 'Urgent clinician review' : 'Urgency assessment requires clinical judgement'}</h3>
      <p className="text-sm">{assessment.action}</p>
      {assessment.reasons.map(reason => <p className="text-sm mt-1" key={reason.rule_id}>{reason.explanation}</p>)}
      {urgent && assessment.acknowledged && <p className="text-sm font-bold">Reviewed for continuation. These findings remain flagged.</p>}
      {assessment.missing_information.length > 0 && <p className="text-xs mt-2">Not assessed: {assessment.missing_information.join(', ')}.</p>}
      <details className="text-xs mt-2">
        <summary>Assessment scope</summary>
        {assessment.limitations.map(limit => <p key={limit}>{limit}</p>)}
        <p>Rule set: {assessment.rules_version}. {assessment.rules_review_status === 'PENDING_CLINICAL_REVIEW' ? 'Local clinical review pending.' : 'Local review recorded.'}</p>
      </details>
    </section>
  );
};
