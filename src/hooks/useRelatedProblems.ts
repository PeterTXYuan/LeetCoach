import { useEffect, useRef, useState } from "react";
import { fetchRelatedProblems, type RelatedProblemsResponse } from "../api/relatedProblems";

type RelatedState =
  | { status: "idle" | "loading" | "not_found" | "error" }
  | { status: "success"; response: RelatedProblemsResponse };

export function useRelatedProblems(slug: string, isActive: boolean) {
  const [snapshot, setSnapshot] = useState<{ slug: string; state: RelatedState }>({ slug, state: { status: "idle" } });
  const [attempt, setAttempt] = useState(0);
  const cache = useRef(new Map<string, RelatedProblemsResponse | null>());

  useEffect(() => {
    if (!isActive) return;
    const update = (state: RelatedState) => setSnapshot({ slug, state });
    if (cache.current.has(slug)) {
      const response = cache.current.get(slug)!;
      update(response ? { status: "success", response } : { status: "not_found" });
      return;
    }
    const controller = new AbortController();
    update({ status: "loading" });
    void fetchRelatedProblems(slug, controller.signal).then((response) => {
      if (controller.signal.aborted) return;
      cache.current.set(slug, response);
      update(response ? { status: "success", response } : { status: "not_found" });
    }).catch(() => {
      if (!controller.signal.aborted) update({ status: "error" });
    });
    return () => controller.abort();
  }, [slug, isActive, attempt]);

  return {
    state: snapshot.slug === slug ? snapshot.state : { status: isActive ? "loading" : "idle" } as RelatedState,
    retry: () => {
      if (!isActive) return;
      cache.current.delete(slug);
      setAttempt((value) => value + 1);
    }
  };
}
