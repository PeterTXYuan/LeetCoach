// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../src/App";
import { parseWorkspaces, solutionPolicyVersion, workspaceStorageKey } from "../src/coachWorkspaceStorage";

const json = (data: unknown) => ({ ok: true, status: 200, json: async () => data } as Response);
const fetchMock = vi.fn();
let disk: Record<string, unknown>;
let currentUrl: string;
let currentTabId: number;
let storageGet: ReturnType<typeof vi.fn>;
let storageSet: ReturnType<typeof vi.fn>;

const catalogs = {
  "two-sum": [
    { id: "brute-force", name: "Brute Force", isPrimary: false },
    { id: "hash-map", name: "Hash Map", isPrimary: true }
  ],
  "valid-parentheses": [
    { id: "stack", name: "Stack", isPrimary: true }
  ]
};

function hintRequests() {
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/hints")).length;
}

function starterRequests() {
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/guidance")).length;
}

function starter(slug = "two-sum", approachId = "hash-map", language = "python", codes?: string[]) {
  return { slug, approachId, language, policyVersion: 8, isAiGenerated: false, usedFallback: false,
    notice: "Complete the TODOs.", ...Object.fromEntries([1, 2, 3].map((level) => [
      `level${level}`, codes?.[level - 1] ?? `// TODO: ${slug} ${approachId} ${language} ${level}`
    ])) };
}

function solutionRequests() {
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/guidance")).length;
}

function bundle(slug: string, approachId: string, language: string, codes?: string[]) {
  const scaffold = starter(slug, approachId, language, codes);
  const answer = solution(slug, approachId, language);
  return { ...scaffold, policyVersion: 9, generationId: `${slug}-${approachId}-${language}`,
    kind: "linked", isAiGenerated: true,
    solution: { code: answer.code, explanation: answer.explanation,
      timeComplexity: answer.timeComplexity, spaceComplexity: answer.spaceComplexity },
    verification: { status: "NOT_RUN", summary: "Test fixture" } };
}

function solution(slug: string, approachId: string, language: string) {
  return { slug, approachId, language, isAiGenerated: true,
    warning: "Full solution revealed. Try solving the problem yourself first.",
    code: `${slug} ${approachId} ${language} full solution`, explanation: "How the approach works.",
    timeComplexity: "O(n)", spaceComplexity: "O(n)" };
}

function storedWorkspace(slug: string) {
  return (disk[workspaceStorageKey] as Record<string, any> | undefined)?.[slug];
}

beforeEach(() => {
  localStorage.setItem("leetcoach-theme", "light");
  disk = {};
  currentUrl = "https://leetcode.com/problems/two-sum/";
  currentTabId = 1;
  storageGet = vi.fn(async (key: string) => ({ [key]: disk[key] }));
  storageSet = vi.fn(async (items: Record<string, unknown>) => {
    Object.assign(disk, structuredClone(items));
  });
  const activated = { addListener: vi.fn(), removeListener: vi.fn() };
  const updated = { addListener: vi.fn(), removeListener: vi.fn() };
  vi.stubGlobal("chrome", {
    tabs: {
      query: vi.fn(async () => [{
        id: currentTabId,
        url: currentUrl,
        title: currentUrl.includes("valid-parentheses")
          ? "Valid Parentheses - LeetCode" : "Two Sum - LeetCode"
      }]),
      onActivated: activated, onUpdated: updated
    },
    storage: { local: { get: storageGet, set: storageSet } }
  });
  fetchMock.mockReset().mockImplementation(async (url: string) => {
    const path = new URL(url).pathname;
    const parts = path.split("/");
    const slug = parts[3] as keyof typeof catalogs;
    if (path.endsWith("/hints")) {
      const approachId = parts.includes("approaches")
        ? parts[5]
        : catalogs[slug].find((approach) => approach.isPrimary)!.id;
      return json({
        slug, approachId,
        hints: [1, 2, 3].map((index) => `${slug} ${approachId} hint ${index}`)
      });
    }
    if (path.endsWith("/related")) {
      return json({ slug, easier: [], similar: [], harder: [] });
    }
    if (path.endsWith("/guidance")) {
      const body = JSON.parse(fetchMock.mock.lastCall![1].body as string);
      return json(bundle(slug, parts[5], body.language));
    }
    if (path.endsWith("/solution")) {
      const body = JSON.parse(fetchMock.mock.lastCall![1].body as string);
      return json(solution(slug, parts[5], body.language));
    }
    return json({
      slug,
      approaches: catalogs[slug].map((approach, index) => ({
        ...approach, pattern: approach.name, summary: "Summary",
        displayOrder: index + 1, thinkingSteps: [`Think about ${approach.id}`],
        recognitionSignals: { quote: "problem clue", bullets: [`Recognize ${slug} ${approach.id}`] }
      }))
    });
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

async function mount() {
  const view = render(<App />);
  await screen.findByRole("button", { name: "Approach 1" });
  return view;
}

async function activate(url: string, tabId = url.includes("two-sum") ? 1 : url.includes("valid-parentheses") ? 2 : 3) {
  currentUrl = url;
  currentTabId = tabId;
  const refresh = vi.mocked(chrome.tabs.onActivated.addListener).mock.calls[0][0];
  await act(async () => {
    refresh({ tabId, windowId: 1 });
    await Promise.resolve();
  });
}

async function navigate(url: string, tabId = currentTabId) {
  currentUrl = url;
  const refresh = vi.mocked(chrome.tabs.onUpdated.addListener).mock.calls[0][0];
  await act(async () => {
    refresh(tabId, { status: "complete", url }, { id: tabId, url } as chrome.tabs.Tab);
    await Promise.resolve();
  });
}

function click(name: string) {
  fireEvent.click(screen.getByRole("button", { name, exact: true }));
}

function section(name: string) {
  fireEvent.click(screen.getByRole("tab", { name, exact: true }));
}

describe("persistent Coach workspaces", () => {
  it("shows soft warnings beside the affected level and answer, then clears them on regeneration", async () => {
    await mount();
    click("Approach 2");
    fetchMock.mockImplementationOnce(() => json({
      ...bundle("two-sum", "hash-map", "python"),
      warnings: [
        { scope: "level1", code: "NO_USEFUL_SETUP", message: "Level 1 is very minimal." },
        { scope: "solution", code: "CORRECTNESS_FIXTURE_FAILED", message: "The answer failed sample checks." }
      ],
      verification: { status: "FAIL", summary: "2/4 fixtures passed" }
    }));
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("Level 1 is very minimal.");
    expect(screen.queryByText("The answer failed sample checks.")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Level 2/ }));
    expect(screen.queryByText("Level 1 is very minimal.")).toBeNull();
    click("Generate answer in Python");
    await screen.findByText("The answer failed sample checks.");
    expect(screen.getByText(/Representative checks: failed/)).toBeTruthy();
    click("Regenerate answer");
    await waitFor(() => expect(screen.queryByText("The answer failed sample checks.")).toBeNull());
    expect(starterRequests()).toBe(2);
  });

  it("shares one Policy 9 bundle between Starter Code and the hidden full answer", async () => {
    await mount();
    click("Approach 2");
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map python 1");
    expect(screen.queryByRole("article", { name: "Generated answer" })).toBeNull();
    expect(starterRequests()).toBe(1);
    fireEvent.click(screen.getByRole("button", { name: /Level 2/ }));
    expect(screen.getByText("// TODO: two-sum hash-map python 2")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Level 3/ }));
    expect(screen.getByText("// TODO: two-sum hash-map python 3")).toBeTruthy();
    expect(starterRequests()).toBe(1);
    click("Generate answer in Python");
    await screen.findByText("two-sum hash-map python full solution");
    expect(starterRequests()).toBe(1);
    await waitFor(() => expect(storedWorkspace("two-sum")?.guidanceByApproach["hash-map"].python.policyVersion).toBe(9));
    expect(storedWorkspace("two-sum")?.starterByApproach["hash-map"].batches).toEqual({});
    expect(storedWorkspace("two-sum")?.solutionByApproach["hash-map"].responses).toEqual({});
  });

  it("joins simultaneous Starter and Answer clicks to one pending request", async () => {
    await mount();
    click("Approach 2");
    let resolve!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    click("Get starter code");
    click("Generate Starter Code");
    click("Generate answer in Python");
    expect(starterRequests()).toBe(1);
    await act(async () => resolve(json(bundle("two-sum", "hash-map", "python"))));
    expect(await screen.findByText("// TODO: two-sum hash-map python 1")).toBeTruthy();
    expect(screen.getByText("two-sum hash-map python full solution")).toBeTruthy();
  });

  it("hiding Starter Code during generation keeps other guidance intact", async () => {
    await mount();
    click("Approach 2");
    let resolve!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    click("Get starter code");
    click("Generate Starter Code");
    click("Hide starter code");
    await act(async () => resolve(json(bundle("two-sum", "hash-map", "python"))));
    expect(screen.queryByText("// TODO: two-sum hash-map python 1")).toBeNull();
    click("Generate answer in Python");
    expect(screen.getByText("two-sum hash-map python full solution")).toBeTruthy();
    expect(starterRequests()).toBe(1);
    click("Generate Starter Code");
    expect(screen.getByText("// TODO: two-sum hash-map python 1")).toBeTruthy();
    expect(starterRequests()).toBe(1);
  });

  it("atomically replaces all four outputs from either Regenerate button", async () => {
    await mount();
    click("Approach 2");
    click("Generate answer in Python");
    await screen.findByText("two-sum hash-map python full solution");
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map python 1");
    const firstId = storedWorkspace("two-sum")?.guidanceByApproach["hash-map"].python.generationId;
    let resolve!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    click("Regenerate starter code");
    expect((screen.getByRole("button", { name: "Regenerating starter code..." }) as HTMLButtonElement).disabled).toBe(true);
    await act(async () => resolve(json({ ...bundle("two-sum", "hash-map", "python",
      ["New L1", "New L2", "New L3"]), generationId: "replacement", solution: {
      code: "New full answer", explanation: "New explanation", timeComplexity: "O(n)", spaceComplexity: "O(n)"
    } })));
    await screen.findByText("New L1");
    expect(screen.getByText("New full answer")).toBeTruthy();
    expect(storedWorkspace("two-sum")?.guidanceByApproach["hash-map"].python.generationId).not.toBe(firstId);
    click("Regenerate answer");
    await screen.findByText("two-sum hash-map python full solution");
    expect(screen.getByText("// TODO: two-sum hash-map python 1")).toBeTruthy();
    expect(starterRequests()).toBe(3);
  });

  it("retains the previous bundle and both visible sections after a failed regeneration", async () => {
    await mount();
    click("Approach 2");
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map python 1");
    click("Generate answer in Python");
    await screen.findByText("two-sum hash-map python full solution");
    const old = structuredClone(storedWorkspace("two-sum")?.guidanceByApproach["hash-map"].python);
    fetchMock.mockRejectedValueOnce(new Error("Offline"));
    click("Regenerate starter code");
    await screen.findByText(/Unable to regenerate starter code/);
    expect(screen.getByText("// TODO: two-sum hash-map python 1")).toBeTruthy();
    expect(screen.getByText("two-sum hash-map python full solution")).toBeTruthy();
    expect(storedWorkspace("two-sum")?.guidanceByApproach["hash-map"].python).toEqual(old);
  });

  it("keeps languages independent and does not auto-request on language or level changes", async () => {
    await mount();
    click("Approach 2");
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map python 1");
    fireEvent.change(screen.getByLabelText("Starter language"), { target: { value: "java" } });
    expect(screen.queryByText("// TODO: two-sum hash-map python 1")).toBeNull();
    expect(starterRequests()).toBe(1);
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map java 1");
    expect(starterRequests()).toBe(2);
    fireEvent.change(screen.getByLabelText("Starter language"), { target: { value: "python" } });
    expect(screen.getByText("// TODO: two-sum hash-map python 1")).toBeTruthy();
    click("Generate answer in Python");
    await screen.findByText("two-sum hash-map python full solution");
    expect(starterRequests()).toBe(2);
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "java" } });
    expect(screen.queryByText("two-sum hash-map python full solution")).toBeNull();
    expect(starterRequests()).toBe(2);
    click("Generate answer in Java");
    await screen.findByText("two-sum hash-map java full solution");
    expect(starterRequests()).toBe(2);
  });

  it("invalidates old independent caches while retaining hints, selection, and preferences", async () => {
    const original = {
      ...parseWorkspaces({})["two-sum"],
      selectedApproachId: "hash-map", isThinkingExpanded: false, activeSection: "coach",
      hintsByApproach: { "hash-map": { response: { slug: "two-sum", approachId: "hash-map",
        hints: ["Saved hint"] }, visibleHintCount: 1 } },
      starterByApproach: { "hash-map": { language: "java", level: 2, isExpanded: true,
        isVisible: true, batches: { "java:8": starter("two-sum", "hash-map", "java") } } },
      solutionByApproach: { "hash-map": { policyVersion: solutionPolicyVersion, language: "cpp",
        visibleByLanguage: { cpp: true }, responses: { cpp: solution("two-sum", "hash-map", "cpp") } } }
    };
    const parsed = parseWorkspaces({ "two-sum": original })["two-sum"];
    expect(parsed.selectedApproachId).toBe("hash-map");
    expect(parsed.hintsByApproach["hash-map"].response.hints).toEqual(["Saved hint"]);
    expect(parsed.starterByApproach["hash-map"]).toMatchObject({ language: "java", level: 2, batches: {} });
    expect(parsed.solutionByApproach["hash-map"]).toMatchObject({ language: "cpp", responses: {} });
    expect(parsed.guidanceByApproach).toEqual({});
  });

  it("hydrates only complete Policy 9 bundles and never reveals them on remount", async () => {
    disk[workspaceStorageKey] = { "two-sum": {
      selectedApproachId: "hash-map", isThinkingExpanded: false, activeSection: "coach",
      hintsByApproach: {}, starterByApproach: { "hash-map": { language: "python", level: 1,
        isExpanded: true, isVisible: true, batches: {} } },
      solutionByApproach: { "hash-map": { policyVersion: solutionPolicyVersion, language: "python",
        visibleByLanguage: { python: true }, responses: {} } },
      guidanceByApproach: { "hash-map": { python: bundle("two-sum", "hash-map", "python"),
        java: { ...bundle("two-sum", "hash-map", "java"), policyVersion: 8 } } }
    } };
    expect(parseWorkspaces(disk[workspaceStorageKey])["two-sum"].guidanceByApproach?.["hash-map"].java)
      .toBeUndefined();
    await mount();
    expect(screen.queryByText("// TODO: two-sum hash-map python 1")).toBeNull();
    expect(screen.queryByText("two-sum hash-map python full solution")).toBeNull();
    click("Get starter code");
    click("Generate Starter Code");
    expect(screen.getByText("// TODO: two-sum hash-map python 1")).toBeTruthy();
    click("Generate answer in Python");
    expect(screen.getByText("two-sum hash-map python full solution")).toBeTruthy();
    expect(starterRequests()).toBe(0);
  });
  it("keeps Coach disclosure and section across extension and browser tab switches", async () => {
    await mount();
    click("Approach 1");
    click("Get first hint");
    await screen.findByText("two-sum brute-force hint 1");
    click("Show next hint");
    expect(screen.getByText("two-sum brute-force hint 2")).toBeTruthy();
    click("Show thinking process");
    section("Practice");
    await screen.findByRole("heading", { name: "Easier" });
    expect(storedWorkspace("two-sum")?.activeSection).toBe("practice");
    section("Coach");
    expect(screen.getByText("two-sum brute-force hint 2")).toBeTruthy();
    expect(screen.getByText("Think about brute-force")).toBeTruthy();
    section("Practice");

    await activate("https://leetcode.com/problems/valid-parentheses/");
    await screen.findByRole("heading", { name: "Valid Parentheses" });
    expect(screen.getByRole("tab", { name: "Coach" }).getAttribute("aria-selected")).toBe("true");
    click("Get first hint");
    await screen.findByText("valid-parentheses stack hint 1");
    expect(hintRequests()).toBe(2);
    await waitFor(() => expect(storedWorkspace("valid-parentheses")?.hintsByApproach.stack).toBeTruthy());
    expect(storedWorkspace("two-sum")?.hintsByApproach["brute-force"].visibleHintCount).toBe(0);

    await activate("https://leetcode.com/problems/two-sum/");
    await waitFor(() => expect(screen.getByRole("tab", { name: "Practice" }).getAttribute("aria-selected")).toBe("true"));
    section("Coach");
    expect(screen.getByText("two-sum brute-force hint 2")).toBeTruthy();
    expect(screen.getByText("Think about brute-force")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Close selected approach" })).toBeTruthy();
    expect(hintRequests()).toBe(2);
  });

  it("reopens the side panel with selection and cache but no revealed guidance", async () => {
    const view = await mount();
    click("Approach 1");
    click("Get first hint");
    await screen.findByText("two-sum brute-force hint 1");
    click("Show next hint");
    click("Show thinking process");
    section("Practice");
    await waitFor(() => expect(storedWorkspace("two-sum")?.activeSection).toBe("practice"));
    await waitFor(() => expect(storedWorkspace("two-sum")?.hintsByApproach["brute-force"].visibleHintCount).toBe(0));
    view.unmount();

    render(<App />);
    await waitFor(() => expect(screen.getByRole("tab", { name: "Practice" }).getAttribute("aria-selected")).toBe("true"));
    section("Coach");
    expect(screen.queryByText("two-sum brute-force hint 2")).toBeNull();
    expect(screen.queryByText("Think about brute-force")).toBeNull();
    expect(screen.getByRole("button", { name: "Close selected approach" })).toBeTruthy();
    expect(hintRequests()).toBe(1);
    click("Get first hint");
    expect(screen.getByText("two-sum brute-force hint 1")).toBeTruthy();
    expect(hintRequests()).toBe(1);
    expect(storageGet).toHaveBeenCalledWith(workspaceStorageKey);
  });

  it("keeps generated batches separate from disclosure state and from other approaches", async () => {
    await mount();
    click("Get first hint");
    await screen.findByText("two-sum hash-map hint 1");
    click("Show next hint");
    click("Approach 1");
    click("Get first hint");
    await screen.findByText("two-sum brute-force hint 1");
    expect(hintRequests()).toBe(2);

    click("Reset revealed hints");
    expect(screen.queryByText("two-sum brute-force hint 1")).toBeNull();
    await waitFor(() => expect(storedWorkspace("two-sum")?.hintsByApproach["brute-force"].visibleHintCount).toBe(0));
    expect(storedWorkspace("two-sum")?.hintsByApproach["brute-force"].response.hints).toHaveLength(3);
    click("Get first hint");
    expect(screen.getByText("two-sum brute-force hint 1")).toBeTruthy();
    expect(hintRequests()).toBe(2);

    click("Close selected approach");
    expect(screen.queryByText("two-sum hash-map hint 2")).toBeNull();
    expect(screen.queryByText("two-sum brute-force hint 1")).toBeNull();
    await waitFor(() => expect(storedWorkspace("two-sum")?.hintsByApproach["brute-force"].visibleHintCount).toBe(0));
    click("Approach 1");
    expect(screen.queryByText("two-sum brute-force hint 1")).toBeNull();
    click("Get first hint");
    expect(screen.getByText("two-sum brute-force hint 1")).toBeTruthy();
    expect(hintRequests()).toBe(2);
  });

  it("keeps a same-problem workspace mounted through a non-LeetCode tab", async () => {
    await mount();
    click("Approach 1");
    click("Get first hint");
    await screen.findByText("two-sum brute-force hint 1");
    const coach = screen.getByRole("tabpanel", { name: "Coach" });
    await activate("https://example.com/");
    await screen.findByText("Open a LeetCode problem to use Coach and Practice.");
    expect(coach.isConnected).toBe(true);
    await activate("https://leetcode.com/problems/two-sum/");
    expect(screen.getByRole("tabpanel", { name: "Coach" })).toBe(coach);
    expect(screen.getByText("two-sum brute-force hint 1")).toBeTruthy();
    expect(hintRequests()).toBe(1);
  });

  it("preserves disclosures across browser tab switches between different problems", async () => {
    await mount();
    click("Approach 2");
    click("Get first hint");
    await screen.findByText("two-sum hash-map hint 1");
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map python 1");
    click("Generate answer in Python");
    await screen.findByText("two-sum hash-map python full solution");
    click("Reveal recognition signals");
    click("Show thinking process");

    await activate("https://leetcode.com/problems/valid-parentheses/");
    await screen.findByRole("heading", { name: "Valid Parentheses" });
    click("Get first hint");
    await screen.findByText("valid-parentheses stack hint 1");

    await activate("https://leetcode.com/problems/two-sum/");
    expect(screen.getByText("two-sum hash-map hint 1")).toBeTruthy();
    expect(screen.getByText("// TODO: two-sum hash-map python 1")).toBeTruthy();
    expect(screen.getByText("two-sum hash-map python full solution")).toBeTruthy();
    expect(screen.getByText("Recognize two-sum hash-map")).toBeTruthy();
    expect(screen.getByText("Think about hash-map")).toBeTruthy();
    expect([hintRequests(), starterRequests(), solutionRequests()]).toEqual([2, 1, 1]);
    await activate("https://leetcode.com/problems/valid-parentheses/");
    expect(screen.getByText("valid-parentheses stack hint 1")).toBeTruthy();
  });

  it("shares one slug's runtime disclosure across browser tabs but collapses it on panel remount", async () => {
    const view = await mount();
    click("Approach 2");
    click("Reveal recognition signals");
    expect(screen.getByText("Recognize two-sum hash-map")).toBeTruthy();
    await activate("https://leetcode.com/problems/two-sum/", 4);
    expect(screen.getByText("Recognize two-sum hash-map")).toBeTruthy();
    view.unmount();

    render(<App />);
    await screen.findByRole("button", { name: "Close selected approach" });
    expect(screen.queryByText("Recognize two-sum hash-map")).toBeNull();
    expect(screen.getByRole("button", { name: "Reveal recognition signals" })).toBeTruthy();
  });

  it("collapses on same-tab navigation and reload while keeping cached responses", async () => {
    await mount();
    click("Approach 2");
    click("Get first hint");
    await screen.findByText("two-sum hash-map hint 1");
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map python 1");
    click("Generate answer in Python");
    await screen.findByText("two-sum hash-map python full solution");
    click("Reveal recognition signals");
    click("Show thinking process");

    await navigate("https://leetcode.com/problems/valid-parentheses/", 1);
    await screen.findByRole("heading", { name: "Valid Parentheses" });
    await navigate("https://leetcode.com/problems/two-sum/", 1);
    await screen.findByRole("heading", { name: "Two Sum" });
    await waitFor(() => expect(screen.queryByText("two-sum hash-map hint 1")).toBeNull());
    expect(screen.queryByText("// TODO: two-sum hash-map python 1")).toBeNull();
    expect(screen.queryByText("two-sum hash-map python full solution")).toBeNull();
    expect(screen.queryByText("Recognize two-sum hash-map")).toBeNull();
    expect(screen.queryByText("Think about hash-map")).toBeNull();
    expect(screen.getByRole("button", { name: "Close selected approach" })).toBeTruthy();
    click("Get first hint");
    expect(screen.getByText("two-sum hash-map hint 1")).toBeTruthy();
    expect([hintRequests(), starterRequests(), solutionRequests()]).toEqual([1, 1, 1]);

    await navigate("https://leetcode.com/problems/two-sum/", 1);
    expect(screen.queryByText("two-sum hash-map hint 1")).toBeNull();
    click("Get first hint");
    expect(screen.getByText("two-sum hash-map hint 1")).toBeTruthy();
    expect(hintRequests()).toBe(1);
  });

  it("ignores pending guidance that finishes after disclosure collapses", async () => {
    await mount();
    click("Approach 2");
    let resolveHint!: (value: Response) => void;
    let resolveBundle!: (value: Response) => void;
    fetchMock
      .mockImplementationOnce(() => new Promise((resolve) => { resolveHint = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveBundle = resolve; }));
    click("Get first hint");
    const hintSignal = fetchMock.mock.lastCall![1].signal as AbortSignal;
    click("Get starter code");
    click("Generate Starter Code");
    const bundleSignal = fetchMock.mock.lastCall![1].signal as AbortSignal;
    click("Generate answer in Python");
    expect(starterRequests()).toBe(1);

    click("Approach 1");
    expect(hintSignal.aborted).toBe(true);
    expect(bundleSignal.aborted).toBe(false);
    await act(async () => {
      resolveHint(json({ slug: "two-sum", approachId: "hash-map", hints: ["Late hint"] }));
      resolveBundle(json(bundle("two-sum", "hash-map", "python", ["Late starter", "Late guided", "Late strong"])));
    });
    click("Approach 2");
    expect(screen.queryByText("Late hint")).toBeNull();
    expect(screen.queryByText("Late starter")).toBeNull();
    expect(screen.queryByText("two-sum hash-map python full solution")).toBeNull();
    expect(storedWorkspace("two-sum")?.hintsByApproach["hash-map"]).toBeUndefined();
    expect(storedWorkspace("two-sum")?.guidanceByApproach["hash-map"].python.level1).toBe("Late starter");
  });

  it("does not save a late hint response under a different problem", async () => {
    await mount();
    let resolveHint!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveHint = resolve; }));
    click("Get first hint");
    const signal = fetchMock.mock.lastCall![1].signal as AbortSignal;
    await activate("https://leetcode.com/problems/valid-parentheses/");
    await screen.findByRole("heading", { name: "Valid Parentheses" });
    expect(signal.aborted).toBe(true);
    await act(async () => resolveHint(json({
      slug: "two-sum", approachId: "hash-map", hints: ["Stale hint"]
    })));
    expect(storedWorkspace("two-sum")?.hintsByApproach["hash-map"]).toBeUndefined();
    await activate("https://leetcode.com/problems/two-sum/");
    click("Get first hint");
    await screen.findByText("two-sum hash-map hint 1");
    expect(hintRequests()).toBe(2);
  });

  it("waits for storage hydration before showing Coach or writing defaults", async () => {
    let resolveGet!: (value: Record<string, unknown>) => void;
    storageGet.mockImplementationOnce(() => new Promise((resolve) => { resolveGet = resolve; }));
    const saved = {
      "two-sum": {
        selectedApproachId: "brute-force", isThinkingExpanded: true,
        activeSection: "coach", hintsByApproach: {
          "brute-force": {
            response: { slug: "two-sum", approachId: "brute-force", hints: ["Saved first", "Saved second"] },
            visibleHintCount: 2
          }
        }
      }
    };
    render(<App />);
    await screen.findByText("Restoring Coach workspace...");
    expect(screen.queryByRole("button", { name: "Approach 1" })).toBeNull();
    expect(storageSet).not.toHaveBeenCalled();
    expect(hintRequests()).toBe(0);
    await act(async () => resolveGet({ [workspaceStorageKey]: saved }));
    expect(await screen.findByRole("button", { name: "Close selected approach" })).toBeTruthy();
    expect(screen.queryByText("Saved second")).toBeNull();
    expect(screen.queryByText("Think about brute-force")).toBeNull();
    click("Get first hint");
    expect(screen.getByText("Saved first")).toBeTruthy();
    expect(hintRequests()).toBe(0);
  });

  it("falls back safely for corrupted or obsolete storage", async () => {
    disk[workspaceStorageKey] = {
      "two-sum": {
        selectedApproachId: "hash-map", isThinkingExpanded: true,
        activeSection: "coach", hintsByApproach: {
          "hash-map": {
            response: { slug: "other-problem", approachId: "hash-map", hints: ["Wrong"] },
            visibleHintCount: 1
          }
        }
      }
    };
    expect(parseWorkspaces(disk[workspaceStorageKey])).toEqual({});
    const view = await mount();
    expect(screen.getByRole("tab", { name: "Coach" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.queryByRole("button", { name: "Close selected approach" })).toBeNull();
    view.unmount();
  });

  it("does not erase saved data when the storage read fails", async () => {
    const saved = {
      "two-sum": {
        selectedApproachId: "brute-force", isThinkingExpanded: true,
        activeSection: "practice", hintsByApproach: {}
      }
    };
    disk[workspaceStorageKey] = structuredClone(saved);
    storageGet.mockRejectedValueOnce(new Error("Storage unavailable"));
    await mount();
    click("Get first hint");
    expect(await screen.findByText("two-sum hash-map hint 1")).toBeTruthy();
    expect(hintRequests()).toBe(1);
    expect(storageSet).not.toHaveBeenCalled();
    expect(disk[workspaceStorageKey]).toEqual(saved);
  });

  it("discards an approach ID that no longer exists in the canonical analysis", async () => {
    disk[workspaceStorageKey] = {
      "two-sum": {
        selectedApproachId: "old-approach", isThinkingExpanded: true,
        activeSection: "coach", hintsByApproach: {}
      }
    };
    await mount();
    expect(screen.queryByRole("button", { name: "Close selected approach" })).toBeNull();
    await waitFor(() => expect(storedWorkspace("two-sum")?.selectedApproachId).toBeNull());
    expect(storedWorkspace("two-sum")?.isThinkingExpanded).toBe(false);
  });

  it("still works in memory when chrome.storage.local is missing", async () => {
    vi.stubGlobal("chrome", { tabs: chrome.tabs });
    await mount();
    click("Get first hint");
    expect(await screen.findByText("two-sum hash-map hint 1")).toBeTruthy();
    click("Show next hint");
    expect(screen.getByText("two-sum hash-map hint 2")).toBeTruthy();
    expect(hintRequests()).toBe(1);
  });
});
