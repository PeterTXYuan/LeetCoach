export type ApproachHintsResponse = {
  slug: string;
  approachId: string;
  hints: string[];
};

const backendBaseUrl = "http://localhost:8000";

export async function fetchPrimaryApproachHints(
  slug: string,
  signal?: AbortSignal
) {
  return fetchApproachHintsResponse(
    `${backendBaseUrl}/api/problems/${encodeURIComponent(slug)}/hints`,
    signal
  );
}

export async function fetchSpecificApproachHints(
  slug: string,
  approachId: string,
  signal?: AbortSignal
) {
  return fetchApproachHintsResponse(
    `${backendBaseUrl}/api/problems/${encodeURIComponent(
      slug
    )}/approaches/${encodeURIComponent(approachId)}/hints`,
    signal
  );
}

async function fetchApproachHintsResponse(
  url: string,
  signal?: AbortSignal
): Promise<ApproachHintsResponse | null> {
  const response = await fetch(url, { signal });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Approach hints request failed: ${response.status}`);
  }

  return normalizeApproachHintsResponse(await response.json());
}

function normalizeApproachHintsResponse(rawResponse: unknown) {
  if (
    !isRecord(rawResponse) ||
    typeof rawResponse.slug !== "string" ||
    typeof rawResponse.approachId !== "string" ||
    !Array.isArray(rawResponse.hints)
  ) {
    throw new Error("Invalid approach hints response.");
  }

  return {
    slug: rawResponse.slug,
    approachId: rawResponse.approachId,
    hints: rawResponse.hints.map(String)
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
