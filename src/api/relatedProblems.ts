export type RelatedProblem = {
  slug: string;
  title: string;
  difficulty: "Easy" | "Medium" | "Hard";
  reason?: string;
};

export type RelatedProblemsResponse = {
  slug: string;
  easier: RelatedProblem[];
  similar: RelatedProblem[];
  harder: RelatedProblem[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeGroup(value: unknown): RelatedProblem[] {
  if (!Array.isArray(value)) throw new Error("Invalid related problems group.");
  return value.map((problem) => {
    if (!isRecord(problem) || typeof problem.slug !== "string" ||
      !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(problem.slug) ||
      typeof problem.title !== "string" || !problem.title.trim() ||
      !["Easy", "Medium", "Hard"].includes(problem.difficulty as string) ||
      (problem.reason !== undefined && typeof problem.reason !== "string")) {
      throw new Error("Invalid related problem.");
    }
    return {
      slug: problem.slug, title: problem.title,
      difficulty: problem.difficulty as RelatedProblem["difficulty"],
      ...(problem.reason !== undefined ? { reason: problem.reason as string } : {})
    };
  });
}

export async function fetchRelatedProblems(slug: string, signal?: AbortSignal): Promise<RelatedProblemsResponse | null> {
  const response = await fetch(`http://localhost:8000/api/problems/${encodeURIComponent(slug)}/related`, { signal });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Related problems request failed: ${response.status}`);
  const data: unknown = await response.json();
  if (!isRecord(data) || data.slug !== slug) throw new Error("Related problems do not match the current problem.");
  return { slug, easier: normalizeGroup(data.easier), similar: normalizeGroup(data.similar), harder: normalizeGroup(data.harder) };
}
