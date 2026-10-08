import type { SolutionLanguage } from "./approachSolution";

export type GuidanceLevel = 1 | 2 | 3;
export type StarterCodeResponse = {
  slug: string;
  approachId: string;
  language: SolutionLanguage;
  level: GuidanceLevel;
  levelName: string;
  isAiGenerated: boolean;
  usedFallback?: boolean;
  code: string;
  notice: string;
};

export class InvalidStarterOptionsError extends Error {}

export async function fetchStarterCode(
  slug: string,
  approachId: string,
  language: SolutionLanguage,
  level: GuidanceLevel,
  signal?: AbortSignal
): Promise<StarterCodeResponse | null> {
  const response = await fetch(
    `http://localhost:8000/api/problems/${encodeURIComponent(slug)}/approaches/${encodeURIComponent(approachId)}/starter-code`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language, level }),
      signal
    }
  );
  if (response.status === 404) return null;
  if (response.status === 400 || response.status === 422) {
    throw new InvalidStarterOptionsError("Unsupported starter code options.");
  }
  if (!response.ok) throw new Error(`Starter code request failed: ${response.status}`);
  const result = normalizeStarterCode(await response.json());
  if (
    result.slug !== slug || result.approachId !== approachId ||
    result.language !== language || result.level !== level
  ) throw new Error("Starter code does not match the requested context.");
  return result;
}

export function normalizeStarterCode(value: unknown): StarterCodeResponse {
  if (typeof value !== "object" || value === null) throw new Error("Invalid starter code response.");
  const data = value as Record<string, unknown>;
  if (
    typeof data.slug !== "string" || typeof data.approachId !== "string" ||
    !["python", "java", "javascript", "cpp"].includes(data.language as string) ||
    ![1, 2, 3].includes(data.level as number) ||
    typeof data.levelName !== "string" || typeof data.isAiGenerated !== "boolean" ||
    typeof data.code !== "string" || !data.code.trim() || typeof data.notice !== "string" ||
    (data.usedFallback !== undefined && typeof data.usedFallback !== "boolean")
  ) throw new Error("Invalid starter code response.");
  return data as StarterCodeResponse;
}
