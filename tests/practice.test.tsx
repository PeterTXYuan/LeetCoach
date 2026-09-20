// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { PracticePanel } from "../src/components/PracticePanel";
import { fetchRelatedProblems } from "../src/api/relatedProblems";

const problem = { slug: "contains-duplicate", title: "Contains Duplicate", difficulty: "Easy", reason: "Remember seen values." };
const related = (slug = "two-sum") => ({ slug, easier: [{ ...problem, slug: "running-sum-of-1d-array", title: "Running Sum of 1d Array" }], similar: [problem], harder: [{ slug: "3sum", title: "3Sum", difficulty: "Medium" }] });
const json = (data: unknown, status = 200) => ({ ok: status === 200, status, json: async () => data } as Response);
const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset().mockResolvedValue(json(related()));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it("fetches only when active, renders all groups, and reuses loaded data on return", async () => {
  const view = render(<PracticePanel slug="two-sum" isActive={false} />);
  expect(fetchMock).not.toHaveBeenCalled();
  view.rerender(<PracticePanel slug="two-sum" isActive />);
  expect(screen.getByRole("status").textContent).toContain("Loading");
  await screen.findByRole("article", { name: "Contains Duplicate" });
  for (const [group, title] of [["Easier", "Running Sum of 1d Array"], ["Similar", "Contains Duplicate"], ["Harder", "3Sum"]]) {
    const region = screen.getByRole("region", { name: group });
    expect(within(region).getByRole("article", { name: title })).toBeTruthy();
    expect(within(region).getByRole("button", { name: `Open Problem: ${title}` })).toBeTruthy();
  }
  expect(fetchMock.mock.lastCall![0]).toBe("http://localhost:8000/api/problems/two-sum/related");
  view.rerender(<PracticePanel slug="two-sum" isActive={false} />);
  view.rerender(<PracticePanel slug="two-sum" isActive />);
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("clears old cards on problem change and waits for Practice activation to fetch", async () => {
  const view = render(<PracticePanel slug="two-sum" isActive />);
  await screen.findByRole("article", { name: "Contains Duplicate" });
  view.rerender(<PracticePanel slug="valid-parentheses" isActive={false} />);
  expect(screen.queryByRole("article")).toBeNull();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  fetchMock.mockResolvedValueOnce(json({ slug: "valid-parentheses", easier: [], similar: [], harder: [] }));
  view.rerender(<PracticePanel slug="valid-parentheses" isActive />);
  await screen.findByText("No easier problems listed yet.");
  expect(fetchMock.mock.lastCall![0]).toContain("/valid-parentheses/related");
});

it.each(["inactive", "slug", "unmount"])("cancels a pending request and ignores its late response after %s", async (change) => {
  let resolve!: (response: Response) => void;
  fetchMock.mockImplementationOnce(() => new Promise((yes) => { resolve = yes; }));
  const view = render(<PracticePanel slug="two-sum" isActive />);
  const signal = fetchMock.mock.lastCall![1].signal;
  if (change === "inactive") view.rerender(<PracticePanel slug="two-sum" isActive={false} />);
  if (change === "slug") {
    fetchMock.mockResolvedValueOnce(json({ slug: "valid-parentheses", easier: [], similar: [], harder: [] }));
    view.rerender(<PracticePanel slug="valid-parentheses" isActive />);
  }
  if (change === "unmount") view.unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => resolve(json(related())));
  expect(screen.queryByRole("article")).toBeNull();
  if (change === "inactive") {
    view.rerender(<PracticePanel slug="two-sum" isActive />);
    await screen.findByRole("article", { name: "Contains Duplicate" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  }
});

it("shows not-found feedback for unseeded problems", async () => {
  fetchMock.mockResolvedValueOnce(json({}, 404));
  render(<PracticePanel slug="not-seeded" isActive />);
  await screen.findByText("Related problems are not available for this problem yet.");
  expect(screen.queryByRole("article")).toBeNull();
});

it("retries failed requests and renders empty groups without failing", async () => {
  fetchMock.mockRejectedValueOnce(new Error("Offline"));
  render(<PracticePanel slug="two-sum" isActive />);
  await screen.findByRole("alert");
  fetchMock.mockResolvedValueOnce(json({ slug: "two-sum", easier: [], similar: [], harder: [] }));
  fireEvent.click(screen.getByRole("button", { name: "Retry related problems" }));
  await screen.findByText("No easier problems listed yet.");
  expect(screen.getByText("No similar problems listed yet.")).toBeTruthy();
  expect(screen.getByText("No harder problems listed yet.")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it.each([true, false])("opens the canonical LeetCode URL (Chrome API available: %s)", async (hasChrome) => {
  const create = vi.fn();
  vi.stubGlobal("chrome", hasChrome ? { tabs: { create } } : undefined);
  const open = vi.spyOn(window, "open").mockReturnValue(null);
  render(<PracticePanel slug="two-sum" isActive />);
  fireEvent.click(await screen.findByRole("button", { name: "Open Problem: 3Sum" }));
  if (hasChrome) {
    expect(create).toHaveBeenCalledWith({ url: "https://leetcode.com/problems/3sum/" });
    expect(open).not.toHaveBeenCalled();
  } else expect(open).toHaveBeenCalledWith("https://leetcode.com/problems/3sum/", "_blank", "noopener,noreferrer");
});

it.each([
  { ...related(), slug: "wrong-problem" },
  { ...related(), easier: null },
  { ...related(), similar: [{ ...problem, slug: "../bad" }] },
  { ...related(), similar: [{ ...problem, difficulty: "Unknown" }] },
  { ...related(), similar: [{ ...problem, reason: 42 }] }
])("rejects invalid related-problem responses %#", async (data) => {
  fetchMock.mockResolvedValueOnce(json(data));
  await expect(fetchRelatedProblems("two-sum")).rejects.toThrow();
});

it("reports server errors instead of displaying incomplete cards", async () => {
  fetchMock.mockResolvedValueOnce(json({}, 500));
  render(<PracticePanel slug="two-sum" isActive />);
  await screen.findByRole("alert");
  expect(screen.queryByRole("article")).toBeNull();
});
