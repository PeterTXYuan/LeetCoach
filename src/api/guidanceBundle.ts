import type { SolutionLanguage } from "./approachSolution";

export const linkedGuidancePolicyVersion = 9;
export type GuidanceWarning = {
  scope: "level1" | "level2" | "level3" | "solution" | "bundle";
  code: string;
  message: string;
};
export type GuidanceBundle = {
  slug: string; approachId: string; language: SolutionLanguage;
  policyVersion: 9; generationId: string; kind: "linked" | "starterOnlyMock";
  isAiGenerated: boolean; notice: string;
  level1: string; level2: string; level3: string;
  solution: null | { code: string; explanation: string; timeComplexity: string; spaceComplexity: string };
  verification: { status: "PASS" | "FAIL" | "NOT_RUN"; summary: string };
  warnings?: GuidanceWarning[];
  usage?: null | { promptTokens: number | null; completionTokens: number | null;
    totalTokens: number | null; latencyMs: number; outputChars: number; finishReason: string | null };
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export function normalizeGuidanceBundle(value: unknown): GuidanceBundle {
  if (!isRecord(value) || value.policyVersion !== linkedGuidancePolicyVersion ||
      typeof value.generationId !== "string" || !value.generationId ||
      typeof value.slug !== "string" || typeof value.approachId !== "string" ||
      !["python", "java", "javascript", "cpp"].includes(value.language as string) ||
      !["linked", "starterOnlyMock"].includes(value.kind as string) ||
      typeof value.isAiGenerated !== "boolean" || typeof value.notice !== "string" ||
      ![value.level1, value.level2, value.level3].every(
        (code) => typeof code === "string" && Boolean(code.trim())) ||
      !isRecord(value.verification) ||
      !["PASS", "FAIL", "NOT_RUN"].includes(value.verification.status as string) ||
      typeof value.verification.summary !== "string") throw new Error("Invalid linked guidance bundle.");
  if (value.kind === "linked" && (!isRecord(value.solution) || !value.isAiGenerated))
    throw new Error("Linked answer is missing.");
  if (value.solution !== null && (!isRecord(value.solution) ||
      !["code", "explanation", "timeComplexity", "spaceComplexity"].every(
        (key) => typeof (value.solution as Record<string, unknown>)[key] === "string" &&
          Boolean(((value.solution as Record<string, unknown>)[key] as string).trim()))))
    throw new Error("Invalid linked answer.");
  if (value.warnings !== undefined && (!Array.isArray(value.warnings) ||
      value.warnings.length > 32 || value.warnings.some((warning) =>
        !isRecord(warning) ||
        !["level1", "level2", "level3", "solution", "bundle"].includes(warning.scope as string) ||
        typeof warning.code !== "string" || !warning.code ||
        typeof warning.message !== "string" || !warning.message || warning.message.length > 300)))
    throw new Error("Invalid guidance warnings.");
  return value as GuidanceBundle;
}

export async function fetchGuidanceBundle(slug: string, approachId: string,
  language: SolutionLanguage, signal?: AbortSignal): Promise<GuidanceBundle | null> {
  const response = await fetch(
    `http://localhost:8000/api/problems/${encodeURIComponent(slug)}/approaches/${encodeURIComponent(approachId)}/guidance`,
    { method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language }), signal }
  );
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Guidance request failed: ${response.status}`);
  const result = normalizeGuidanceBundle(await response.json());
  if (result.slug !== slug || result.approachId !== approachId || result.language !== language)
    throw new Error("Guidance response did not match the requested context.");
  return result;
}
