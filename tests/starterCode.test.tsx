// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../src/App";
import { StarterCode } from "../src/components/StarterCode";
import { fetchStarterCode, normalizeStarterCode } from "../src/api/starterCode";

const response = (overrides = {}) => ({
  slug: "two-sum", approachId: "hash-map", language: "python", level: 1,
  levelName: "Kickstart", isAiGenerated: false, policyVersion: 5,
  code: "# TODO: starter", notice: "Complete the TODOs.", ...overrides
});
const json = (data: unknown, status = 200) => ({ ok: status === 200, status, json: async () => data } as Response);
const fetchMock = vi.fn();
const props = { slug: "two-sum", approachId: "hash-map", approachNumber: 2 };
const click = (name: string | RegExp) => fireEvent.click(screen.getByRole("button", { name }));
const chooseLanguage = (language: string) => fireEvent.change(screen.getByLabelText("Starter language"), { target: { value: language } });

beforeEach(() => {
  fetchMock.mockReset().mockImplementation(async (_url: string, options: RequestInit) => {
    const body = JSON.parse(options.body as string);
    return json(response({ ...body, code: `// TODO: ${body.language} level ${body.level}` }));
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

  it.each(["python", "java", "javascript", "cpp"])("requests %s at each level only after Generate", async (language) => {
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
      expect(fetchMock).toHaveBeenCalledTimes(level - 1);
      expect(screen.queryByRole("article")).toBeNull();
      click("Generate Starter Code");
      await screen.findByText(`// TODO: ${language} level ${level}`);
      expect(fetchMock.mock.lastCall![0]).toBe("http://localhost:8000/api/problems/two-sum/approaches/hash-map/starter-code");
      expect(JSON.parse(fetchMock.mock.lastCall![1].body)).toEqual({ language, level });
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

  it.each(["language", "level", "approach", "problem", "clear", "hide", "unmount"])("ignores a late response after %s changes", async (change) => {
    const view = render(<StarterCode {...props} />);
    click("Get starter code");
    let resolve!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise((yes) => { resolve = yes; }));
    click("Generate Starter Code");
    const signal = fetchMock.mock.lastCall![1].signal;
    if (change === "language") chooseLanguage("java");
    if (change === "level") click(/Level 2/);
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
    expect(JSON.parse(fetchMock.mock.lastCall![1].body)).toEqual({ language: "java", level: 2 });
  });

  it("shows a usable offline fallback and permits an explicit AI retry", async () => {
    fetchMock.mockResolvedValueOnce(json(response({
      code: "# TODO: offline scaffold", isAiGenerated: false, usedFallback: true,
      notice: "AI starter code could not be used. Showing an offline scaffold."
    })));
    render(<StarterCode {...props} />);
    click("Get starter code");
    click("Generate Starter Code");
    await screen.findByText("# TODO: offline scaffold");
    expect(screen.getByText(/Showing an offline scaffold/)).toBeTruthy();
    click("Try AI generation again");
    await screen.findByText("// TODO: python level 1");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("button", { name: "Try AI generation again" })).toBeNull();
  });
});

describe("starter API contract", () => {
  it.each([
    { slug: "other" }, { approachId: "brute-force" }, { language: "java" }, { level: 2 }
  ])("rejects mismatched response context %j", async (mismatch) => {
    fetchMock.mockResolvedValueOnce(json(response(mismatch)));
    await expect(fetchStarterCode("two-sum", "hash-map", "python", 1)).rejects.toThrow("does not match");
  });
  it.each([null, {}, response({ level: "1" }), response({ language: "ruby" }), response({ code: "" }), response({ usedFallback: "yes" }), response({ policyVersion: "2" })])("rejects malformed data %j", (data) => {
    expect(() => normalizeStarterCode(data)).toThrow("Invalid starter code");
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
    if (!url.endsWith("/starter-code")) return json({ slug: "two-sum", approaches });
    return json(response({ ...JSON.parse(options!.body as string), approachId: url.includes("/brute-force/") ? "brute-force" : "hash-map" }));
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
  expect(fetchMock.mock.lastCall![0]).toContain("/hash-map/starter-code");
  click(/^Approach 2$/);
  expect(screen.queryByRole("article", { name: "Generated starter code" })).toBeNull();
  expect(screen.getByLabelText("Starter code for Approach 2")).toBeTruthy();
  click("Get starter code");
  click("Generate Starter Code");
  await screen.findByRole("article", { name: "Generated starter code" });
  expect(fetchMock.mock.lastCall![0]).toContain("/brute-force/starter-code");
  click("Close selected approach");
  expect(screen.queryByRole("article", { name: "Generated starter code" })).toBeNull();
  expect(screen.getByRole("button", { name: "Get starter code" })).toBeTruthy();
  expect(screen.getByLabelText("Starter code for Approach 1")).toBeTruthy();
  const requestsBeforeReturn = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/starter-code")).length;
  click(/^Approach 2$/);
  expect(screen.queryByRole("article", { name: "Generated starter code" })).toBeNull();
  click("Get starter code");
  click("Generate Starter Code");
  expect(screen.getByRole("article", { name: "Generated starter code" })).toBeTruthy();
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/starter-code")).length).toBe(requestsBeforeReturn);
  click("Close selected approach");
  expect(within(screen.getByRole("region", { name: "Hints" })).getByRole("button", { name: "Get first hint" })).toBeTruthy();
});
