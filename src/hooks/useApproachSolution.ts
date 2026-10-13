import { useEffect, useRef, useState } from "react";
import {
  type ApproachSolutionResponse, type SolutionLanguage,
  InvalidApproachSolutionResponseError, SolutionProviderResponseError, UnsupportedLanguageRequestError,
  fetchApproachSolution
} from "../api/approachSolution";
import { emptySolution, type SavedSolution } from "../coachWorkspaceStorage";

export type ApproachSolutionState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; response: ApproachSolutionResponse }
  | { status: "not_found" }
  | { status: "unsupported_language" }
  | { status: "error"; message: string };

type UseApproachSolutionOptions = {
  slug?: string;
  approachId: string | null;
  disclosureRevision: number;
  saved?: SavedSolution;
  onSave?: (update: (current: SavedSolution) => SavedSolution) => void;
};

type RequestContext = { slug: string; approachId: string; language: SolutionLanguage };
type TransientState = { key: string; state: ApproachSolutionState };
const contextKey = (slug?: string, approachId?: string | null, language?: SolutionLanguage,
  disclosureRevision?: number) => JSON.stringify([slug, approachId, language, disclosureRevision]);

export function useApproachSolution({ slug, approachId, disclosureRevision, saved, onSave }: UseApproachSolutionOptions) {
  const [localSaved, setLocalSaved] = useState<SavedSolution>(emptySolution);
  const settings = saved ?? localSaved;
  const language = settings.language;
  const updateSettings = (update: (current: SavedSolution) => SavedSolution) => {
    if (onSave) onSave(update);
    else setLocalSaved(update);
  };
  const key = contextKey(slug, approachId, language, disclosureRevision);
  const latestKeyRef = useRef(key);
  latestKeyRef.current = key;
  const abortRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);
  const lastRequestRef = useRef<RequestContext | null>(null);
  const [transient, setTransient] = useState<TransientState | null>(null);

  useEffect(() => {
    requestIdRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    lastRequestRef.current = null;
    setTransient(null);
    return () => abortRef.current?.abort();
  }, [key]);

  const candidate = settings.responses[language];
  const cached = candidate && candidate.slug === slug && candidate.approachId === approachId &&
    candidate.language === language ? candidate : undefined;
  const solutionState: ApproachSolutionState = transient?.key === key
    ? transient.state
    : cached && settings.visibleByLanguage[language]
      ? { status: "success", response: cached }
      : { status: "idle" };

  const chooseLanguage = (next: SolutionLanguage) => {
    requestIdRef.current += 1;
    abortRef.current?.abort();
    lastRequestRef.current = null;
    setTransient(null);
    updateSettings((current) => ({ ...current, language: next }));
  };

  const hideSolution = () => {
    requestIdRef.current += 1;
    abortRef.current?.abort();
    setTransient(null);
    updateSettings((current) => ({ ...current,
      visibleByLanguage: { ...current.visibleByLanguage, [current.language]: false }
    }));
  };

  const request = (context: RequestContext) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestId = ++requestIdRef.current;
    const requestKey = key;
    lastRequestRef.current = context;
    setTransient({ key: requestKey, state: { status: "loading" } });
    void fetchApproachSolution(context.slug, context.approachId, context.language, controller.signal)
      .then((response) => {
        if (controller.signal.aborted || requestId !== requestIdRef.current ||
            requestKey !== latestKeyRef.current) return;
        if (!response) {
          setTransient({ key: requestKey, state: { status: "not_found" } });
          return;
        }
        updateSettings((current) => ({ ...current,
          responses: { ...current.responses, [context.language]: response },
          visibleByLanguage: { ...current.visibleByLanguage, [context.language]: true }
        }));
        setTransient(null);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || requestId !== requestIdRef.current ||
            requestKey !== latestKeyRef.current) return;
        if (error instanceof UnsupportedLanguageRequestError) {
          setTransient({ key: requestKey, state: { status: "unsupported_language" } });
          return;
        }
        const message = error instanceof InvalidApproachSolutionResponseError
          ? "The full solution response did not match this problem, approach, or language. Please retry."
          : error instanceof SolutionProviderResponseError
          ? error.status === 502
            ? "The generated full solution could not be verified. Please retry."
            : error.status === 503
              ? "The full solution provider is unavailable. Check its configuration and retry."
              : "Unable to load the full solution. Please retry."
          : "Unable to connect to the local LeetCoach backend.";
        setTransient({ key: requestKey, state: { status: "error", message } });
      });
  };

  const generateSolution = () => {
    if (!slug || !approachId || solutionState.status === "loading") return;
    if (cached) {
      setTransient(null);
      updateSettings((current) => ({ ...current,
        visibleByLanguage: { ...current.visibleByLanguage, [language]: true }
      }));
      return;
    }
    request({ slug, approachId, language });
  };

  const retrySolution = () => {
    const context = lastRequestRef.current;
    if (!context || contextKey(context.slug, context.approachId, context.language,
      disclosureRevision) !== key) return;
    request(context);
  };

  return { language, solutionState, generateSolution, retrySolution, chooseLanguage, hideSolution };
}
