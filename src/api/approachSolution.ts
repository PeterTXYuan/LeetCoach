export type SolutionLanguage = "python" | "java" | "javascript" | "cpp";

export type ApproachSolutionResponse = {
  slug: string;
  approachId: string;
  language: SolutionLanguage;
  isAiGenerated: boolean;
  warning: string;
  code: string;
  explanation: string;
  timeComplexity: string;
  spaceComplexity: string;
};

const backendBaseUrl = "http://localhost:8000";

export class UnsupportedLanguageRequestError extends Error {
  constructor() {
    super("Unsupported solution language.");
  }
}

export class SolutionProviderResponseError extends Error {
  constructor(readonly status: number) {
    super(`Full solution provider returned HTTP ${status}.`);
  }
}

export class InvalidApproachSolutionResponseError extends Error {
  constructor() {
    super("Invalid full solution response.");
  }
}

export async function fetchApproachSolution(
  slug: string,
  approachId: string,
  language: SolutionLanguage,
  signal?: AbortSignal
) {
  const response = await fetch(
    `${backendBaseUrl}/api/problems/${encodeURIComponent(
      slug
    )}/approaches/${encodeURIComponent(approachId)}/solution`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ language }),
      signal
    }
  );

  if (response.status === 404) {
    return null;
  }

  if (response.status === 400) {
    throw new UnsupportedLanguageRequestError();
  }

  if (!response.ok) throw new SolutionProviderResponseError(response.status);

  let result: ApproachSolutionResponse;
  try {
    result = normalizeApproachSolutionResponse(await response.json());
  } catch {
    throw new InvalidApproachSolutionResponseError();
  }
  if (result.slug !== slug || result.approachId !== approachId || result.language !== language) {
    throw new InvalidApproachSolutionResponseError();
  }
  return result;
}

export function normalizeApproachSolutionResponse(rawResponse: unknown): ApproachSolutionResponse {
  if (
    !isRecord(rawResponse) ||
    typeof rawResponse.slug !== "string" ||
    typeof rawResponse.approachId !== "string" ||
    !isSolutionLanguage(rawResponse.language) ||
    typeof rawResponse.isAiGenerated !== "boolean" ||
    typeof rawResponse.warning !== "string" ||
    typeof rawResponse.code !== "string" || !rawResponse.code.trim() ||
    typeof rawResponse.explanation !== "string" || !rawResponse.explanation.trim() ||
    typeof rawResponse.timeComplexity !== "string" || !rawResponse.timeComplexity.trim() ||
    typeof rawResponse.spaceComplexity !== "string" || !rawResponse.spaceComplexity.trim()
  ) {
    throw new Error("Invalid approach solution response.");
  }

  return {
    slug: rawResponse.slug,
    approachId: rawResponse.approachId,
    language: rawResponse.language,
    isAiGenerated: rawResponse.isAiGenerated,
    warning: rawResponse.warning,
    code: rawResponse.code,
    explanation: rawResponse.explanation,
    timeComplexity: rawResponse.timeComplexity,
    spaceComplexity: rawResponse.spaceComplexity
  };
}

function isSolutionLanguage(value: unknown): value is SolutionLanguage {
  return (
    value === "python" ||
    value === "java" ||
    value === "javascript" ||
    value === "cpp"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
