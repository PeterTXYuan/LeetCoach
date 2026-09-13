import type { ApproachHintsState } from "../hooks/useApproachHints";

type HintPanelProps = {
  approachNumber?: number;
  hintState: ApproachHintsState;
  onRequestFirstHint: () => void;
  onResetHints: () => void;
  onRetryHints: () => void;
  onShowNextHint: () => void;
  visibleHintCount: number;
};

export function HintPanel({
  approachNumber,
  hintState,
  onRequestFirstHint,
  onResetHints,
  onRetryHints,
  onShowNextHint,
  visibleHintCount
}: HintPanelProps) {
  const hasVisibleHints =
    hintState.status === "success" && visibleHintCount > 0;
  const totalHints =
    hintState.status === "success" ? hintState.response.hints.length : 0;
  const visibleHints =
    hintState.status === "success"
      ? hintState.response.hints.slice(0, visibleHintCount)
      : [];
  const hasMoreHints =
    hasVisibleHints && visibleHintCount < totalHints;

  return (
    <section className="hint-panel" aria-labelledby="hint-panel-title">
      <div className="section-heading-row">
        <div>
          <p className="section-kicker">Progressive guidance</p>
          <div className="hint-title-row">
            <h2 id="hint-panel-title">Hints</h2>
            {approachNumber !== undefined && (
              <span className="hint-approach-badge" aria-label={`Hints for Approach ${approachNumber}`}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="6" cy="5" r="2" />
                  <circle cx="6" cy="19" r="2" />
                  <circle cx="18" cy="5" r="2" />
                  <path d="M6 7v10M18 7a6 6 0 0 1-6 6H6" />
                </svg>
                Approach {approachNumber}
              </span>
            )}
          </div>
        </div>
        {hasVisibleHints && (
          <button
            aria-label="Reset revealed hints"
            className="text-action"
            type="button"
            onClick={onResetHints}
          >
            Reset hints
          </button>
        )}
      </div>

      {hintState.status === "idle" && (
        <button
          aria-label="Get first hint"
          className="secondary-action"
          type="button"
          onClick={onRequestFirstHint}
        >
          Get first hint
        </button>
      )}

      {hintState.status === "loading" && (
        <p className="analysis-message">Loading hint...</p>
      )}

      {hintState.status === "not_found" && (
        <>
          <p className="analysis-message">
            Hints are not available for this approach yet.
          </p>
          <button
            aria-label="Retry loading hints"
            className="secondary-action"
            type="button"
            onClick={onRetryHints}
          >
            Retry
          </button>
        </>
      )}

      {hintState.status === "error" && (
        <>
          <p className="analysis-message">
            Unable to load hints from the local LeetCoach backend.
          </p>
          <button
            aria-label="Retry loading hints"
            className="secondary-action"
            type="button"
            onClick={onRetryHints}
          >
            Retry
          </button>
        </>
      )}

      {hasVisibleHints && (
        <ol className="hint-list">
          {visibleHints.map((hint, index) => (
            <li className="reveal-motion" key={`${index}-${hint}`}>
              <span className="hint-count">
                Hint {index + 1} of {totalHints}
              </span>
              <p>{hint}</p>
            </li>
          ))}
        </ol>
      )}

      {hintState.status === "success" && visibleHintCount === 0 && (
        <button
          aria-label="Get first hint"
          className="secondary-action"
          type="button"
          onClick={onRequestFirstHint}
        >
          Get first hint
        </button>
      )}

      {hasMoreHints && (
        <button
          aria-label="Show next hint"
          className="secondary-action"
          type="button"
          onClick={onShowNextHint}
        >
          Show next hint
        </button>
      )}

      {hintState.status === "success" &&
        totalHints > 0 &&
        visibleHintCount === totalHints && (
          <p className="all-hints-revealed">All hints revealed</p>
        )}
    </section>
  );
}
