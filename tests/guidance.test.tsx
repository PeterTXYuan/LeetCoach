// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../src/App";

const approaches = [
  { id: "brute-force", name: "Brute Force", isPrimary: false },
  { id: "hash-map", name: "One-pass Hash Map", isPrimary: true }
].map((a, i) => ({ ...a, pattern: a.name, summary: "Summary", displayOrder: i + 1, thinkingSteps: ["Think first"],
  recognitionSignals: { quote: "two numbers", bullets: [`Recognize ${a.id}`, "A plain-language clue."] }
}));

const hints = (id: string) => ({ slug: "two-sum", approachId: id, hints: [`${id} hint 1`, `${id} hint 2`] });
const solution = (language: string) => ({
  slug: "two-sum", approachId: "brute-force", language, isAiGenerated: false,
  warning: "Curated mock example", code: `${language} example code`, explanation: "Check each pair",
  timeComplexity: "O(n^2)", spaceComplexity: "O(1)"
});
const json = (data: unknown) => ({ ok: true, status: 200, json: async () => data } as Response);
const fetchMock = vi.fn();

beforeEach(() => {
  localStorage.setItem("leetcoach-theme", "light");
  const event = { addListener: vi.fn(), removeListener: vi.fn() };
  vi.stubGlobal("chrome", { tabs: {
    query: vi.fn().mockResolvedValue([{ url: "https://leetcode.com/problems/two-sum/", title: "Two Sum - LeetCode" }]),
    onActivated: event, onUpdated: event
  } });
  fetchMock.mockReset().mockImplementation(async (url: string, options?: RequestInit) => {
    if (url.endsWith("/related")) return json({ slug: "two-sum", easier: [], similar: [], harder: [] });
    if (url.endsWith("/starter-code")) return json({
      slug: "two-sum", approachId: "brute-force", ...JSON.parse(options!.body as string),
      levelName: "Guided", isAiGenerated: false, code: "// TODO: starter scaffold", notice: "Complete the TODOs."
    });
    if (url.endsWith("/solution")) return json(solution(JSON.parse(options!.body as string).language));
    if (url.endsWith("/hints")) return json(hints(url.includes("/brute-force/") ? "brute-force" : "hash-map"));
    const problemMatch = url.match(/\/api\/problems\/([^/]+)$/);
    return json({ slug: problemMatch ? decodeURIComponent(problemMatch[1]) : "two-sum", approaches });
  });
  vi.stubGlobal("fetch", fetchMock);
});

describe("global section navigation", () => {
  const selectTab = (name: string) => fireEvent.click(screen.getByRole("tab", { name, exact: true }));

  async function activateBrowserTab(url: string, title?: string) {
    vi.mocked(chrome.tabs.query).mockResolvedValue([{ url, title }] as chrome.tabs.Tab[]);
    const refresh = vi.mocked(chrome.tabs.onActivated.addListener).mock.calls[0][0];
    await act(async () => {
      refresh({ tabId: 2, windowId: 1 });
      await Promise.resolve();
      await Promise.resolve();
    });
  }

  it("preserves expanded Coach guidance across extension and browser tab switches", async () => {
    await mount();
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Coach", "Practice", "Progress", "About"]);
    expect(screen.getByRole("tab", { name: "Coach" }).getAttribute("aria-selected")).toBe("true");
    click("Approach 1");
    click("Get first hint");
    await screen.findByText("brute-force hint 1");
    click("Show thinking process");
    chooseLanguage("java");
    click("Generate answer in Java");
    await screen.findByText("java example code");
    click("Get starter code");
    fireEvent.change(screen.getByLabelText("Starter language"), { target: { value: "cpp" } });
    fireEvent.click(screen.getByRole("button", { name: /Level 2/ }));
    click("Generate Starter Code");
    await screen.findByText("// TODO: starter scaffold");
    click("Reveal recognition signals");
    const coach = screen.getByRole("tabpanel", { name: "Coach" });
    const requestCount = fetchMock.mock.calls.length;
    for (const section of ["Practice", "Progress", "About"]) {
      selectTab(section);
      if (section === "Practice") await screen.findByRole("heading", { name: "Easier" });
      expect(screen.queryByRole("tabpanel", { name: "Coach" })).toBeNull();
      expect(coach.isConnected).toBe(true);
      expect(screen.getByRole("tabpanel", { name: section })).toBeTruthy();
      selectTab("Coach");
      expect(screen.getByRole("tabpanel", { name: "Coach" })).toBe(coach);
      expect(screen.getByText("brute-force hint 1")).toBeTruthy();
      expect(screen.getByText("Think first")).toBeTruthy();
      expect(screen.getByText("java example code")).toBeTruthy();
      expect(screen.getByText("// TODO: starter scaffold")).toBeTruthy();
      expect(screen.getByText("Recognize brute-force")).toBeTruthy();
      expect(screen.getByRole("button", { name: "Close starter code options" })).toBeTruthy();
      expect((screen.getByLabelText("Language") as HTMLSelectElement).value).toBe("java");
    }
    expect(fetchMock.mock.calls.filter(([url]) => !url.endsWith("/related"))).toHaveLength(requestCount);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/related"))).toHaveLength(1);

    expect((screen.getByLabelText("Starter language") as HTMLSelectElement).value).toBe("cpp");
    expect(screen.getByRole("button", { name: /Level 2/ }).getAttribute("aria-pressed")).toBe("true");
    expect(fetchMock.mock.calls.filter(([url]) => !url.endsWith("/related"))).toHaveLength(requestCount);

    const requestsBeforeBrowserSwitch = fetchMock.mock.calls.length;
    await activateBrowserTab("https://example.com/");
    await screen.findByText("Open a LeetCode problem to use Coach and Practice.");
    expect(coach.isConnected).toBe(true);
    await activateBrowserTab("https://leetcode.com/problems/two-sum/", "Two Sum - LeetCode");
    await waitFor(() => expect(screen.getByRole("tab", { name: "Coach" }).getAttribute("aria-selected")).toBe("true"));
    expect(screen.getByRole("tabpanel", { name: "Coach" })).toBe(coach);
    expect(screen.getByText("brute-force hint 1")).toBeTruthy();
    expect(screen.getByText("Think first")).toBeTruthy();
    expect(screen.getByText("java example code")).toBeTruthy();
    expect(screen.getByText("// TODO: starter scaffold")).toBeTruthy();
    expect(screen.getByText("Recognize brute-force")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(requestsBeforeBrowserSwitch);
  });

  it.each(["Coach", "Practice", "Progress", "About"])("restores %s after returning to the same problem", async (section) => {
    await mount();
    if (section !== "Coach") selectTab(section);
    if (section === "Practice") await screen.findByRole("heading", { name: "Easier" });
    const relatedRequests = () => fetchMock.mock.calls.filter(([url]) => url.endsWith("/related")).length;
    const beforeLeaving = relatedRequests();

    await activateBrowserTab("https://example.com/");
    await screen.findByText("Open a LeetCode problem to use Coach and Practice.");
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Progress", "About"]);
    expect(screen.getByRole("tab", { name: section === "About" ? "About" : "Progress" }).getAttribute("aria-selected")).toBe("true");

    await activateBrowserTab("https://leetcode.com/problems/two-sum/", "Two Sum - LeetCode");
    await waitFor(() => expect(screen.getByRole("tab", { name: section }).getAttribute("aria-selected")).toBe("true"));
    if (section === "Practice") {
      await screen.findByRole("heading", { name: "Easier" });
      expect(relatedRequests()).toBe(beforeLeaving);
    }
  });

  it("uses a deliberate global selection made while away", async () => {
    await mount();
    selectTab("Practice");
    await screen.findByRole("heading", { name: "Easier" });
    await activateBrowserTab("https://example.com/");
    await screen.findByText("Open a LeetCode problem to use Coach and Practice.");
    selectTab("About");
    await activateBrowserTab("https://leetcode.com/problems/two-sum/", "Two Sum - LeetCode");
    await waitFor(() => expect(screen.getByRole("tab", { name: "About" }).getAttribute("aria-selected")).toBe("true"));
  });

  it("starts a different problem at Coach and resets problem-specific state", async () => {
    await mount();
    click("Approach 1");
    click("Get first hint");
    await screen.findByText("brute-force hint 1");
    selectTab("Practice");
    await screen.findByRole("heading", { name: "Easier" });

    await activateBrowserTab(
      "https://leetcode.com/problems/valid-parentheses/",
      "Valid Parentheses - LeetCode"
    );
    await waitFor(() => expect(screen.getByRole("tab", { name: "Coach" }).getAttribute("aria-selected")).toBe("true"));
    await screen.findByRole("heading", { name: "Valid Parentheses" });
    expect(screen.queryByText("brute-force hint 1")).toBeNull();
    expect(screen.queryByRole("button", { name: "Close selected approach" })).toBeNull();
  });

  it("allows an in-flight Coach request to finish while a non-LeetCode tab is active", async () => {
    await mount();
    click("Approach 1");
    let resolve!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((yes) => { resolve = yes; }));
    click("Generate answer in Python");
    const signal = fetchMock.mock.lastCall![1].signal;
    await activateBrowserTab("https://example.com/");
    await screen.findByText("Open a LeetCode problem to use Coach and Practice.");
    expect(signal.aborted).toBe(false);
    await act(async () => resolve(json(solution("python"))));
    await activateBrowserTab("https://leetcode.com/problems/two-sum/", "Two Sum - LeetCode");
    await waitFor(() => expect(screen.getByRole("tab", { name: "Coach" }).getAttribute("aria-selected")).toBe("true"));
    expect(screen.getByText("python example code")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("shows only global tabs without a problem and defaults to Coach when one appears", async () => {
    vi.mocked(chrome.tabs.query).mockResolvedValue([{ url: "https://example.com" }] as chrome.tabs.Tab[]);
    render(<App />);
    await screen.findByText("Open a LeetCode problem to use Coach and Practice.");
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Progress", "About"]);
    expect(fetchMock).not.toHaveBeenCalled();
    selectTab("About");
    expect(screen.getByRole("heading", { name: "About LeetCoach" })).toBeTruthy();
    vi.mocked(chrome.tabs.query).mockResolvedValue([{ url: "https://leetcode.com/problems/two-sum/" }] as chrome.tabs.Tab[]);
    const refresh = vi.mocked(chrome.tabs.onActivated.addListener).mock.calls[0][0];
    await act(async () => refresh({ tabId: 1, windowId: 1 }));
    await screen.findByRole("button", { name: "Approach 1" });
    expect(screen.getByRole("tab", { name: "Coach" }).getAttribute("aria-selected")).toBe("true");
    selectTab("Practice");
    vi.mocked(chrome.tabs.query).mockResolvedValue([{ url: "https://example.com" }] as chrome.tabs.Tab[]);
    await act(async () => refresh({ tabId: 2, windowId: 1 }));
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Progress", "About"]);
    expect(screen.getByRole("tabpanel", { name: "Progress" })).toBeTruthy();
  });

  it("supports arrow and Home/End navigation with one tab stop", async () => {
    await mount();
    const coach = screen.getByRole("tab", { name: "Coach" });
    fireEvent.keyDown(coach, { key: "ArrowLeft" });
    expect(document.activeElement).toBe(screen.getByRole("tab", { name: "About" }));
    fireEvent.keyDown(document.activeElement!, { key: "Home" });
    expect(document.activeElement).toBe(coach);
    fireEvent.keyDown(coach, { key: "ArrowRight" });
    expect(document.activeElement).toBe(screen.getByRole("tab", { name: "Practice" }));
    fireEvent.keyDown(document.activeElement!, { key: "End" });
    expect(document.activeElement).toBe(screen.getByRole("tab", { name: "About" }));
    expect(screen.getAllByRole("tab").filter((tab) => tab.tabIndex === 0)).toHaveLength(1);
  });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

async function mount() {
  render(<App />);
  await screen.findByRole("button", { name: "Approach 1" });
}
function click(name: string) { fireEvent.click(screen.getByRole("button", { name, exact: true })); }
function chooseLanguage(language: string) { fireEvent.change(screen.getByLabelText("Language"), { target: { value: language } }); }

describe("canonical hint disclosure", () => {
  it("labels default hints by primary ID and hides them on selection while reusing the batch", async () => {
    await mount();
    expect(screen.getByLabelText("Hints for Approach 2")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    click("Get first hint");
    await screen.findByText("hash-map hint 1");
    click("Approach 2");
    expect(screen.queryByText("hash-map hint 1")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    click("Get first hint");
    expect(screen.getByText("hash-map hint 1")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("closing an alternative hides its hints and returns to the primary badge and endpoint", async () => {
    await mount();
    click("Approach 1");
    expect(screen.getByLabelText("Hints for Approach 1")).toBeTruthy();
    click("Get first hint");
    await screen.findByText("brute-force hint 1");
    click("Close selected approach");
    expect(screen.queryByText("brute-force hint 1")).toBeNull();
    expect(screen.queryByRole("button", { name: "Show next hint" })).toBeNull();
    expect(screen.getByLabelText("Hints for Approach 2")).toBeTruthy();
    click("Get first hint");
    await screen.findByText("hash-map hint 1");
    expect(fetchMock.mock.lastCall![0]).toBe("http://localhost:8000/api/problems/two-sum/hints");
  });

  it.each(["success", "error"])("ignores a late alternative-hint %s after collapsing the approach", async (outcome) => {
    await mount();
    click("Approach 1");
    let resolve!: (value: Response) => void;
    let reject!: (reason: Error) => void;
    fetchMock.mockImplementationOnce(() => new Promise((yes, no) => { resolve = yes; reject = no; }));
    click("Get first hint");
    const signal = fetchMock.mock.lastCall![1].signal;
    click("Approach 1");
    expect(signal.aborted).toBe(true);
    await act(async () => {
      if (outcome === "success") resolve(json(hints("brute-force")));
      else reject(new Error("Old connection failed"));
    });
    expect(screen.queryByText("brute-force hint 1")).toBeNull();
    expect(screen.queryByRole("button", { name: "Retry loading hints" })).toBeNull();
    click("Get first hint");
    await screen.findByText("hash-map hint 1");
  });

  it("reset hides next-hint controls and explicitly restarts from cached hint one", async () => {
    await mount();
    click("Get first hint");
    await screen.findByText("hash-map hint 1");
    click("Show next hint");
    click("Reset revealed hints");
    expect(screen.queryByRole("button", { name: "Show next hint" })).toBeNull();
    click("Get first hint");
    await screen.findByText("hash-map hint 1");
    expect(screen.queryByText("hash-map hint 2")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

describe("solution language changes", () => {
  it("clears the old code, waits for an explicit request, and labels the new answer", async () => {
    await mount();
    click("Approach 1");
    click("Generate answer in Python");
    await screen.findByText("python example code");
    expect(document.querySelector(".code-language")?.textContent).toBe("Python");
    chooseLanguage("java");
    expect(screen.queryByText("python example code")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    click("Generate answer in Java");
    await screen.findByText("java example code");
    expect(document.querySelector(".code-language")?.textContent).toBe("Java");
  });

  it("cancels an in-flight answer when changing language and ignores its late result", async () => {
    await mount();
    click("Approach 1");
    let resolve!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((yes) => { resolve = yes; }));
    click("Generate answer in Python");
    const signal = fetchMock.mock.lastCall![1].signal;
    chooseLanguage("javascript");
    expect(signal.aborted).toBe(true);
    await act(async () => resolve(json(solution("python"))));
    expect(screen.queryByText("python example code")).toBeNull();
    click("Generate answer in JavaScript");
    await screen.findByText("javascript example code");
  });

  it("clears an old-language error and retry context on language change", async () => {
    await mount();
    click("Approach 1");
    fetchMock.mockRejectedValueOnce(new Error("Offline"));
    click("Generate answer in Python");
    await screen.findByRole("button", { name: "Retry", exact: true });
    chooseLanguage("cpp");
    expect(screen.queryByRole("button", { name: "Retry", exact: true })).toBeNull();
    click("Generate answer in C++");
    await screen.findByText("cpp example code");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  });
});
