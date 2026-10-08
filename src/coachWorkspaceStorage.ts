import type { ApproachHintsResponse } from "./api/approachHints";
import { normalizeStarterCode, type GuidanceLevel, type StarterCodeResponse } from "./api/starterCode";
import type { SolutionLanguage } from "./api/approachSolution";
import type { SectionId } from "./components/SectionNav";

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
  responses: Record<string, StarterCodeResponse>;
};

export function emptyStarter(): SavedStarter {
  return { language: "python", level: 1, isExpanded: false, isVisible: false, responses: {} };
}

export function starterResponseKey(language: SolutionLanguage, level: GuidanceLevel): string {
  return `${language}:${level}`;
}

export type CoachWorkspace = {
  selectedApproachId: string | null;
  isThinkingExpanded: boolean;
  activeSection: SectionId;
  hintsByApproach: Record<string, SavedHints>;
  starterByApproach: Record<string, SavedStarter>;
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
    starterByApproach: {}
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
    visibleHintCount: value.visibleHintCount as number
  };
}

function parseSavedStarter(value: unknown, slug: string, approachId: string): SavedStarter | null {
  if (!isRecord(value) || !isRecord(value.responses) ||
      !["python", "java", "javascript", "cpp"].includes(value.language as string) ||
      ![1, 2, 3].includes(value.level as number) ||
      typeof value.isExpanded !== "boolean" || typeof value.isVisible !== "boolean") return null;
  const responses: Record<string, StarterCodeResponse> = {};
  for (const [key, saved] of Object.entries(value.responses)) {
    try {
      const response = normalizeStarterCode(saved);
      if (response.slug !== slug || response.approachId !== approachId ||
          key !== starterResponseKey(response.language, response.level)) continue;
      responses[key] = response;
    } catch { /* Drop one corrupted cache entry, keep the rest of the workspace. */ }
  }
  return {
    language: value.language as SolutionLanguage, level: value.level as GuidanceLevel,
    isExpanded: value.isExpanded, isVisible: value.isVisible, responses
  };
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
      const parsed = parseSavedStarter(saved, slug, approachId);
      if (parsed) starterByApproach[approachId] = parsed;
    }
  }
  return {
    selectedApproachId: value.selectedApproachId as string | null,
    isThinkingExpanded: value.isThinkingExpanded,
    activeSection: value.activeSection as SectionId,
    hintsByApproach,
    starterByApproach
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
  // Serialize whole-map writes so a slower older write cannot replace newer state.
  pendingWrite = pendingWrite.catch(() => {}).then(async () => {
    await storage.set({ [workspaceStorageKey]: workspaces });
  });
  void pendingWrite.catch(() => {});
}
