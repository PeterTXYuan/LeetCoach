import { useEffect, useState } from "react";
import {
  fetchProblemAnalysis,
  type ProblemAnalysis
} from "./api/problemAnalysis";

export type ProblemAnalysisState =
  | {
      status: "idle";
    }
  | {
      status: "loading";
    }
  | {
      status: "success";
      analysis: ProblemAnalysis;
    }
  | {
      status: "not_found";
    }
  | {
      status: "error";
    };

export function useProblemAnalysis(slug?: string) {
  const [analysisState, setAnalysisState] = useState<ProblemAnalysisState>({
    status: "idle"
  });
  const [retryAttempt, setRetryAttempt] = useState(0);

  useEffect(() => {
    if (!slug) {
      setAnalysisState({ status: "idle" });
      return;
    }

    const abortController = new AbortController();

    const loadAnalysis = async () => {
      setAnalysisState({ status: "loading" });

      try {
        const analysis = await fetchProblemAnalysis(
          slug,
          abortController.signal
        );

        if (abortController.signal.aborted) {
          return;
        }

        setAnalysisState(
          analysis
            ? { status: "success", analysis }
            : { status: "not_found" }
        );
      } catch {
        if (!abortController.signal.aborted) {
          setAnalysisState({ status: "error" });
        }
      }
    };

    void loadAnalysis();

    return () => {
      abortController.abort();
    };
  }, [slug, retryAttempt]);

  return {
    analysisState,
    retry: () => setRetryAttempt((attempt) => attempt + 1)
  };
}
