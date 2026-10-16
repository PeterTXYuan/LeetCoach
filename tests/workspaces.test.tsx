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
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/starter-code")).length;
}

function solutionRequests() {
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/solution")).length;
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
    if (path.endsWith("/starter-code")) {
      const body = JSON.parse(fetchMock.mock.lastCall![1].body as string);
      return json({ slug, approachId: parts[5], language: body.language, level: body.level,
        policyVersion: 6,
        levelName: ["", "Kickstart", "Guided", "Strong Scaffold"][body.level],
        isAiGenerated: false, code: `// TODO: ${slug} ${parts[5]} ${body.language} ${body.level}`,
        notice: "Complete the TODOs." });
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
  it("regenerates each cached guidance type with a fresh request and replaces only that response", async () => {
    const normalFetch = fetchMock.getMockImplementation()!;
    const versions = { hints: 0, starter: 0, answer: 0 };
    fetchMock.mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith("/hints")) {
        const version = ++versions.hints;
        return Promise.resolve(json({ slug: "two-sum", approachId: "hash-map",
          hints: [`Hint version ${version} one`, `Hint version ${version} two`] }));
      }
      if (url.endsWith("/starter-code")) {
        const version = ++versions.starter;
        return Promise.resolve(json({ slug: "two-sum", approachId: "hash-map",
          ...JSON.parse(options!.body as string), policyVersion: 6, levelName: "Kickstart",
          isAiGenerated: true, code: `Starter version ${version}`, notice: "Complete the TODOs." }));
      }
      if (url.endsWith("/solution")) {
        const version = ++versions.answer;
        return Promise.resolve(json({ ...solution("two-sum", "hash-map", "python"),
          code: `Answer version ${version}` }));
      }
      return normalFetch(url, options);
    });
    await mount();
    click("Approach 2");
    click("Get first hint");
    await screen.findByText("Hint version 1 one");
    click("Show next hint");
    click("Regenerate hints");
    await screen.findByText("Hint version 2 one");
    expect(screen.queryByText("Hint version 1 one")).toBeNull();
    expect(screen.queryByText("Hint version 2 two")).toBeNull();
    expect(hintRequests()).toBe(2);
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/hints"))[1][1].cache)
      .toBe("no-store");

    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("Starter version 1");
    click("Regenerate starter code");
    await screen.findByText("Starter version 2");
    expect(screen.queryByText("Starter version 1")).toBeNull();
    expect(starterRequests()).toBe(2);

    click("Generate answer in Python");
    await screen.findByText("Answer version 1");
    click("Regenerate answer");
    await screen.findByText("Answer version 2");
    expect(screen.queryByText("Answer version 1")).toBeNull();
    expect(solutionRequests()).toBe(2);
    await waitFor(() => expect(storedWorkspace("two-sum")?.hintsByApproach["hash-map"].response.hints[0])
      .toBe("Hint version 2 one"));
    expect(storedWorkspace("two-sum")?.starterByApproach["hash-map"].responses["python:1"].code)
      .toBe("Starter version 2");
    expect(storedWorkspace("two-sum")?.solutionByApproach["hash-map"].responses.python.code)
      .toBe("Answer version 2");
  });

  it("keeps previous generated guidance visible when regeneration fails", async () => {
    await mount();
    click("Approach 2");
    click("Get first hint");
    await screen.findByText("two-sum hash-map hint 1");
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map python 1");
    click("Generate answer in Python");
    await screen.findByText("two-sum hash-map python full solution");

    fetchMock.mockRejectedValueOnce(new Error("Offline"));
    click("Regenerate hints");
    await screen.findByText(/Could not regenerate hints/);
    expect(screen.getByText("two-sum hash-map hint 1")).toBeTruthy();

    fetchMock.mockRejectedValueOnce(new Error("Offline"));
    click("Regenerate starter code");
    await screen.findByText(/Unable to regenerate starter code/);
    expect(screen.getByText("// TODO: two-sum hash-map python 1")).toBeTruthy();

    fetchMock.mockRejectedValueOnce(new Error("Offline"));
    click("Regenerate answer");
    await screen.findByText(/Your previous answer is still available/);
    expect(screen.getByText("two-sum hash-map python full solution")).toBeTruthy();
  });

  it("blocks duplicate regeneration clicks and leaves other starter levels and answer languages cached", async () => {
    await mount();
    click("Approach 2");
    click("Get first hint");
    await screen.findByText("two-sum hash-map hint 1");
    let resolveHints!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveHints = resolve; }));
    click("Regenerate hints");
    expect((screen.getByRole("button", { name: "Regenerating hints..." }) as HTMLButtonElement).disabled).toBe(true);
    click("Regenerating hints...");
    expect(hintRequests()).toBe(2);
    await act(async () => resolveHints(json({ slug: "two-sum", approachId: "hash-map",
      hints: ["Fresh hint one", "Fresh hint two"] })));
    expect(await screen.findByText("Fresh hint one")).toBeTruthy();

    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map python 1");
    fireEvent.click(screen.getByRole("button", { name: /Level 2/ }));
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map python 2");
    fireEvent.click(screen.getByRole("button", { name: /Level 1/ }));
    let resolveStarter!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveStarter = resolve; }));
    click("Regenerate starter code");
    expect((screen.getByRole("button", { name: "Regenerating starter code..." }) as HTMLButtonElement).disabled).toBe(true);
    click("Regenerating starter code...");
    expect(starterRequests()).toBe(3);
    await act(async () => resolveStarter(json({ slug: "two-sum", approachId: "hash-map",
      language: "python", level: 1, levelName: "Kickstart", policyVersion: 6,
      isAiGenerated: true, code: "Fresh starter", notice: "Complete the TODOs." })));
    expect(await screen.findByText("Fresh starter")).toBeTruthy();
    await waitFor(() => expect(storedWorkspace("two-sum")?.starterByApproach["hash-map"].responses["python:2"].code)
      .toBe("// TODO: two-sum hash-map python 2"));

    click("Generate answer in Python");
    await screen.findByText("two-sum hash-map python full solution");
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "java" } });
    click("Generate answer in Java");
    await screen.findByText("two-sum hash-map java full solution");
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "python" } });
    let resolveAnswer!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveAnswer = resolve; }));
    click("Regenerate answer");
    expect((screen.getByRole("button", { name: "Regenerating answer..." }) as HTMLButtonElement).disabled).toBe(true);
    click("Regenerating answer...");
    expect(solutionRequests()).toBe(3);
    await act(async () => resolveAnswer(json({ ...solution("two-sum", "hash-map", "python"), code: "Fresh answer" })));
    expect(await screen.findByText("Fresh answer")).toBeTruthy();
    await waitFor(() => expect(storedWorkspace("two-sum")?.solutionByApproach["hash-map"].responses.java.code)
      .toBe("two-sum hash-map java full solution"));
  });

  it("collapses every reveal on approach changes but reuses each generated response", async () => {
    await mount();
    click("Approach 2");
    click("Get first hint");
    await screen.findByText("two-sum hash-map hint 1");
    click("Show next hint");
    click("Get starter code");
    fireEvent.click(screen.getByRole("button", { name: /Level 2/ }));
    click("Generate Starter Code");
    await screen.findByText("// TODO: two-sum hash-map python 2");
    click("Generate answer in Python");
    await screen.findByText("two-sum hash-map python full solution");
    click("Reveal recognition signals");
    click("Show thinking process");
    const requests = [hintRequests(), starterRequests(), solutionRequests()];

    click("Approach 1");
    click("Approach 2");
    await waitFor(() => expect(screen.queryByText("two-sum hash-map hint 1")).toBeNull());
    expect(screen.queryByText("// TODO: two-sum hash-map python 2")).toBeNull();
    expect(screen.queryByText("two-sum hash-map python full solution")).toBeNull();
    expect(screen.queryByText("Recognize two-sum hash-map")).toBeNull();
    expect(screen.queryByText("Think about hash-map")).toBeNull();
    expect(screen.getByRole("button", { name: "Get starter code" })).toBeTruthy();
    expect([hintRequests(), starterRequests(), solutionRequests()]).toEqual(requests);

    click("Get first hint");
    expect(screen.getByText("two-sum hash-map hint 1")).toBeTruthy();
    click("Get starter code");
    expect(screen.getByRole("button", { name: /Level 2/ }).getAttribute("aria-pressed")).toBe("true");
    click("Generate Starter Code");
    expect(screen.getByText("// TODO: two-sum hash-map python 2")).toBeTruthy();
    click("Generate answer in Python");
    expect(screen.getByText("two-sum hash-map python full solution")).toBeTruthy();
    expect([hintRequests(), starterRequests(), solutionRequests()]).toEqual(requests);
    await waitFor(() => expect(storedWorkspace("two-sum")?.solutionByApproach["hash-map"]
      .responses.python.code).toContain("hash-map"));
    expect(storedWorkspace("two-sum")?.hintsByApproach["hash-map"].visibleHintCount).toBe(0);
    expect(storedWorkspace("two-sum")?.starterByApproach["hash-map"].isExpanded).toBe(false);
    expect(storedWorkspace("two-sum")?.solutionByApproach["hash-map"].visibleByLanguage).toEqual({});
    expect(storedWorkspace("two-sum")?.recognitionRevealedByApproach).toBeUndefined();
  });

  it("caches full solutions separately while collapsing them on approach changes and remounts", async () => {
    const view = await mount();
    click("Approach 1");
    expect(solutionRequests()).toBe(0);
    click("Generate answer in Python");
    expect(await screen.findByText("two-sum brute-force python full solution")).toBeTruthy();
    expect(screen.getByRole("note").textContent).toContain("Full solution revealed");
    expect(solutionRequests()).toBe(1);
    click("Generate answer in Python");
    expect(solutionRequests()).toBe(1);
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "java" } });
    expect(screen.queryByText("two-sum brute-force python full solution")).toBeNull();
    expect(solutionRequests()).toBe(1);
    click("Generate answer in Java");
    expect(await screen.findByText("two-sum brute-force java full solution")).toBeTruthy();
    expect(solutionRequests()).toBe(2);
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "python" } });
    expect(screen.getByText("two-sum brute-force python full solution")).toBeTruthy();
    expect(solutionRequests()).toBe(2);
    click("Approach 2");
    expect(screen.queryByText("two-sum brute-force python full solution")).toBeNull();
    click("Generate answer in Python");
    expect(await screen.findByText("two-sum hash-map python full solution")).toBeTruthy();
    expect(solutionRequests()).toBe(3);
    click("Approach 1");
    expect(screen.queryByText("two-sum brute-force python full solution")).toBeNull();
    click("Generate answer in Python");
    expect(screen.getByText("two-sum brute-force python full solution")).toBeTruthy();
    expect(solutionRequests()).toBe(3);
    await waitFor(() => expect(storedWorkspace("two-sum")?.solutionByApproach["brute-force"]
      .responses.java.code).toContain("brute-force java"));
    await activate("https://leetcode.com/problems/valid-parentheses/");
    await screen.findByRole("heading", { name: "Valid Parentheses" });
    expect(screen.queryByText("two-sum brute-force python full solution")).toBeNull();
    click("Approach 1");
    click("Generate answer in Python");
    expect(await screen.findByText("valid-parentheses stack python full solution")).toBeTruthy();
    await activate("https://leetcode.com/problems/two-sum/");
    expect(await screen.findByText("two-sum brute-force python full solution")).toBeTruthy();
    expect(solutionRequests()).toBe(4);
    view.unmount();
    await mount();
    expect(screen.getByRole("button", { name: "Close selected approach" })).toBeTruthy();
    expect(screen.queryByText("two-sum brute-force python full solution")).toBeNull();
    click("Generate answer in Python");
    expect(screen.getByText("two-sum brute-force python full solution")).toBeTruthy();
    expect(solutionRequests()).toBe(4);
  });

  it("hides an answer without deleting its cache or revealing it on remount", async () => {
    const view = await mount();
    click("Approach 1");
    click("Generate answer in Python");
    expect(await screen.findByText("two-sum brute-force python full solution")).toBeTruthy();
    click("Hide answer");
    expect(screen.queryByText("two-sum brute-force python full solution")).toBeNull();
    await waitFor(() => expect(storedWorkspace("two-sum")?.solutionByApproach["brute-force"]
      .visibleByLanguage.python).toBeUndefined());
    view.unmount();
    await mount();
    expect(screen.queryByText("two-sum brute-force python full solution")).toBeNull();
    expect(solutionRequests()).toBe(1);
    click("Generate answer in Python");
    expect(screen.getByText("two-sum brute-force python full solution")).toBeTruthy();
    expect(solutionRequests()).toBe(1);
  });

  it("drops corrupted or outdated solution entries without losing hints and starter code", () => {
    const valid = solution("two-sum", "hash-map", "python");
    const parsed = parseWorkspaces({ "two-sum": {
      selectedApproachId: "hash-map", isThinkingExpanded: false, activeSection: "coach",
      hintsByApproach: { "hash-map": { response: {
        slug: "two-sum", approachId: "hash-map", hints: ["Saved hint"] }, visibleHintCount: 1 } },
      starterByApproach: { "hash-map": { language: "python", level: 1, isExpanded: false,
        isVisible: false, responses: {} } },
      solutionByApproach: {
        "hash-map": { policyVersion: solutionPolicyVersion, language: "python",
          visibleByLanguage: { python: true, java: true, cpp: true },
          responses: { python: valid, java: { ...valid, language: "java", slug: "other" },
            cpp: { ...valid, language: "cpp", code: "" } } },
        "brute-force": { policyVersion: 0, language: "python", visibleByLanguage: { python: true },
          responses: { python: solution("two-sum", "brute-force", "python") } }
      }
    } });
    expect(parsed["two-sum"].hintsByApproach["hash-map"].response.hints).toEqual(["Saved hint"]);
    expect(parsed["two-sum"].starterByApproach["hash-map"]).toBeTruthy();
    expect(parsed["two-sum"].solutionByApproach["hash-map"].responses).toEqual({ python: valid });
    expect(parsed["two-sum"].solutionByApproach["hash-map"].visibleByLanguage).toEqual({});
    expect(parsed["two-sum"].solutionByApproach["brute-force"]).toBeUndefined();
  });

  it("aborts a pending answer when language or problem changes and ignores late data", async () => {
    await mount();
    click("Approach 1");
    let resolveSolution!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveSolution = resolve; }));
    click("Generate answer in Python");
    const signal = fetchMock.mock.lastCall![1].signal as AbortSignal;
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "java" } });
    expect(signal.aborted).toBe(true);
    await act(async () => resolveSolution(json(solution("two-sum", "brute-force", "python"))));
    expect(storedWorkspace("two-sum")?.solutionByApproach?.["brute-force"]?.responses.python).toBeUndefined();
    click("Generate answer in Java");
    expect(await screen.findByText("two-sum brute-force java full solution")).toBeTruthy();
    expect(solutionRequests()).toBe(2);

    let resolveOther!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveOther = resolve; }));
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "cpp" } });
    click("Generate answer in C++");
    const otherSignal = fetchMock.mock.lastCall![1].signal as AbortSignal;
    await activate("https://leetcode.com/problems/valid-parentheses/");
    await screen.findByRole("heading", { name: "Valid Parentheses" });
    expect(otherSignal.aborted).toBe(true);
    await act(async () => resolveOther(json(solution("two-sum", "brute-force", "cpp"))));
    expect(storedWorkspace("two-sum")?.solutionByApproach["brute-force"].responses.cpp).toBeUndefined();
    expect(screen.queryByText("two-sum brute-force cpp full solution")).toBeNull();
  });

  it("never stores a successful HTTP response for a different solution identity", async () => {
    await mount();
    click("Approach 1");
    fetchMock.mockResolvedValueOnce(json(solution("two-sum", "hash-map", "python")));
    click("Generate answer in Python");
    expect((await screen.findByRole("alert")).textContent).toContain("did not match");
    expect(screen.queryByText("two-sum hash-map python full solution")).toBeNull();
    expect(storedWorkspace("two-sum")?.solutionByApproach?.["brute-force"]?.responses.python).toBeUndefined();
    click("Retry");
    expect(await screen.findByText("two-sum brute-force python full solution")).toBeTruthy();
    expect(solutionRequests()).toBe(2);
  });

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
    expect(screen.queryByText("// TODO: two-sum hash-map java 2")).toBeNull();
    click("Get starter code");
    expect((screen.getByLabelText("Starter language") as HTMLSelectElement).value).toBe("java");
    click("Generate Starter Code");
    expect(screen.getByText("// TODO: two-sum hash-map java 2")).toBeTruthy();
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
        responses: { "java:1": savedResponse(1, 6), "java:2": savedResponse(2, 5),
          "java:3": savedResponse(3, 3) }
      } }
    } });
    const workspace = parsed["two-sum"];
    expect(workspace.selectedApproachId).toBe("hash-map");
    expect(workspace.isThinkingExpanded).toBe(false);
    expect(workspace.hintsByApproach["hash-map"].response.hints).toEqual(["Saved hint"]);
    expect(workspace.starterByApproach["hash-map"]).toMatchObject({
      language: "java", level: 2, isExpanded: false, isVisible: false
    });
    expect(Object.keys(workspace.starterByApproach["hash-map"].responses)).toEqual(["java:1"]);
  });

  it("does not regenerate an old-policy starter cache during hydration", async () => {
    disk[workspaceStorageKey] = { "two-sum": {
      selectedApproachId: "hash-map", isThinkingExpanded: false, activeSection: "coach",
      hintsByApproach: { "hash-map": {
        response: { slug: "two-sum", approachId: "hash-map", hints: ["Saved hint"] },
        visibleHintCount: 0
      } },
      starterByApproach: { "hash-map": { language: "java", level: 2,
        isExpanded: false, isVisible: false,
        responses: { "java:2": { slug: "two-sum", approachId: "hash-map", language: "java",
          level: 2, levelName: "Guided", isAiGenerated: true, policyVersion: 3,
          code: "// TODO: old scaffold", notice: "Old" } } } }
    } };
    await mount();
    expect(starterRequests()).toBe(0);
    expect(storedWorkspace("two-sum")?.selectedApproachId).toBe("hash-map");
    click("Get starter code");
    expect((screen.getByLabelText("Starter language") as HTMLSelectElement).value).toBe("java");
    expect(starterRequests()).toBe(0);
    click("Generate Starter Code");
    expect(await screen.findByText("// TODO: two-sum hash-map java 2")).toBeTruthy();
    expect(starterRequests()).toBe(1);
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
      slug: "two-sum", approachId: "hash-map", language: "python", level: 1, policyVersion: 6,
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
    expect(screen.queryByText("# TODO: offline fallback")).toBeNull();
    click("Get starter code");
    click("Generate Starter Code");
    expect(screen.getByText("# TODO: offline fallback")).toBeTruthy();
    expect(starterRequests()).toBe(1);
    click("Try AI generation again");
    expect(await screen.findByText("// TODO: two-sum hash-map python 1")).toBeTruthy();
    expect(starterRequests()).toBe(2);
    expect(screen.queryByRole("button", { name: "Try AI generation again" })).toBeNull();
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
    let resolveStarter!: (value: Response) => void;
    let resolveAnswer!: (value: Response) => void;
    fetchMock
      .mockImplementationOnce(() => new Promise((resolve) => { resolveHint = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveStarter = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveAnswer = resolve; }));
    click("Get first hint");
    const hintSignal = fetchMock.mock.lastCall![1].signal as AbortSignal;
    click("Get starter code");
    click("Generate Starter Code");
    const starterSignal = fetchMock.mock.lastCall![1].signal as AbortSignal;
    click("Generate answer in Python");
    const answerSignal = fetchMock.mock.lastCall![1].signal as AbortSignal;

    click("Approach 1");
    expect([hintSignal.aborted, starterSignal.aborted, answerSignal.aborted]).toEqual([true, true, true]);
    await act(async () => {
      resolveHint(json({ slug: "two-sum", approachId: "hash-map", hints: ["Late hint"] }));
      resolveStarter(json({ slug: "two-sum", approachId: "hash-map", language: "python", level: 1,
        policyVersion: 6, levelName: "Kickstart", isAiGenerated: false, code: "Late starter", notice: "TODO" }));
      resolveAnswer(json(solution("two-sum", "hash-map", "python")));
    });
    click("Approach 2");
    expect(screen.queryByText("Late hint")).toBeNull();
    expect(screen.queryByText("Late starter")).toBeNull();
    expect(screen.queryByText("two-sum hash-map python full solution")).toBeNull();
    expect(storedWorkspace("two-sum")?.hintsByApproach["hash-map"]).toBeUndefined();
    expect(storedWorkspace("two-sum")?.starterByApproach["hash-map"]?.responses).toEqual({});
    expect(storedWorkspace("two-sum")?.solutionByApproach["hash-map"]?.responses).toBeUndefined();
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
