import type { ReactNode } from "react";
import { unavailableProblemMessage } from "../api/problemAnalysis";
import type { ProblemAnalysisState } from "../useProblemAnalysis";

type AnalysisStatusProps = {
  analysisState: ProblemAnalysisState;
  children: ReactNode;
  onRetry: () => void;
};

export function AnalysisStatus({
  analysisState,
  children,
  onRetry
}: AnalysisStatusProps) {
  if (analysisState.status === "loading") {
    return <p className="analysis-message">Loading pattern analysis...</p>;
  }

  if (analysisState.status === "not_found") {
    return <p className="analysis-message">{unavailableProblemMessage}</p>;
  }

  if (analysisState.status === "error") {
    return (
      <>
        <p className="analysis-message">
          Unable to connect to the local LeetCoach backend.
        </p>
        <button className="secondary-action" type="button" onClick={onRetry}>
          Retry
        </button>
      </>
    );
  }

  if (analysisState.status !== "success") {
    return null;
  }

  if (analysisState.analysis.approaches.length === 0) {
    return (
      <p className="analysis-message">
        This problem does not have any approaches in the local LeetCoach dataset
        yet.
      </p>
    );
  }

  return <>{children}</>;
}
