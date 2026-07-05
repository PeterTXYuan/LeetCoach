import type { ProblemApproach } from "../api/problemAnalysis";

type ThinkingProcessProps = {
  approach: ProblemApproach;
  isExpanded: boolean;
  onToggle: () => void;
};

export function ThinkingProcess({
  approach,
  isExpanded,
  onToggle
}: ThinkingProcessProps) {
  return (
    <section className="thinking-process" aria-labelledby="thinking-title">
      <button
        aria-expanded={isExpanded}
        aria-controls="thinking-steps"
        className="secondary-action"
        type="button"
        onClick={onToggle}
      >
        {isExpanded ? "Hide thinking process" : "Show thinking process"}
      </button>

      {isExpanded && (
        <>
          <h3 id="thinking-title" className="thinking-title">
            Thinking process
          </h3>
          <ol className="thinking-steps" id="thinking-steps">
            {approach.thinkingSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}
