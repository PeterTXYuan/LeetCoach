import type { ApproachHintsResponse } from "./api/approachHints";
import { starterCodePolicyVersion, type GuidanceLevel, type StarterCodeBatchResponse } from "./api/starterCode";
import { type ApproachSolutionResponse, type SolutionLanguage } from "./api/approachSolution";
import type { SectionId } from "./components/SectionNav";
import { normalizeGuidanceBundle, type GuidanceBundle } from "./api/guidanceBundle";

export const workspaceStorageKey = "leetcoach-workspaces-v1";

export type SavedHints = {
  response: ApproachHintsResponse;
  visibleHintCount: number;
};

export type SavedStarter = {
  language: SolutionLanguage;
  level: GuidanceLevel;
  isExpanded: boolean;
  isVisible: boolean;
  batches: Record<string, StarterCodeBatchResponse>;
};

export function emptyStarter(): SavedStarter {
  return { language: "python", level: 1, isExpanded: false, isVisible: false, batches: {} };
}

export function starterBatchKey(language: SolutionLanguage): string {
  return `${language}:${starterCodePolicyVersion}`;
}

export const solutionPolicyVersion = 1;

export type SavedSolution = {
  policyVersion: number;
  language: SolutionLanguage;
  visibleByLanguage: Partial<Record<SolutionLanguage, boolean>>;
  responses: Partial<Record<SolutionLanguage, ApproachSolutionResponse>>;
};

export function emptySolution(): SavedSolution {
  return { policyVersion: solutionPolicyVersion, language: "python", visibleByLanguage: {}, responses: {} };
}

export type CoachWorkspace = {
  selectedApproachId: string | null;
  isThinkingExpanded: boolean;
  activeSection: SectionId;
  hintsByApproach: Record<string, SavedHints>;
  starterByApproach: Record<string, SavedStarter>;
  solutionByApproach: Record<string, SavedSolution>;
  guidanceByApproach?: Record<string, Partial<Record<SolutionLanguage, GuidanceBundle>>>;
  recognitionRevealedByApproach: Record<string, boolean>;
  disclosureRevision: number;
};

export type CoachWorkspaces = Record<string, CoachWorkspace>;

const canonicalKey = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const sections: readonly SectionId[] = ["coach", "practice", "progress", "about"];

export function emptyWorkspace(): CoachWorkspace {
  return {
    selectedApproachId: null,
    isThinkingExpanded: false,
    activeSection: "coach",
    hintsByApproach: {},
    starterByApproach: {},
    solutionByApproach: {},
    guidanceByApproach: {},
    recognitionRevealedByApproach: {},
    disclosureRevision: 0
  };
}

/** Hide guidance without deleting generated responses or user choices. */
export function collapseWorkspaceDisclosure(workspace: CoachWorkspace): CoachWorkspace {
  return {
    ...workspace,
    isThinkingExpanded: false,
    hintsByApproach: Object.fromEntries(Object.entries(workspace.hintsByApproach).map(
      ([id, saved]) => [id, { ...saved, visibleHintCount: 0 }]
    )),
    starterByApproach: Object.fromEntries(Object.entries(workspace.starterByApproach).map(
      ([id, saved]) => [id, { ...saved, isExpanded: false, isVisible: false }]
    )),
    solutionByApproach: Object.fromEntries(Object.entries(workspace.solutionByApproach).map(
      ([id, saved]) => [id, { ...saved, visibleByLanguage: {} }]
    )),
    recognitionRevealedByApproach: {},
    disclosureRevision: workspace.disclosureRevision + 1
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseSavedHints(value: unknown, slug: string, approachId: string): SavedHints | null {
  if (!isRecord(value) || !isRecord(value.response)) return null;
  const response = value.response;
  if (
    response.slug !== slug || response.approachId !== approachId ||
    !Array.isArray(response.hints) || response.hints.length === 0 ||
    response.hints.length > 3 ||
    !response.hints.every((hint) => typeof hint === "string" && hint.trim().length > 0) ||
    !Number.isInteger(value.visibleHintCount) ||
    (value.visibleHintCount as number) < 0 ||
    (value.visibleHintCount as number) > response.hints.length
  ) return null;
  return {
    response: { slug, approachId, hints: [...response.hints] as string[] },
    visibleHintCount: 0
  };
}

function parseSavedStarter(value: unknown): SavedStarter | null {
  if (!isRecord(value) ||
      !["python", "java", "javascript", "cpp"].includes(value.language as string) ||
      ![1, 2, 3].includes(value.level as number) ||
      typeof value.isExpanded !== "boolean" || typeof value.isVisible !== "boolean") return null;
  // Policy 8 starter batches have no lineage to a Policy 9 answer.
  const batches: Record<string, StarterCodeBatchResponse> = {};
  return {
    language: value.language as SolutionLanguage, level: value.level as GuidanceLevel,
    isExpanded: false,
    isVisible: false,
    batches
  };
}

function parseSavedSolution(value: unknown): SavedSolution | null {
  if (!isRecord(value) || value.policyVersion !== solutionPolicyVersion ||
      !["python", "java", "javascript", "cpp"].includes(value.language as string) ||
      !isRecord(value.responses) || !isRecord(value.visibleByLanguage)) return null;
  // Standalone answers cannot prove that they complete a Policy 9 scaffold.
  const responses: SavedSolution["responses"] = {};
  return { policyVersion: solutionPolicyVersion, language: value.language as SolutionLanguage,
    visibleByLanguage: {}, responses };
}

function parseWorkspace(value: unknown, slug: string): CoachWorkspace | null {
  if (!isRecord(value) || !isRecord(value.hintsByApproach)) return null;
  if (value.selectedApproachId !== null &&
      (typeof value.selectedApproachId !== "string" ||
       !canonicalKey.test(value.selectedApproachId))) return null;
  if (typeof value.isThinkingExpanded !== "boolean" ||
      !sections.includes(value.activeSection as SectionId)) return null;

  const hintsByApproach: Record<string, SavedHints> = {};
  for (const [approachId, saved] of Object.entries(value.hintsByApproach)) {
    if (!canonicalKey.test(approachId)) return null;
    const parsed = parseSavedHints(saved, slug, approachId);
    if (!parsed) return null;
    hintsByApproach[approachId] = parsed;
  }
  const starterByApproach: Record<string, SavedStarter> = {};
  // Existing v1 workspaces predate starter caching; absence is a valid migration.
  if (value.starterByApproach !== undefined && isRecord(value.starterByApproach)) {
    for (const [approachId, saved] of Object.entries(value.starterByApproach)) {
      if (!canonicalKey.test(approachId)) continue;
      const parsed = parseSavedStarter(saved);
      if (parsed) starterByApproach[approachId] = parsed;
    }
  }
  const solutionByApproach: Record<string, SavedSolution> = {};
  if (value.solutionByApproach !== undefined && isRecord(value.solutionByApproach)) {
    for (const [approachId, saved] of Object.entries(value.solutionByApproach)) {
      if (!canonicalKey.test(approachId)) continue;
      const parsed = parseSavedSolution(saved);
      if (parsed) solutionByApproach[approachId] = parsed;
    }
  }
  const guidanceByApproach: NonNullable<CoachWorkspace["guidanceByApproach"]> = {};
  if (isRecord(value.guidanceByApproach)) {
    for (const [approachId, languages] of Object.entries(value.guidanceByApproach)) {
      if (!canonicalKey.test(approachId) || !isRecord(languages)) continue;
      const valid: Partial<Record<SolutionLanguage, GuidanceBundle>> = {};
      for (const language of ["python", "java", "javascript", "cpp"] as const) {
        try {
          if (languages[language] === undefined) continue;
          const bundle = normalizeGuidanceBundle(languages[language]);
          if (bundle.slug === slug && bundle.approachId === approachId && bundle.language === language)
            valid[language] = bundle;
        } catch { /* Discard only this corrupt or old-policy entry. */ }
      }
      if (Object.keys(valid).length) guidanceByApproach[approachId] = valid;
    }
  }
  return {
    selectedApproachId: value.selectedApproachId as string | null,
    isThinkingExpanded: false,
    activeSection: value.activeSection as SectionId,
    hintsByApproach,
    starterByApproach,
    solutionByApproach,
    guidanceByApproach,
    recognitionRevealedByApproach: {},
    disclosureRevision: 0
  };
}

export function parseWorkspaces(value: unknown): CoachWorkspaces {
  if (!isRecord(value)) return {};
  const workspaces: CoachWorkspaces = {};
  for (const [slug, saved] of Object.entries(value)) {
    if (!canonicalKey.test(slug)) continue;
    const parsed = parseWorkspace(saved, slug);
    if (parsed) workspaces[slug] = parsed;
  }
  return workspaces;
}

function storageArea() {
  try {
    return typeof chrome !== "undefined" ? chrome.storage?.local : undefined;
  } catch {
    return undefined;
  }
}

export type WorkspaceLoad = { workspaces: CoachWorkspaces; canPersist: boolean };

export async function loadWorkspaces(): Promise<WorkspaceLoad> {
  const storage = storageArea();
  if (!storage) return { workspaces: {}, canPersist: false };
  try {
    await pendingWrite.catch(() => {});
    const result = await storage.get(workspaceStorageKey);
    return { workspaces: parseWorkspaces(result[workspaceStorageKey]), canPersist: true };
  } catch {
    return { workspaces: {}, canPersist: false };
  }
}

let pendingWrite: Promise<void> = Promise.resolve();

export function saveWorkspaces(workspaces: CoachWorkspaces): void {
  const storage = storageArea();
  if (!storage) return;
  // Persist content and choices, never the open panel's disclosure state.
  const persistent = Object.fromEntries(Object.entries(workspaces).map(([slug, workspace]) => {
    const collapsed = collapseWorkspaceDisclosure(workspace);
    const { recognitionRevealedByApproach: _recognition, disclosureRevision: _revision,
      ...saved } = collapsed;
    return [slug, saved];
  }));
  // Serialize whole-map writes so a slower older write cannot replace newer state.
  pendingWrite = pendingWrite.catch(() => {}).then(async () => {
    await storage.set({ [workspaceStorageKey]: persistent });
  });
  void pendingWrite.catch(() => {});
}
