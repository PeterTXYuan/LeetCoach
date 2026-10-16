import { useCallback, useEffect, useRef, useState } from "react";
import {
  type ApproachHintsResponse,
  fetchPrimaryApproachHints,
  fetchSpecificApproachHints
} from "../api/approachHints";
import type { SavedHints } from "../coachWorkspaceStorage";

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
  hintsByApproach?: Record<string, SavedHints>;
  disclosureRevision: number;
  updateHints: (
    slug: string, approachId: string,
    update: (current: SavedHints | undefined) => SavedHints | undefined
  ) => void;
};

type RequestState = { contextKey: string; status: "idle" | "loading" | "not_found" | "error" };

export function useApproachHints({
  slug,
  selectedApproachId,
  primaryApproachId,
  hintsByApproach,
  updateHints,
  disclosureRevision
}: UseApproachHintsOptions) {
  const approachId = selectedApproachId ?? primaryApproachId;
  const contextKey = JSON.stringify([slug, approachId, disclosureRevision]);
  const currentContextKey = useRef(contextKey);
  currentContextKey.current = contextKey;
  const [requestState, setRequestState] = useState<RequestState>({
    contextKey, status: "idle"
  });
  const [regenerationState, setRegenerationState] = useState<RequestState>({
    contextKey, status: "idle"
  });
  const abortRef = useRef<AbortController | null>(null);
  const saved = approachId ? hintsByApproach?.[approachId] : undefined;

  useEffect(() => {
    setRequestState({ contextKey, status: "idle" });
    setRegenerationState({ contextKey, status: "idle" });
    return () => abortRef.current?.abort();
  }, [contextKey]);

  const requestHints = useCallback(async (forceFresh: boolean) => {
    if (!slug || !approachId) return;
    if (saved && !forceFresh) {
      updateHints(slug, approachId, (current) => current
        ? { ...current, visibleHintCount: 1 }
        : current);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const setStatus = forceFresh ? setRegenerationState : setRequestState;
    setStatus({ contextKey, status: "loading" });
    try {
      const response = selectedApproachId
        ? await fetchSpecificApproachHints(slug, selectedApproachId, controller.signal, forceFresh)
        : await fetchPrimaryApproachHints(slug, controller.signal, forceFresh);
      if (controller.signal.aborted || currentContextKey.current !== contextKey) return;
      if (!response) {
        setStatus({ contextKey, status: forceFresh ? "error" : "not_found" });
        return;
      }
      if (response.slug !== slug || response.approachId !== approachId) {
        throw new Error("The hints do not match the requested canonical approach.");
      }
      updateHints(slug, approachId, () => ({ response, visibleHintCount: 1 }));
      setStatus({ contextKey, status: "idle" });
    } catch {
      if (!controller.signal.aborted && currentContextKey.current === contextKey) {
        setStatus({ contextKey, status: "error" });
      }
    }
  }, [slug, approachId, saved, selectedApproachId, contextKey, updateHints]);
  const requestFirstHint = useCallback(() => void requestHints(false), [requestHints]);
  const regenerateHints = useCallback(() => void requestHints(true), [requestHints]);

  const showNextHint = useCallback(() => {
    if (!slug || !approachId) return;
    updateHints(slug, approachId, (current) => current && current.visibleHintCount > 0
      ? { ...current, visibleHintCount: Math.min(
          current.visibleHintCount + 1, current.response.hints.length
        ) }
      : current);
  }, [slug, approachId, updateHints]);

  const resetHints = useCallback(() => {
    if (!slug || !approachId) return;
    abortRef.current?.abort();
    setRegenerationState({ contextKey, status: "idle" });
    updateHints(slug, approachId, (current) => current
      ? { ...current, visibleHintCount: 0 }
      : current);
  }, [slug, approachId, contextKey, updateHints]);

  const hintState: ApproachHintsState = saved
    ? { status: "success", response: saved.response }
    : requestState.contextKey === contextKey
      ? { status: requestState.status }
      : { status: "idle" };

  return {
    hintState,
    visibleHintCount: saved?.visibleHintCount ?? 0,
    requestFirstHint,
    retryHints: requestFirstHint,
    regenerateHints,
    regenerationStatus: regenerationState.contextKey === contextKey ? regenerationState.status : "idle",
    showNextHint,
    resetHints
  };
}
