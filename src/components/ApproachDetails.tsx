import type { ProblemApproach } from "../api/problemAnalysis";

type ApproachDetailsProps = {
  approach: ProblemApproach;
};

export function ApproachDetails({ approach }: ApproachDetailsProps) {
  return (
    <section className="selected-approach" aria-label={approach.name}>
      <p className="analysis-label">Selected approach</p>
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
