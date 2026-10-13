import { useId } from "react";
import type { RecognitionSignalsData } from "../api/problemAnalysis";

type RecognitionSignalsProps = {
  signals: RecognitionSignalsData;
  slug: string;
  isRevealed: boolean;
  onToggle: () => void;
};

export function RecognitionSignals({ signals, slug, isRevealed, onToggle }: RecognitionSignalsProps) {
  const id = useId();

  return (
    <section className="recognition-section" aria-labelledby={`${id}-title`}>
      <div className="hint-title-row">
        <svg className="recognition-icon" width="16" height="16" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M9 18h6M10 21h4M8 14a6 6 0 1 1 8 0c-1 1-1 2-1 2H9s0-1-1-2Z" />
        </svg>
        <h2 id={`${id}-title`}>Recognition Signals</h2>
      </div>
      <button className="secondary-action" type="button" aria-expanded={isRevealed}
        aria-controls={`${id}-content`} onClick={onToggle}>
        {isRevealed ? "Hide recognition signals" : "Reveal recognition signals"}
      </button>
      <div id={`${id}-content`} hidden={!isRevealed}>
        {isRevealed && (
          <div className="recognition-content reveal-motion">
            {signals.quote && (
              <blockquote className="recognition-quote" cite={`https://leetcode.com/problems/${encodeURIComponent(slug)}/`}>
                <p>“{signals.quote}”</p>
              </blockquote>
            )}
            <ul className="recognition-list">
              {signals.bullets.map((bullet, index) => <li key={index}>{bullet}</li>)}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
