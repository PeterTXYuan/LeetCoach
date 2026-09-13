import { useCallback, useEffect, useRef, useState } from "react";
import {
  type ApproachHintsResponse,
  fetchPrimaryApproachHints,
  fetchSpecificApproachHints
} from "../api/approachHints";

export type ApproachHintsState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; response: ApproachHintsResponse }
  | { status: "not_found" }
  | { status: "error" };

type UseApproachHintsOptions = {
  slug?: string;
  selectedApproachId: string | null;
  primaryApproachId: string | null;
};

type HintSnapshot = {
  contextKey: string;
  hintState: ApproachHintsState;
  visibleHintCount: number;
};

export function useApproachHints({
  slug,
  selectedApproachId,
  primaryApproachId
}: UseApproachHintsOptions) {
  const approachId = selectedApproachId ?? primaryApproachId;
  const contextKey = JSON.stringify([slug, approachId]);
  const [snapshot, setSnapshot] = useState<HintSnapshot>({
    contextKey,
    hintState: { status: "idle" },
    visibleHintCount: 0
  });
  const cacheRef = useRef(new Map<string, ApproachHintsResponse>());
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    cacheRef.current.clear();
  }, [slug]);

  // Default hints and explicitly selected primary hints share a canonical ID.
  // A different ID resets disclosure and cancels even a pending/error request.
  useEffect(() => {
    setSnapshot({ contextKey, hintState: { status: "idle" }, visibleHintCount: 0 });
    return () => abortRef.current?.abort();
  }, [contextKey]);

  const requestCurrentHints = useCallback(async () => {
    if (!slug || !approachId) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const update = (hintState: ApproachHintsState, visibleHintCount = 0) => {
      setSnapshot({ contextKey, hintState, visibleHintCount });
    };
    const cached = cacheRef.current.get(contextKey);
    if (cached) {
      update({ status: "success", response: cached }, Math.min(1, cached.hints.length));
      return;
    }

    update({ status: "loading" });
    try {
      const response = selectedApproachId
        ? await fetchSpecificApproachHints(slug, selectedApproachId, controller.signal)
        : await fetchPrimaryApproachHints(slug, controller.signal);
      if (controller.signal.aborted) return;
      if (!response) {
        update({ status: "not_found" });
        return;
      }
      if (response.slug !== slug || response.approachId !== approachId) {
        throw new Error("The hints do not match the requested canonical approach.");
      }
      cacheRef.current.set(contextKey, response);
      update({ status: "success", response }, Math.min(1, response.hints.length));
    } catch {
      if (!controller.signal.aborted) update({ status: "error" });
    }
  }, [slug, approachId, selectedApproachId, contextKey]);

  const showNextHint = useCallback(() => {
    setSnapshot((current) => {
      if (
        current.contextKey !== contextKey ||
        current.hintState.status !== "success" ||
        current.visibleHintCount === 0
      ) return current;
      return {
        ...current,
        visibleHintCount: Math.min(
          current.visibleHintCount + 1,
          current.hintState.response.hints.length
        )
      };
    });
  }, [contextKey]);

  const resetHints = useCallback(() => {
    setSnapshot((current) => ({ ...current, visibleHintCount: 0 }));
  }, []);

  // Hide the old context immediately, before the context-change effect runs.
  const current: HintSnapshot = snapshot.contextKey === contextKey
    ? snapshot
    : { contextKey, hintState: { status: "idle" }, visibleHintCount: 0 };

  return {
    hintState: current.hintState,
    visibleHintCount: current.visibleHintCount,
    requestFirstHint: requestCurrentHints,
    retryHints: requestCurrentHints,
    showNextHint,
    resetHints
  };
}
