export type ProblemAnalysis = {
  slug: string;
  approaches: ProblemApproach[];
};

export type ProblemApproach = {
  id: string;
  name: string;
  pattern: string;
  summary: string;
  thinkingSteps: string[];
};

export const unavailableProblemMessage =
  "This problem is not available in the local LeetCoach dataset yet.";

const backendBaseUrl = "http://localhost:8000";

export async function fetchProblemAnalysis(
  slug: string,
  signal?: AbortSignal
): Promise<ProblemAnalysis | null> {
  const response = await fetch(
    `${backendBaseUrl}/api/problems/${encodeURIComponent(slug)}`,
    { signal }
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Problem analysis request failed: ${response.status}`);
  }

  return normalizeProblemAnalysis(await response.json());
}

export function normalizeProblemAnalysis(rawAnalysis: unknown): ProblemAnalysis {
  if (!isRecord(rawAnalysis) || typeof rawAnalysis.slug !== "string") {
    throw new Error("Invalid problem analysis response.");
  }

  if (Array.isArray(rawAnalysis.approaches)) {
    return {
      slug: rawAnalysis.slug,
      approaches: rawAnalysis.approaches.map(normalizeApproach)
    };
  }

  if (
    isRecord(rawAnalysis.pattern) &&
    typeof rawAnalysis.pattern.name === "string" &&
    typeof rawAnalysis.pattern.summary === "string" &&
    Array.isArray(rawAnalysis.thinkingSteps)
  ) {
    return {
      slug: rawAnalysis.slug,
      approaches: [
        {
          id: "legacy-primary",
          name: rawAnalysis.pattern.name,
          pattern: rawAnalysis.pattern.name,
          summary: rawAnalysis.pattern.summary,
          thinkingSteps: rawAnalysis.thinkingSteps.map(String)
        }
      ]
    };
  }

  throw new Error("Invalid problem analysis response.");
}

function normalizeApproach(rawApproach: unknown): ProblemApproach {
  if (
    !isRecord(rawApproach) ||
    typeof rawApproach.id !== "string" ||
    typeof rawApproach.name !== "string" ||
    typeof rawApproach.pattern !== "string" ||
    typeof rawApproach.summary !== "string" ||
    !Array.isArray(rawApproach.thinkingSteps)
  ) {
    throw new Error("Invalid problem approach response.");
  }

  return {
    id: rawApproach.id,
    name: rawApproach.name,
    pattern: rawApproach.pattern,
    summary: rawApproach.summary,
    thinkingSteps: rawApproach.thinkingSteps.map(String)
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
