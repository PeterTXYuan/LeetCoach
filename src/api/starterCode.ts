import type { SolutionLanguage } from "./approachSolution";

export type GuidanceLevel = 1 | 2 | 3;
export const starterCodePolicyVersion = 8;
export type StarterCodeBatchResponse = {
  slug: string;
  approachId: string;
  language: SolutionLanguage;
  policyVersion: number;
  isAiGenerated: boolean;
  usedFallback?: boolean;
  notice: string;
  level1: string;
  level2: string;
  level3: string;
};

export async function fetchStarterCodeBatch(
  slug: string, approachId: string, language: SolutionLanguage, signal?: AbortSignal
): Promise<StarterCodeBatchResponse | null> {
  const response = await fetch(
    `http://localhost:8000/api/problems/${encodeURIComponent(slug)}/approaches/${encodeURIComponent(approachId)}/starter-code/batch`,
    { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language }), signal }
  );
  if (response.status === 404) return null;
  if (response.status === 400 || response.status === 422) {
    throw new InvalidStarterOptionsError("Unsupported starter code options.");
  }
  if (!response.ok) throw new Error(`Starter code request failed: ${response.status}`);
  const batch = normalizeStarterCodeBatch(await response.json());
  if (batch.slug !== slug || batch.approachId !== approachId || batch.language !== language) {
    throw new Error("Starter code does not match the requested context.");
  }
  return batch;
}

export function normalizeStarterCodeBatch(value: unknown): StarterCodeBatchResponse {
  if (typeof value !== "object" || value === null) throw new Error("Invalid starter code batch.");
  const data = value as Record<string, unknown>;
  if (typeof data.slug !== "string" || typeof data.approachId !== "string" ||
      !["python", "java", "javascript", "cpp"].includes(data.language as string) ||
      data.policyVersion !== starterCodePolicyVersion || typeof data.isAiGenerated !== "boolean" ||
      typeof data.notice !== "string" ||
      (data.usedFallback !== undefined && typeof data.usedFallback !== "boolean") ||
      ![data.level1, data.level2, data.level3].every((code) => typeof code === "string" && code.trim())) {
    throw new Error("Invalid starter code batch.");
  }
  if (new Set([data.level1, data.level2, data.level3]).size !== 3) throw new Error("Invalid starter code batch.");
  return data as StarterCodeBatchResponse;
}

export function starterLevel(batch: StarterCodeBatchResponse, level: GuidanceLevel): StarterCodeResponse {
  return { ...batch, level, levelName: ["", "Kickstart", "Guided", "Strong Scaffold"][level],
    code: batch[`level${level}`] };
}
export type StarterCodeResponse = {
  slug: string;
  approachId: string;
  language: SolutionLanguage;
  level: GuidanceLevel;
  levelName: string;
  isAiGenerated: boolean;
  usedFallback?: boolean;
  policyVersion?: number;
  code: string;
  notice: string;
};

export class InvalidStarterOptionsError extends Error {}
