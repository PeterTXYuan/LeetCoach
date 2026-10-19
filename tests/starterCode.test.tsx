// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { StarterCode } from "../src/components/StarterCode";
import { fetchStarterCodeBatch, normalizeStarterCodeBatch, starterCodePolicyVersion, type StarterCodeBatchResponse } from "../src/api/starterCode";
import { emptyStarter } from "../src/coachWorkspaceStorage";

const response = (overrides = {}) => ({
  slug: "two-sum", approachId: "hash-map", language: "python",
  isAiGenerated: false, policyVersion: starterCodePolicyVersion,
  level1: "# TODO: starter 1", level2: "# TODO: starter 2", level3: "# TODO: starter 3",
  notice: "Complete the TODOs.", ...overrides
});
const json = (data: unknown, status = 200) => ({ ok: status === 200, status, json: async () => data } as Response);
const fetchMock = vi.fn();
const props = { slug: "two-sum", approachId: "hash-map", approachNumber: 2 };
const click = (name: string | RegExp) => fireEvent.click(screen.getByRole("button", { name }));
const chooseLanguage = (language: string) => fireEvent.change(screen.getByLabelText("Starter language"), { target: { value: language } });

beforeEach(() => {
  fetchMock.mockReset().mockImplementation(async (_url: string, options: RequestInit) => {
    const body = JSON.parse(options.body as string);
    return json(response({ ...body, ...Object.fromEntries([1, 2, 3].map(
      (level) => [`level${level}`, `// TODO: ${body.language} level ${level}`]
    )) }));
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("starter code generation", () => {
  it("labels Level 1 as Kickstart and explains the three teaching depths", () => {
    render(<StarterCode {...props} />);
    click("Get starter code");
    expect(screen.getByRole("button", { name: /Level 1 Kickstart/ })).toBeTruthy();
    expect(screen.getByText(/useful first setup step/)).toBeTruthy();
    click(/Level 2 Guided/);
    expect(screen.getByText(/initial flow/)).toBeTruthy();
    click(/Level 3 Strong Scaffold/);
    expect(screen.getByText(/important decisions and result logic/)).toBeTruthy();
  });

  it.each(["python", "java", "javascript", "cpp"])("generates all %s levels in one request, then switches locally", async (language) => {
    render(<StarterCode {...props} />);
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.queryByRole("button", { name: "Generate Starter Code" })).toBeNull();
    expect(screen.getByRole("button", { name: "Get starter code" }).getAttribute("aria-expanded")).toBe("false");
    click("Get starter code");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Close starter code options" }).getAttribute("aria-expanded")).toBe("true");
    chooseLanguage(language);
    for (const level of [1, 2, 3]) {
      click(new RegExp(`Level ${level}`));
      expect(fetchMock).toHaveBeenCalledTimes(level === 1 ? 0 : 1);
      if (level === 1) expect(screen.queryByRole("article")).toBeNull();
      click("Generate Starter Code");
      await screen.findByText(`// TODO: ${language} level ${level}`);
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(fetchMock.mock.lastCall![0]).toBe("http://localhost:8000/api/problems/two-sum/approaches/hash-map/starter-code/batch");
      expect(JSON.parse(fetchMock.mock.lastCall![1].body)).toEqual({ language });
    }
  });

  it("clears completed code on language changes and supports clear without resetting options", async () => {
    render(<StarterCode {...props} />);
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: python level 1");
    chooseLanguage("java");
    expect(screen.queryByRole("article")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    click(/Level 3/);
    click("Generate Starter Code");
    await screen.findByText("// TODO: java level 3");
    click("Hide starter code");
    expect(screen.queryByRole("article")).toBeNull();
    expect((screen.getByLabelText("Starter language") as HTMLSelectElement).value).toBe("java");
    expect(screen.getByRole("button", { name: /Level 3/ }).getAttribute("aria-pressed")).toBe("true");
  });

  it.each(["language", "approach", "problem", "clear", "hide", "unmount"])("ignores a late response after %s changes", async (change) => {
    const view = render(<StarterCode {...props} />);
    click("Get starter code");
    let resolve!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((yes) => { resolve = yes; }));
    click("Generate Starter Code");
    const signal = fetchMock.mock.lastCall![1].signal;
    if (change === "language") chooseLanguage("java");
    if (change === "approach") view.rerender(<StarterCode {...props} approachId="brute-force" />);
    if (change === "problem") view.rerender(<StarterCode {...props} slug="valid-parentheses" approachId="stack" />);
    if (change === "clear") click("Hide starter code");
    if (change === "hide") click("Close starter code options");
    if (change === "unmount") view.unmount();
    expect(signal.aborted).toBe(true);
    await act(async () => resolve(json(response())));
    expect(screen.queryByRole("article")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    if (change === "hide") {
      click("Get starter code");
      expect(screen.queryByRole("article")).toBeNull();
      expect(fetchMock).toHaveBeenCalledTimes(1);
    }
  });

  it("keeps one pending batch request when the chosen level changes", async () => {
    let resolve!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((yes) => { resolve = yes; }));
    render(<StarterCode {...props} />);
    click("Get starter code");
    click("Generate Starter Code");
    const signal = fetchMock.mock.lastCall![1].signal;
    click(/Level 3/);
    expect(signal.aborted).toBe(false);
    await act(async () => resolve(json(response())));
    expect(await screen.findByText("# TODO: starter 3")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("caches each language batch and preserves every level after a rejected regeneration", async () => {
    render(<StarterCode {...props} />);
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: python level 1");
    chooseLanguage("java");
    click("Generate Starter Code");
    await screen.findByText("// TODO: java level 1");
    chooseLanguage("python");
    click(/Level 3/);
    expect(screen.getByText("// TODO: python level 3")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    fetchMock.mockResolvedValueOnce(json(response({ level3: "" })));
    click("Regenerate starter code");
    await screen.findByText(/Unable to regenerate/);
    for (const level of [1, 2, 3]) {
      click(new RegExp(`Level ${level}`));
      expect(screen.getByText(`// TODO: python level ${level}`)).toBeTruthy();
    }
    chooseLanguage("java");
    expect(screen.getByText("// TODO: java level 3")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("ignores an older completion after a new request for the same combination", async () => {
    let resolveOld!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((yes) => { resolveOld = yes; }));
    render(<StarterCode {...props} />);
    click("Get starter code");
    click("Generate Starter Code");
    click("Hide starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: python level 1");
    await act(async () => resolveOld(json(response({ policyVersion: 7, level1: "Old Policy 7 completion" }))));
    expect(screen.queryByText("Old Policy 7 completion")).toBeNull();
    expect(screen.getByText("// TODO: python level 1")).toBeTruthy();
  });

  it("does not show a Policy 7 batch even if stale in-memory state uses the Policy 8 key", () => {
    render(<StarterCode {...props} saved={{ ...emptyStarter(), isExpanded: true, isVisible: true,
      batches: { "python:8": response({ policyVersion: 7, level1: "Old Policy 7 code" }) as StarterCodeBatchResponse }
    }} />);
    expect(screen.queryByText("Old Policy 7 code")).toBeNull();
    expect(screen.queryByRole("article", { name: "Generated starter code" })).toBeNull();
  });

  it("keeps a Policy 8 batch when regeneration receives an old Policy 7 response", async () => {
    render(<StarterCode {...props} />);
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("// TODO: python level 1");
    fetchMock.mockResolvedValueOnce(json(response({ policyVersion: 7, level1: "Old Policy 7 code" })));
    click("Regenerate starter code");
    await screen.findByText(/Unable to regenerate/);
    expect(screen.queryByText("Old Policy 7 code")).toBeNull();
    for (const level of [1, 2, 3]) {
      click(new RegExp(`Level ${level}`));
      expect(screen.getByText(`// TODO: python level ${level}`)).toBeTruthy();
    }
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it.each([
    [404, /not available/], [400, /not supported/], [422, /not supported/], [500, /Unable to load/]
  ] as const)("shows actionable feedback for HTTP %s", async (status, message) => {
    fetchMock.mockResolvedValueOnce(json({}, status));
    render(<StarterCode {...props} />);
    click("Get starter code");
    click("Generate Starter Code");
    expect((await screen.findByRole("alert")).textContent).toMatch(message);
  });

  it("retries a connection failure with the current choices", async () => {
    render(<StarterCode {...props} />);
    click("Get starter code");
    chooseLanguage("java");
    click(/Level 2/);
    fetchMock.mockRejectedValueOnce(new Error("Offline"));
    click("Generate Starter Code");
    await screen.findByRole("button", { name: "Retry starter code" });
    click("Retry starter code");
    await screen.findByText("// TODO: java level 2");
    expect(JSON.parse(fetchMock.mock.lastCall![1].body)).toEqual({ language: "java" });
  });

  it("labels an offline mock batch truthfully and permits regeneration", async () => {
    fetchMock.mockResolvedValueOnce(json(response({
      level1: "# TODO: offline scaffold", isAiGenerated: false, usedFallback: false,
      notice: "Offline mock starter code."
    })));
    render(<StarterCode {...props} />);
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("# TODO: offline scaffold");
    expect(screen.getByText(/Offline mock starter code/)).toBeTruthy();
    click("Regenerate starter code");
    await screen.findByText("// TODO: python level 1");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("button", { name: "Try AI generation again" })).toBeNull();
  });
});

describe("starter API contract", () => {
  it.each([
    { slug: "other" }, { approachId: "brute-force" }, { language: "java" }
  ])("rejects mismatched response context %j", async (mismatch) => {
    fetchMock.mockResolvedValueOnce(json(response(mismatch)));
    await expect(fetchStarterCodeBatch("two-sum", "hash-map", "python")).rejects.toThrow("does not match");
  });
  it.each([null, {}, response({ level1: null }), response({ language: "ruby" }), response({ level2: "" }), response({ usedFallback: "yes" }), response({ policyVersion: 7 }), response({ policyVersion: 6 }), response({ level3: "# TODO: starter 1" })])("rejects malformed data %j", (data) => {
    expect(() => normalizeStarterCodeBatch(data)).toThrow("Invalid starter code");
  });
});

it("places Starter Code between Hints and Solution strategies and uses canonical IDs regardless of order", async () => {
  localStorage.setItem("leetcoach-theme", "light");
  const events = { addListener: vi.fn(), removeListener: vi.fn() };
  vi.stubGlobal("chrome", { tabs: { query: async () => [{ url: "https://leetcode.com/problems/two-sum/" }], onActivated: events, onUpdated: events } });
  const approaches = [
    { id: "hash-map", isPrimary: true }, { id: "brute-force", isPrimary: false }
  ].map((a, i) => ({ ...a, name: a.id, pattern: "Pattern", summary: "Summary", displayOrder: i + 1, thinkingSteps: [] }));
  fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
    if (!url.endsWith("/guidance")) return json({ slug: "two-sum", approaches });
    return json({ ...response({ ...JSON.parse(options!.body as string),
        approachId: url.includes("/brute-force/") ? "brute-force" : "hash-map" }),
      policyVersion: 9, generationId: "fixture", kind: "linked", isAiGenerated: true,
      solution: { code: "complete", explanation: "explain", timeComplexity: "O(n)", spaceComplexity: "O(n)" },
      verification: { status: "NOT_RUN", summary: "Test fixture" } });
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Starter Code" });
  const cards = document.querySelector(".analysis-stack")!.children;
  expect(Array.from(cards).map((e) => e.className)).toEqual(["hint-panel", "starter-card", "strategy-card"]);
  expect(screen.getByLabelText("Starter code for Approach 1")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  click("Get starter code");
  click("Generate Starter Code");
  await screen.findByRole("article", { name: "Generated starter code" });
  expect(fetchMock.mock.lastCall![0]).toContain("/hash-map/guidance");
  click(/^Approach 2$/);
  expect(screen.queryByRole("article", { name: "Generated starter code" })).toBeNull();
  expect(screen.getByLabelText("Starter code for Approach 2")).toBeTruthy();
  click("Get starter code");
  click("Generate Starter Code");
  await screen.findByRole("article", { name: "Generated starter code" });
  expect(fetchMock.mock.lastCall![0]).toContain("/brute-force/guidance");
  click("Close selected approach");
  expect(screen.queryByRole("article", { name: "Generated starter code" })).toBeNull();
  expect(screen.getByRole("button", { name: "Get starter code" })).toBeTruthy();
  expect(screen.getByLabelText("Starter code for Approach 1")).toBeTruthy();
  const requestsBeforeReturn = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/guidance")).length;
  click(/^Approach 2$/);
  expect(screen.queryByRole("article", { name: "Generated starter code" })).toBeNull();
  click("Get starter code");
  click("Generate Starter Code");
  expect(screen.getByRole("article", { name: "Generated starter code" })).toBeTruthy();
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/guidance")).length).toBe(requestsBeforeReturn);
  click("Close selected approach");
  expect(within(screen.getByRole("region", { name: "Hints" })).getByRole("button", { name: "Get first hint" })).toBeTruthy();
});
