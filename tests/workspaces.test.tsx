// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../src/App";
import { parseWorkspaces, workspaceStorageKey } from "../src/coachWorkspaceStorage";

const json = (data: unknown) => ({ ok: true, status: 200, json: async () => data } as Response);
const fetchMock = vi.fn();
let disk: Record<string, unknown>;
let currentUrl: string;
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
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/starter-code")).length;
}

function storedWorkspace(slug: string) {
  return (disk[workspaceStorageKey] as Record<string, any> | undefined)?.[slug];
}

beforeEach(() => {
  localStorage.setItem("leetcoach-theme", "light");
  disk = {};
  currentUrl = "https://leetcode.com/problems/two-sum/";
  storageGet = vi.fn(async (key: string) => ({ [key]: disk[key] }));
  storageSet = vi.fn(async (items: Record<string, unknown>) => {
    Object.assign(disk, structuredClone(items));
  });
  const event = { addListener: vi.fn(), removeListener: vi.fn() };
  vi.stubGlobal("chrome", {
    tabs: {
      query: vi.fn(async () => [{
        url: currentUrl,
        title: currentUrl.includes("valid-parentheses")
          ? "Valid Parentheses - LeetCode" : "Two Sum - LeetCode"
      }]),
      onActivated: event, onUpdated: event
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
    if (path.endsWith("/starter-code")) {
      const body = JSON.parse(fetchMock.mock.lastCall![1].body as string);
      return json({ slug, approachId: parts[5], language: body.language, level: body.level,
        policyVersion: 3,
        levelName: ["", "Kickstart", "Guided", "Strong Scaffold"][body.level],
        isAiGenerated: false, code: `// TODO: ${slug} ${parts[5]} ${body.language} ${body.level}`,
        notice: "Complete the TODOs." });
    }
    return json({
      slug,
      approaches: catalogs[slug].map((approach, index) => ({
        ...approach, pattern: approach.name, summary: "Summary",
        displayOrder: index + 1, thinkingSteps: [`Think about ${approach.id}`]
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

async function activate(url: string) {
  currentUrl = url;
  const refresh = vi.mocked(chrome.tabs.onActivated.addListener).mock.calls[0][0];
  await act(async () => {
    refresh({ tabId: 2, windowId: 1 });
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
  it("caches starter code by canonical approach, language, and level across problems and remounts", async () => {
    const view = await mount();
    click("Get starter code");
    fireEvent.change(screen.getByLabelText("Starter language"), { target: { value: "java" } });
    fireEvent.click(screen.getByRole("button", { name: /Level 2/ }));
    click("Generate Starter Code");
    expect(await screen.findByText("// TODO: two-sum hash-map java 2")).toBeTruthy();
    expect(starterRequests()).toBe(1);
    click("Close starter code options");
    click("Get starter code");
    expect(screen.queryByText("// TODO: two-sum hash-map java 2")).toBeNull();
    click("Generate Starter Code");
    expect(screen.getByText("// TODO: two-sum hash-map java 2")).toBeTruthy();
    expect(starterRequests()).toBe(1);

    fireEvent.click(screen.getByRole("button", { name: /Level 3/ }));
    expect(screen.queryByText("// TODO: two-sum hash-map java 2")).toBeNull();
    click("Generate Starter Code");
    expect(await screen.findByText("// TODO: two-sum hash-map java 3")).toBeTruthy();
    expect(starterRequests()).toBe(2);
    fireEvent.click(screen.getByRole("button", { name: /Level 2/ }));
    expect(screen.getByText("// TODO: two-sum hash-map java 2")).toBeTruthy();
    expect(starterRequests()).toBe(2);

    await waitFor(() => expect(storedWorkspace("two-sum")?.starterByApproach["hash-map"]
      .responses["java:2"].code).toContain("two-sum"));
    await activate("https://leetcode.com/problems/valid-parentheses/");
    await screen.findByRole("heading", { name: "Valid Parentheses" });
    expect(screen.queryByText("// TODO: two-sum hash-map java 2")).toBeNull();
    await activate("https://leetcode.com/problems/two-sum/");
    expect(await screen.findByText("// TODO: two-sum hash-map java 2")).toBeTruthy();
    expect(starterRequests()).toBe(2);
    view.unmount();
    await mount();
    expect(await screen.findByText("// TODO: two-sum hash-map java 2")).toBeTruthy();
    expect((screen.getByLabelText("Starter language") as HTMLSelectElement).value).toBe("java");
    expect(starterRequests()).toBe(2);
  });

  it("drops a bad starter cache entry while retaining older hint data", () => {
    const parsed = parseWorkspaces({ "two-sum": {
      selectedApproachId: null, isThinkingExpanded: false, activeSection: "coach",
      hintsByApproach: { "hash-map": {
        response: { slug: "two-sum", approachId: "hash-map", hints: ["Saved hint"] },
        visibleHintCount: 1
      } },
      starterByApproach: { "hash-map": { language: "java", level: 2, isExpanded: true,
        isVisible: true, responses: { "java:2": { slug: "other", approachId: "hash-map",
          language: "java", level: 2, levelName: "Guided", isAiGenerated: false,
          code: "// TODO", notice: "Finish" } } } }
    } });
    expect(parsed["two-sum"].hintsByApproach["hash-map"].response.hints).toEqual(["Saved hint"]);
    expect(parsed["two-sum"].starterByApproach["hash-map"].responses).toEqual({});
  });

  it("invalidates pre-policy starter code without losing hints or starter preferences", () => {
    const savedResponse = (level: number, policyVersion?: number) => ({
      slug: "two-sum", approachId: "hash-map", language: "java", level,
      levelName: level === 2 ? "Guided" : "Strong Scaffold", isAiGenerated: true,
      code: `// TODO: level ${level}`, notice: "Finish", ...(policyVersion ? { policyVersion } : {})
    });
    const parsed = parseWorkspaces({ "two-sum": {
      selectedApproachId: "hash-map", isThinkingExpanded: true, activeSection: "coach",
      hintsByApproach: { "hash-map": {
        response: { slug: "two-sum", approachId: "hash-map", hints: ["Saved hint"] },
        visibleHintCount: 1
      } },
      starterByApproach: { "hash-map": {
        language: "java", level: 2, isExpanded: true, isVisible: true,
        responses: { "java:2": savedResponse(2, 2), "java:3": savedResponse(3, 3) }
      } }
    } });
    const workspace = parsed["two-sum"];
    expect(workspace.selectedApproachId).toBe("hash-map");
    expect(workspace.isThinkingExpanded).toBe(true);
    expect(workspace.hintsByApproach["hash-map"].response.hints).toEqual(["Saved hint"]);
    expect(workspace.starterByApproach["hash-map"]).toMatchObject({
      language: "java", level: 2, isExpanded: true, isVisible: false
    });
    expect(Object.keys(workspace.starterByApproach["hash-map"].responses)).toEqual(["java:3"]);
  });

  it("does not save an aborted starter response after switching the requested combination", async () => {
    await mount();
    let resolveStarter!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveStarter = resolve; }));
    click("Get starter code");
    click("Generate Starter Code");
    const signal = fetchMock.mock.lastCall![1].signal as AbortSignal;
    fireEvent.change(screen.getByLabelText("Starter language"), { target: { value: "java" } });
    expect(signal.aborted).toBe(true);
    await act(async () => resolveStarter(json({ slug: "two-sum", approachId: "hash-map",
      language: "python", level: 1, levelName: "Kickstart", isAiGenerated: false,
      code: "# TODO: stale", notice: "Finish" })));
    expect(storedWorkspace("two-sum")?.starterByApproach["hash-map"]?.responses["python:1"]).toBeUndefined();
    click("Generate Starter Code");
    expect(await screen.findByText("// TODO: two-sum hash-map java 1")).toBeTruthy();
    expect(starterRequests()).toBe(2);
  });

  it("retains a fallback across remounts but lets the user retry AI explicitly", async () => {
    const view = await mount();
    fetchMock.mockResolvedValueOnce(json({
      slug: "two-sum", approachId: "hash-map", language: "python", level: 1, policyVersion: 3,
      levelName: "Kickstart", isAiGenerated: false, usedFallback: true,
      code: "# TODO: offline fallback", notice: "AI starter code could not be used."
    }));
    click("Get starter code");
    click("Generate Starter Code");
    expect(await screen.findByText("# TODO: offline fallback")).toBeTruthy();
    await waitFor(() => expect(storedWorkspace("two-sum")?.starterByApproach["hash-map"]
      .responses["python:1"].usedFallback).toBe(true));
    view.unmount();
    await mount();
    expect(await screen.findByText("# TODO: offline fallback")).toBeTruthy();
    expect(starterRequests()).toBe(1);
    click("Try AI generation again");
    expect(await screen.findByText("// TODO: two-sum hash-map python 1")).toBeTruthy();
    expect(starterRequests()).toBe(2);
    expect(screen.queryByRole("button", { name: "Try AI generation again" })).toBeNull();
  });
  it("restores a problem's approach, hint count, thinking, and section without another hint request", async () => {
    await mount();
    click("Approach 1");
    click("Get first hint");
    await screen.findByText("two-sum brute-force hint 1");
    click("Show next hint");
    expect(screen.getByText("two-sum brute-force hint 2")).toBeTruthy();
    click("Show thinking process");
    section("Practice");
    await screen.findByRole("heading", { name: "Easier" });
    await waitFor(() => expect(storedWorkspace("two-sum")?.hintsByApproach["brute-force"].visibleHintCount).toBe(2));
    expect(storedWorkspace("two-sum")?.activeSection).toBe("practice");

    await activate("https://leetcode.com/problems/valid-parentheses/");
    await screen.findByRole("heading", { name: "Valid Parentheses" });
    expect(screen.getByRole("tab", { name: "Coach" }).getAttribute("aria-selected")).toBe("true");
    click("Get first hint");
    await screen.findByText("valid-parentheses stack hint 1");
    expect(hintRequests()).toBe(2);
    await waitFor(() => expect(storedWorkspace("valid-parentheses")?.hintsByApproach.stack).toBeTruthy());
    expect(storedWorkspace("two-sum")?.hintsByApproach["brute-force"].visibleHintCount).toBe(2);

    await activate("https://leetcode.com/problems/two-sum/");
    await waitFor(() => expect(screen.getByRole("tab", { name: "Practice" }).getAttribute("aria-selected")).toBe("true"));
    section("Coach");
    expect(await screen.findByText("two-sum brute-force hint 2")).toBeTruthy();
    expect(screen.getByText("Think about brute-force")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Close selected approach" })).toBeTruthy();
    expect(hintRequests()).toBe(2);
  });

  it("restores the same state after the side panel is unmounted and reopened", async () => {
    const view = await mount();
    click("Approach 1");
    click("Get first hint");
    await screen.findByText("two-sum brute-force hint 1");
    click("Show next hint");
    click("Show thinking process");
    section("Practice");
    await waitFor(() => expect(storedWorkspace("two-sum")?.activeSection).toBe("practice"));
    await waitFor(() => expect(storedWorkspace("two-sum")?.hintsByApproach["brute-force"].visibleHintCount).toBe(2));
    view.unmount();

    render(<App />);
    await waitFor(() => expect(screen.getByRole("tab", { name: "Practice" }).getAttribute("aria-selected")).toBe("true"));
    section("Coach");
    expect(await screen.findByText("two-sum brute-force hint 2")).toBeTruthy();
    expect(screen.getByText("Think about brute-force")).toBeTruthy();
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
    expect(screen.getByText("two-sum hash-map hint 2")).toBeTruthy();
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
    expect(await screen.findByText("Saved second")).toBeTruthy();
    expect(screen.getByText("Think about brute-force")).toBeTruthy();
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
