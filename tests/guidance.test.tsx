// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../src/App";

const approaches = [
  { id: "brute-force", name: "Brute Force", isPrimary: false },
  { id: "hash-map", name: "One-pass Hash Map", isPrimary: true }
].map((a, i) => ({ ...a, pattern: a.name, summary: "Summary", displayOrder: i + 1, thinkingSteps: ["Think first"] }));

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
    if (url.endsWith("/solution")) return json(solution(JSON.parse(options!.body as string).language));
    if (url.endsWith("/hints")) return json(hints(url.includes("/brute-force/") ? "brute-force" : "hash-map"));
    return json({ slug: "two-sum", approaches });
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

async function mount() {
  render(<App />);
  await screen.findByRole("button", { name: "Approach 1" });
}
function click(name: string) { fireEvent.click(screen.getByRole("button", { name, exact: true })); }
function chooseLanguage(language: string) { fireEvent.change(screen.getByLabelText("Language"), { target: { value: language } }); }

describe("canonical hint disclosure", () => {
  it("labels default hints by primary ID and preserves them when selecting that approach", async () => {
    await mount();
    expect(screen.getByLabelText("Hints for Approach 2")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    click("Get first hint");
    await screen.findByText("hash-map hint 1");
    click("Approach 2");
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
