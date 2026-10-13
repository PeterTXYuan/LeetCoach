// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import App from "../src/App";
import { normalizeProblemAnalysis } from "../src/api/problemAnalysis";
import { RecognitionSignals } from "../src/components/RecognitionSignals";

const signals = { quote: "A statement excerpt", bullets: ["A simple clue.", "Another clue."] };
const approaches = [
  { id: "hash-map", name: "Hash Map", isPrimary: true, recognitionSignals: signals },
  { id: "brute-force", name: "Brute Force", isPrimary: false,
    recognitionSignals: { quote: "A different excerpt", bullets: ["A pair clue.", "A baseline clue."] } }
].map((a, i) => ({ ...a, displayOrder: i + 1, pattern: a.name, summary: "Summary", thinkingSteps: ["Think first"] }));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const click = (name: string) => fireEvent.click(screen.getByRole("button", { name, exact: true }));

it("is absent without a selection, follows canonical IDs, sits between Summary and Generate Answer, and resets on switch or close", async () => {
  localStorage.setItem("leetcoach-theme", "light");
  const events = { addListener: vi.fn(), removeListener: vi.fn() };
  vi.stubGlobal("chrome", { tabs: { query: vi.fn().mockResolvedValue([{ url: "https://leetcode.com/problems/two-sum/" }]), onActivated: events, onUpdated: events } });
  const fetchMock = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ slug: "two-sum", approaches }) }));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await screen.findByRole("button", { name: "Approach 1" });
  expect(screen.queryByRole("region", { name: "Recognition Signals" })).toBeNull();
  click("Approach 1");
  const card = screen.getByRole("region", { name: "Recognition Signals" });
  expect(card.parentElement).toBe(screen.getByRole("region", { name: "Solution strategies" }));
  expect(card.previousElementSibling?.classList.contains("selected-approach")).toBe(true);
  expect(card.nextElementSibling?.classList.contains("generate-answer")).toBe(true);
  expect(card.querySelector(".recognition-icon")).not.toBeNull();
  expect(card.querySelector(".hint-approach-badge")).toBeNull();
  expect(screen.queryByText("A simple clue.")).toBeNull();
  expect(screen.queryByText(/A statement excerpt/)).toBeNull();
  expect(screen.getByRole("button", { name: "Reveal recognition signals" }).getAttribute("aria-expanded")).toBe("false");
  click("Reveal recognition signals");
  expect(screen.getByText("A simple clue.")).toBeTruthy();
  expect(screen.getByText(/A statement excerpt/)).toBeTruthy();
  click("Hide recognition signals");
  expect(screen.queryByText("A simple clue.")).toBeNull();
  click("Reveal recognition signals");
  click("Approach 2");
  expect(screen.queryByText("A simple clue.")).toBeNull();
  expect(screen.queryByText("A pair clue.")).toBeNull();
  click("Reveal recognition signals");
  expect(screen.getByText("A pair clue.")).toBeTruthy();
  expect(screen.getByText(/A different excerpt/)).toBeTruthy();
  click("Close selected approach");
  expect(screen.queryByRole("region", { name: "Recognition Signals" })).toBeNull();
  click("Approach 2");
  expect(screen.queryByText("A pair clue.")).toBeNull();
  click("Reveal recognition signals");
  // A different slug must not reuse signals even if its approach IDs overlap.
  vi.mocked(chrome.tabs.query).mockResolvedValue([{ url: "https://leetcode.com/problems/valid-parentheses/" }] as chrome.tabs.Tab[]);
  fetchMock.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ slug: "valid-parentheses", approaches }) });
  const refresh = vi.mocked(chrome.tabs.onActivated.addListener).mock.calls[0][0];
  await act(async () => refresh({ tabId: 2, windowId: 1 }));
  expect(screen.queryByRole("region", { name: "Recognition Signals" })).toBeNull();
  click("Approach 2");
  expect(screen.queryByText("A pair clue.")).toBeNull();
  expect(fetchMock).toHaveBeenCalledTimes(2); // Analysis only; reveal never fetches.
});

it("renders signals without a quote and exposes an accessible disclosure button", () => {
  function Harness() {
    const [isRevealed, setIsRevealed] = React.useState(false);
    return <RecognitionSignals slug="two-sum" signals={{ bullets: signals.bullets }}
      isRevealed={isRevealed} onToggle={() => setIsRevealed((value) => !value)} />;
  }
  render(<Harness />);
  const button = screen.getByRole("button", { name: "Reveal recognition signals" });
  button.focus();
  expect(document.activeElement).toBe(button);
  click("Reveal recognition signals");
  expect(button.getAttribute("aria-expanded")).toBe("true");
  expect(screen.getAllByRole("listitem")).toHaveLength(2);
  expect(document.querySelector("blockquote")).toBeNull();
});

it("normalizes optional recognition metadata without breaking older analysis responses", () => {
  const result = normalizeProblemAnalysis({ slug: "two-sum", approaches });
  expect(result.approaches[0].recognitionSignals).toEqual(signals);
  const withoutQuote = normalizeProblemAnalysis({ slug: "two-sum", approaches: [{ ...approaches[0], recognitionSignals: { bullets: signals.bullets } }] });
  expect(withoutQuote.approaches[0].recognitionSignals).toEqual({ bullets: signals.bullets });
});

it.each([undefined, null, {}, { bullets: [] }, { bullets: [1, "A clue"] }])("keeps Coach usable when optional metadata is missing or malformed: %j", (recognitionSignals) => {
  const result = normalizeProblemAnalysis({ slug: "two-sum", approaches: [{ ...approaches[0], recognitionSignals }] });
  expect(result.approaches[0].recognitionSignals).toBeUndefined();
  expect(result.approaches[0].id).toBe("hash-map");
});
