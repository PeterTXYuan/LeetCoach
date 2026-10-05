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
