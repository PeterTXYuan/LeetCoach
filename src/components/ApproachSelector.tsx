import type { ProblemApproach } from "../api/problemAnalysis";

type ApproachSelectorProps = {
  approaches: ProblemApproach[];
  onSelectApproach: (approachId: string) => void;
  selectedApproachId: string | null;
};

export function ApproachSelector({
  approaches,
  onSelectApproach,
  selectedApproachId
}: ApproachSelectorProps) {
  return (
    <section className="approach-selector" aria-labelledby="approach-selector-title">
      <p className="section-kicker">Solution strategies</p>
      <h2 id="approach-selector-title">Choose an approach</h2>
      <p className="section-copy compact">
        Pick a path to explore. Names and patterns stay hidden until you choose.
      </p>
      <div className="approach-button-group" aria-label="Available approaches">
        {approaches.map((approach, index) => (
          <button
            aria-pressed={selectedApproachId === approach.id}
            className={
              selectedApproachId === approach.id
                ? "approach-button selected"
                : "approach-button"
            }
            key={approach.id}
            type="button"
            onClick={() => onSelectApproach(approach.id)}
          >
            Approach {index + 1}
          </button>
        ))}
      </div>
    </section>
  );
}
