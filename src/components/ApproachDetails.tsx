import type { ProblemApproach } from "../api/problemAnalysis";

type ApproachDetailsProps = {
  approach: ProblemApproach;
  onClose: () => void;
};

export function ApproachDetails({ approach, onClose }: ApproachDetailsProps) {
  return (
    <section className="selected-approach reveal-motion" aria-label={approach.name}>
      <div className="selected-approach-header">
        <p className="analysis-label">Selected approach</p>
        <button
          aria-label="Close selected approach"
          className="close-approach-button"
          type="button"
          onClick={onClose}
        >
          Close
        </button>
      </div>
      <h3 className="approach-title">{approach.name}</h3>
      <dl className="approach-details">
        <div>
          <dt>Pattern</dt>
          <dd>{approach.pattern}</dd>
        </div>
        <div>
          <dt>Summary</dt>
          <dd>{approach.summary}</dd>
        </div>
      </dl>
    </section>
  );
}
