export type ProblemAnalysis = {
  slug: string;
  approaches: ProblemApproach[];
};

export type RecognitionSignalsData = {
  quote?: string;
  bullets: string[];
};

export type ProblemApproach = {
  id: string;
  name: string;
  pattern: string;
  summary: string;
  isPrimary: boolean;
  displayOrder: number;
  thinkingSteps: string[];
  recognitionSignals?: RecognitionSignalsData;
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
          isPrimary: true,
          displayOrder: 1,
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
    typeof rawApproach.isPrimary !== "boolean" ||
    typeof rawApproach.displayOrder !== "number" ||
    !Array.isArray(rawApproach.thinkingSteps)
  ) {
    throw new Error("Invalid problem approach response.");
  }

  return {
    id: rawApproach.id,
    name: rawApproach.name,
    pattern: rawApproach.pattern,
    summary: rawApproach.summary,
    isPrimary: rawApproach.isPrimary,
    displayOrder: rawApproach.displayOrder,
    thinkingSteps: rawApproach.thinkingSteps.map(String),
    recognitionSignals: normalizeRecognitionSignals(rawApproach.recognitionSignals)
  };
}

function normalizeRecognitionSignals(value: unknown): RecognitionSignalsData | undefined {
  // Older backends may omit this optional metadata. Invalid signals should not
  // prevent the rest of Coach from working.
  if (!isRecord(value) || !Array.isArray(value.bullets) || value.bullets.length === 0 ||
    !value.bullets.every((bullet) => typeof bullet === "string" && bullet.trim())) {
    return undefined;
  }
  return {
    bullets: value.bullets.map((bullet: string) => bullet.trim()),
    ...(typeof value.quote === "string" && value.quote.trim() ? { quote: value.quote.trim() } : {})
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
