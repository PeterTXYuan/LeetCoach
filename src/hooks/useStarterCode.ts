import { useCallback, useEffect, useRef, useState } from "react";
import type { SolutionLanguage } from "../api/approachSolution";
import {
  fetchStarterCodeBatch, InvalidStarterOptionsError,
  starterCodePolicyVersion, type StarterCodeBatchResponse
} from "../api/starterCode";

type StarterCodeState =
  | { status: "idle" | "loading" | "not_found" | "invalid_options" | "error" }
  | { status: "success"; response: StarterCodeBatchResponse };

type StarterCodeOptions = {
  slug: string;
  approachId: string | null;
  language: SolutionLanguage;
  onResult: (response: StarterCodeBatchResponse) => void;
};

export function useStarterCode({ slug, approachId, language, onResult }: StarterCodeOptions) {
  const contextKey = JSON.stringify([slug, approachId, language, starterCodePolicyVersion]);
  const latestKey = useRef(contextKey);
  latestKey.current = contextKey;
  const [snapshot, setSnapshot] = useState<{ key: string; state: StarterCodeState }>({
    key: contextKey, state: { status: "idle" }
  });
  const abortRef = useRef<AbortController | null>(null);
  const clear = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setSnapshot({ key: contextKey, state: { status: "idle" } });
  }, [contextKey]);

  useEffect(() => {
    clear();
    return () => abortRef.current?.abort();
  }, [clear]);

  const generate = useCallback(async () => {
    if (!approachId || abortRef.current) return;
    const controller = new AbortController();
    abortRef.current = controller;
    const update = (state: StarterCodeState) => setSnapshot({ key: contextKey, state });
    update({ status: "loading" });
    try {
      const response = await fetchStarterCodeBatch(slug, approachId, language, controller.signal);
      if (!controller.signal.aborted && abortRef.current === controller && latestKey.current === contextKey) {
        if (response) onResult(response);
        update(response ? { status: "success", response } : { status: "not_found" });
      }
    } catch (error) {
      if (!controller.signal.aborted && abortRef.current === controller && latestKey.current === contextKey) {
        update({ status: error instanceof InvalidStarterOptionsError ? "invalid_options" : "error" });
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }, [slug, approachId, language, contextKey, onResult]);

  // Never show a prior language batch while its cleanup effect is pending.
  const state: StarterCodeState = snapshot.key === contextKey ? snapshot.state : { status: "idle" };
  return { state, generate, clear };
}
