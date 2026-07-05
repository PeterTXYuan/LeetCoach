import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import {
  type ApproachHintsResponse,
  fetchPrimaryApproachHints,
  fetchSpecificApproachHints
} from "../api/approachHints";

export type ApproachHintsState =
  | {
      status: "idle";
    }
  | {
      status: "loading";
    }
  | {
      status: "success";
      response: ApproachHintsResponse;
    }
  | {
      status: "not_found";
    }
  | {
      status: "error";
    };

type UseApproachHintsOptions = {
  slug?: string;
  selectedApproachId: string | null;
};

type HintRequestContext = {
  slug: string;
  requestedApproachId: string | null;
};

const primaryContextKey = "primary";

export function useApproachHints({
  slug,
  selectedApproachId
}: UseApproachHintsOptions) {
  const [hintState, setHintState] = useState<ApproachHintsState>({
    status: "idle"
  });
  const [visibleHintCount, setVisibleHintCount] = useState(0);
  const cacheRef = useRef(new Map<string, ApproachHintsResponse>());
  const abortRef = useRef<AbortController | null>(null);
  const lastRequestContextRef = useRef<HintRequestContext | null>(null);
  const hintStateRef = useRef(hintState);
  const latestContextRef = useRef({ slug, selectedApproachId });
  const previousSlugRef = useRef<string | undefined>(slug);

  useEffect(() => {
    hintStateRef.current = hintState;
  }, [hintState]);

  useEffect(() => {
    latestContextRef.current = { slug, selectedApproachId };
  }, [slug, selectedApproachId]);

  useEffect(() => {
    if (previousSlugRef.current !== slug) {
      previousSlugRef.current = slug;
      cacheRef.current.clear();
      abortRef.current?.abort();
      lastRequestContextRef.current = null;
      setHintState({ status: "idle" });
      setVisibleHintCount(0);
    }
  }, [slug]);

  useEffect(() => {
    const currentHintState = hintStateRef.current;

    if (
      currentHintState.status === "idle" ||
      currentHintState.status === "loading"
    ) {
      return;
    }

    if (
      currentHintState.status === "success" &&
      (!selectedApproachId ||
        currentHintState.response.approachId === selectedApproachId)
    ) {
      return;
    }

    abortRef.current?.abort();
    lastRequestContextRef.current = null;
    setHintState({ status: "idle" });
    setVisibleHintCount(0);
  }, [selectedApproachId]);

  const requestCurrentHints = useCallback(async () => {
    if (!slug) {
      return;
    }

    const requestContext: HintRequestContext = {
      slug,
      requestedApproachId: selectedApproachId
    };
    const cacheKey = getCacheKey(requestContext);
    const cachedResponse = cacheRef.current.get(cacheKey);

    lastRequestContextRef.current = requestContext;

    if (cachedResponse) {
      setHintState({ status: "success", response: cachedResponse });
      setVisibleHintCount(1);
      return;
    }

    abortRef.current?.abort();
    const abortController = new AbortController();
    abortRef.current = abortController;
    setHintState({ status: "loading" });

    try {
      const response = requestContext.requestedApproachId
        ? await fetchSpecificApproachHints(
            requestContext.slug,
            requestContext.requestedApproachId,
            abortController.signal
          )
        : await fetchPrimaryApproachHints(
            requestContext.slug,
            abortController.signal
          );

      if (abortController.signal.aborted) {
        return;
      }

      if (response === null) {
        setHintState({ status: "not_found" });
        setVisibleHintCount(0);
        return;
      }

      if (!canApplyResponse(response, requestContext, latestContextRef.current)) {
        setHintState({ status: "idle" });
        setVisibleHintCount(0);
        return;
      }

      cacheRef.current.set(cacheKey, response);
      setHintState({ status: "success", response });
      setVisibleHintCount(1);
    } catch {
      if (!abortController.signal.aborted) {
        setHintState({ status: "error" });
        setVisibleHintCount(0);
      }
    }
  }, [selectedApproachId, slug]);

  const retryHints = useCallback(() => {
    const lastContext = lastRequestContextRef.current;

    if (!lastContext) {
      void requestCurrentHints();
      return;
    }

    if (lastContext.slug !== latestContextRef.current.slug) {
      return;
    }

    void requestHintsForContext(lastContext, {
      cacheRef,
      abortRef,
      latestContextRef,
      setHintState,
      setVisibleHintCount
    });
  }, [requestCurrentHints]);

  const showNextHint = useCallback(() => {
    setVisibleHintCount((count) => {
      if (hintState.status !== "success") {
        return count;
      }

      return Math.min(count + 1, hintState.response.hints.length);
    });
  }, [hintState]);

  const resetHints = useCallback(() => {
    setVisibleHintCount(0);
  }, []);

  return useMemo(
    () => ({
      hintState,
      visibleHintCount,
      requestFirstHint: requestCurrentHints,
      showNextHint,
      resetHints,
      retryHints
    }),
    [
      hintState,
      requestCurrentHints,
      resetHints,
      retryHints,
      showNextHint,
      visibleHintCount
    ]
  );
}

function getCacheKey(context: HintRequestContext) {
  return `${context.slug}:${context.requestedApproachId ?? primaryContextKey}`;
}

function canApplyResponse(
  response: ApproachHintsResponse,
  requestContext: HintRequestContext,
  latestContext: {
    slug?: string;
    selectedApproachId: string | null;
  }
) {
  if (response.slug !== latestContext.slug || response.slug !== requestContext.slug) {
    return false;
  }

  if (!latestContext.selectedApproachId) {
    return requestContext.requestedApproachId === null;
  }

  return response.approachId === latestContext.selectedApproachId;
}

type RequestHintsHelpers = {
  cacheRef: MutableRefObject<Map<string, ApproachHintsResponse>>;
  abortRef: MutableRefObject<AbortController | null>;
  latestContextRef: MutableRefObject<{
    slug?: string;
    selectedApproachId: string | null;
  }>;
  setHintState: Dispatch<SetStateAction<ApproachHintsState>>;
  setVisibleHintCount: Dispatch<SetStateAction<number>>;
};

async function requestHintsForContext(
  context: HintRequestContext,
  {
    cacheRef,
    abortRef,
    latestContextRef,
    setHintState,
    setVisibleHintCount
  }: RequestHintsHelpers
) {
  const cacheKey = getCacheKey(context);
  const cachedResponse = cacheRef.current.get(cacheKey);

  if (cachedResponse) {
    setHintState({ status: "success", response: cachedResponse });
    setVisibleHintCount(1);
    return;
  }

  abortRef.current?.abort();
  const abortController = new AbortController();
  abortRef.current = abortController;
  setHintState({ status: "loading" });

  try {
    const response = context.requestedApproachId
      ? await fetchSpecificApproachHints(
          context.slug,
          context.requestedApproachId,
          abortController.signal
        )
      : await fetchPrimaryApproachHints(context.slug, abortController.signal);

    if (abortController.signal.aborted) {
      return;
    }

    if (response === null) {
      setHintState({ status: "not_found" });
      setVisibleHintCount(0);
      return;
    }

    if (!canApplyResponse(response, context, latestContextRef.current)) {
      setHintState({ status: "idle" });
      setVisibleHintCount(0);
      return;
    }

    cacheRef.current.set(cacheKey, response);
    setHintState({ status: "success", response });
    setVisibleHintCount(1);
  } catch {
    if (!abortController.signal.aborted) {
      setHintState({ status: "error" });
      setVisibleHintCount(0);
    }
  }
}
