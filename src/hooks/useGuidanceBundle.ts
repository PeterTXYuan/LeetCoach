import { useEffect, useRef, useState } from "react";
import { fetchGuidanceBundle, type GuidanceBundle } from "../api/guidanceBundle";
import type { SolutionLanguage } from "../api/approachSolution";
import { emptySolution, emptyStarter, type CoachWorkspace } from "../coachWorkspaceStorage";

export type BundleStatus = { status: "idle" | "loading" | "error" | "not_found";
  message?: string; stage?: "starter" | "answer" | "both" };
type Stage = "starter" | "answer";
type Entry = { promise: Promise<GuidanceBundle | null>; controller: AbortController; sequence: number };
const requestKey = (slug: string, approachId: string, language: SolutionLanguage) =>
  JSON.stringify([slug, approachId, language]);

export function useGuidanceBundle(workspace: CoachWorkspace | undefined,
  updateWorkspace: (slug: string, update: (current: CoachWorkspace) => CoachWorkspace) => void) {
  const workspaceRef = useRef(workspace);
  workspaceRef.current = workspace;
  const inFlight = useRef(new Map<string, Entry>());
  const sequences = useRef(new Map<string, number>());
  const disclosureTokens = useRef(new Map<string, number>());
  const [statuses, setStatuses] = useState<Record<string, BundleStatus>>({});
  useEffect(() => () => {
    for (const entry of inFlight.current.values()) entry.controller.abort();
    inFlight.current.clear();
  }, []);

  const statusFor = (slug: string, approachId: string | null, language: SolutionLanguage,
    stage?: Stage): BundleStatus => {
    const status = approachId ? statuses[requestKey(slug, approachId, language)] : undefined;
    return status && (!stage || !status.stage || status.stage === stage || status.stage === "both")
      ? status : { status: "idle" };
  };
  const bundleFor = (approachId: string | null, language: SolutionLanguage) =>
    approachId ? workspace?.guidanceByApproach?.[approachId]?.[language] : undefined;

  const tokenKey = (slug: string, approachId: string, language: SolutionLanguage, stage: Stage) =>
    `${requestKey(slug, approachId, language)}:${stage}`;
  const cancelDisclosure = (slug: string, approachId: string, language: SolutionLanguage, stage: Stage) => {
    const key = tokenKey(slug, approachId, language, stage);
    disclosureTokens.current.set(key, (disclosureTokens.current.get(key) ?? 0) + 1);
  };

  const reveal = (slug: string, approachId: string, language: SolutionLanguage,
    stage: Stage, revision: number, token: number) => {
    if ((disclosureTokens.current.get(tokenKey(slug, approachId, language, stage)) ?? 0) !== token) return;
    updateWorkspace(slug, (current) => {
      if ((disclosureTokens.current.get(tokenKey(slug, approachId, language, stage)) ?? 0) !== token ||
          current.disclosureRevision !== revision ||
          (stage === "answer" && (current.selectedApproachId !== approachId ||
            (current.solutionByApproach[approachId] ?? emptySolution()).language !== language)) ||
          (stage === "starter" && (current.starterByApproach[approachId] ?? emptyStarter()).language !== language))
        return current;
      if (stage === "starter") {
        const previous = current.starterByApproach[approachId] ?? emptyStarter();
        return { ...current, starterByApproach: { ...current.starterByApproach,
          [approachId]: { ...previous, isExpanded: true, isVisible: true } } };
      }
      const previous = current.solutionByApproach[approachId] ?? emptySolution();
      return { ...current, solutionByApproach: { ...current.solutionByApproach,
        [approachId]: { ...previous, visibleByLanguage: { ...previous.visibleByLanguage, [language]: true } } } };
    });
  };

  const request = async (slug: string, approachId: string, language: SolutionLanguage,
    stage: Stage, force = false): Promise<void> => {
    const key = requestKey(slug, approachId, language);
    const revision = workspaceRef.current?.disclosureRevision ?? 0;
    const token = disclosureTokens.current.get(tokenKey(slug, approachId, language, stage)) ?? 0;
    const cached = workspaceRef.current?.guidanceByApproach?.[approachId]?.[language];
    if (cached && !force) {
      if (stage === "answer" && !cached.solution) {
        setStatuses((current) => ({ ...current, [key]: { status: "not_found", stage } }));
      } else reveal(slug, approachId, language, stage, revision, token);
      return;
    }
    let entry = inFlight.current.get(key);
    if (!entry) {
      const controller = new AbortController();
      const sequence = (sequences.current.get(key) ?? 0) + 1;
      sequences.current.set(key, sequence);
      setStatuses((current) => ({ ...current, [key]: { status: "loading", stage } }));
      const promise = fetchGuidanceBundle(slug, approachId, language, controller.signal)
        .then((bundle) => {
          if (controller.signal.aborted || sequences.current.get(key) !== sequence) return null;
          if (bundle) updateWorkspace(slug, (current) => ({ ...current,
            guidanceByApproach: { ...current.guidanceByApproach,
              [approachId]: { ...current.guidanceByApproach?.[approachId], [language]: bundle } }
          }));
          setStatuses((current) => ({ ...current, [key]: { status: bundle ? "idle" : "not_found" } }));
          return bundle;
        }).catch((error: unknown) => {
          if (!controller.signal.aborted && sequences.current.get(key) === sequence)
            setStatuses((current) => ({ ...current, [key]: { status: "error",
              stage: current[key]?.stage,
              message: `${error instanceof Error ? error.message : "Could not generate guidance."} ` +
                "Your previous Starter Code and answer are still available." } }));
          return null;
        }).finally(() => {
          if (inFlight.current.get(key)?.sequence === sequence) inFlight.current.delete(key);
        });
      entry = { promise, controller, sequence };
      inFlight.current.set(key, entry);
    } else {
      setStatuses((current) => ({ ...current, [key]: { status: "loading", stage: "both" } }));
    }
    const bundle = await entry.promise;
    if (bundle?.solution || stage === "starter") reveal(slug, approachId, language, stage, revision, token);
    else if (bundle && stage === "answer")
      setStatuses((current) => ({ ...current, [key]: { status: "not_found", stage } }));
  };
  return { bundleFor, statusFor, request, cancelDisclosure };
}
