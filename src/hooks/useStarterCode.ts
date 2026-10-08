import { useCallback, useEffect, useRef, useState } from "react";
import type { SolutionLanguage } from "../api/approachSolution";
import {
  fetchStarterCode, InvalidStarterOptionsError,
  type GuidanceLevel, type StarterCodeResponse
} from "../api/starterCode";

type StarterCodeState =
  | { status: "idle" | "loading" | "not_found" | "invalid_options" | "error" }
  | { status: "success"; response: StarterCodeResponse };

type StarterCodeOptions = {
  slug: string;
  approachId: string | null;
  language: SolutionLanguage;
  level: GuidanceLevel;
  onResult: (response: StarterCodeResponse) => void;
};

export function useStarterCode({ slug, approachId, language, level, onResult }: StarterCodeOptions) {
  const contextKey = JSON.stringify([slug, approachId, language, level]);
  const latestKey = useRef(contextKey);
  latestKey.current = contextKey;
  const [snapshot, setSnapshot] = useState<{ key: string; state: StarterCodeState }>({
    key: contextKey, state: { status: "idle" }
  });
  const abortRef = useRef<AbortController | null>(null);
  const clear = useCallback(() => {
    abortRef.current?.abort();
    setSnapshot({ key: contextKey, state: { status: "idle" } });
  }, [contextKey]);

  useEffect(() => {
    clear();
    return () => abortRef.current?.abort();
  }, [clear]);

  const generate = useCallback(async () => {
    if (!approachId) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const update = (state: StarterCodeState) => setSnapshot({ key: contextKey, state });
    update({ status: "loading" });
    try {
      const response = await fetchStarterCode(slug, approachId, language, level, controller.signal);
      if (!controller.signal.aborted && latestKey.current === contextKey) {
        if (response) onResult(response);
        update(response ? { status: "success", response } : { status: "not_found" });
      }
    } catch (error) {
      if (!controller.signal.aborted && latestKey.current === contextKey) {
        update({ status: error instanceof InvalidStarterOptionsError ? "invalid_options" : "error" });
      }
    }
  }, [slug, approachId, language, level, contextKey, onResult]);

  // Never show a prior language/level while its cleanup effect is pending.
  const state: StarterCodeState = snapshot.key === contextKey ? snapshot.state : { status: "idle" };
  return { state, generate, clear };
}
