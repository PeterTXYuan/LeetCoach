import { useCallback, useEffect, useRef, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import {
  type ApproachSolutionResponse,
  type SolutionLanguage,
  UnsupportedLanguageRequestError,
  fetchApproachSolution
} from "../api/approachSolution";

export type ApproachSolutionState =
  | {
      status: "idle";
    }
  | {
      status: "loading";
    }
  | {
      status: "success";
      response: ApproachSolutionResponse;
    }
  | {
      status: "not_found";
    }
  | {
      status: "unsupported_language";
    }
  | {
      status: "error";
    };

type UseApproachSolutionOptions = {
  slug?: string;
  approachId: string | null;
};

type SolutionRequestContext = {
  slug: string;
  approachId: string;
  language: SolutionLanguage;
};

export function useApproachSolution({
  slug,
  approachId
}: UseApproachSolutionOptions) {
  const [solutionState, setSolutionState] = useState<ApproachSolutionState>({
    status: "idle"
  });
  const abortRef = useRef<AbortController | null>(null);
  const latestContextRef = useRef({ slug, approachId });
  const lastRequestContextRef = useRef<SolutionRequestContext | null>(null);

  useEffect(() => {
    latestContextRef.current = { slug, approachId };
  }, [approachId, slug]);

  const resetSolution = useCallback(() => {
    abortRef.current?.abort();
    lastRequestContextRef.current = null;
    setSolutionState({ status: "idle" });
  }, []);

  useEffect(() => {
    resetSolution();
    return () => abortRef.current?.abort();
  }, [approachId, slug, resetSolution]);

  const generateSolution = useCallback(
    (language: SolutionLanguage) => {
      if (!slug || !approachId) {
        return;
      }

      const requestContext = {
        slug,
        approachId,
        language
      };
      lastRequestContextRef.current = requestContext;
      void requestSolutionForContext(requestContext, {
        abortRef,
        latestContextRef,
        setSolutionState
      });
    },
    [approachId, slug]
  );

  const retrySolution = useCallback(() => {
    const requestContext = lastRequestContextRef.current;

    if (!requestContext) {
      return;
    }

    if (
      requestContext.slug !== latestContextRef.current.slug ||
      requestContext.approachId !== latestContextRef.current.approachId
    ) {
      return;
    }

    void requestSolutionForContext(requestContext, {
      abortRef,
      latestContextRef,
      setSolutionState
    });
  }, []);

  return {
    solutionState,
    generateSolution,
    retrySolution,
    resetSolution
  };
}

type RequestSolutionHelpers = {
  abortRef: MutableRefObject<AbortController | null>;
  latestContextRef: MutableRefObject<{
    slug?: string;
    approachId: string | null;
  }>;
  setSolutionState: Dispatch<SetStateAction<ApproachSolutionState>>;
};

async function requestSolutionForContext(
  context: SolutionRequestContext,
  { abortRef, latestContextRef, setSolutionState }: RequestSolutionHelpers
) {
  abortRef.current?.abort();
  const abortController = new AbortController();
  abortRef.current = abortController;
  setSolutionState({ status: "loading" });

  try {
    const response = await fetchApproachSolution(
      context.slug,
      context.approachId,
      context.language,
      abortController.signal
    );

    if (abortController.signal.aborted) {
      return;
    }

    if (response === null) {
      setSolutionState({ status: "not_found" });
      return;
    }

    if (response.language !== context.language) {
      throw new Error("The solution language does not match the request.");
    }

    if (!canApplyResponse(response, latestContextRef.current)) {
      setSolutionState({ status: "idle" });
      return;
    }

    setSolutionState({ status: "success", response });
  } catch (error) {
    if (abortController.signal.aborted) {
      return;
    }

    if (error instanceof UnsupportedLanguageRequestError) {
      setSolutionState({ status: "unsupported_language" });
      return;
    }

    setSolutionState({ status: "error" });
  }
}

function canApplyResponse(
  response: ApproachSolutionResponse,
  latestContext: {
    slug?: string;
    approachId: string | null;
  }
) {
  return (
    response.slug === latestContext.slug &&
    response.approachId === latestContext.approachId
  );
}
