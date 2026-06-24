import { useEffect, useState } from "react";
import { useActiveProblem } from "./useActiveProblem";

const leetCodeProblemsUrl = "https://leetcode.com/problemset/";
const themeStorageKey = "leetcoach-theme";

type Theme = "light" | "dark";

function getInitialTheme(): Theme {
  const savedTheme = window.localStorage.getItem(themeStorageKey);

  if (savedTheme === "light" || savedTheme === "dark") {
    return savedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function openLeetCode() {
  if (typeof chrome !== "undefined" && chrome.tabs?.create) {
    chrome.tabs.create({ url: leetCodeProblemsUrl });
    return;
  }

  window.open(leetCodeProblemsUrl, "_blank", "noopener,noreferrer");
}

export default function App() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const activeProblem = useActiveProblem();

  useEffect(() => {
    window.localStorage.setItem(themeStorageKey, theme);
  }, [theme]);

  return (
    <main className="app-shell" data-theme={theme}>
      <header className="top-bar" aria-label="LeetCoach controls">
        <span className="brand-mark">LeetCoach</span>
        <div className="theme-toggle" aria-label="Theme selector">
          <button
            className={theme === "light" ? "theme-option active" : "theme-option"}
            type="button"
            onClick={() => setTheme("light")}
          >
            Light
          </button>
          <button
            className={theme === "dark" ? "theme-option active" : "theme-option"}
            type="button"
            onClick={() => setTheme("dark")}
          >
            Dark
          </button>
        </div>
      </header>

      <section className="hero-card" aria-labelledby="welcome-title">
        <p className="eyebrow">LeetCoach MVP</p>
        <h1 id="welcome-title">Learn the pattern before the answer.</h1>
        <p className="hero-copy">
          Open a LeetCode problem and LeetCoach will help you recognize the
          pattern, read the signals, and build an interview-style thinking
          process without revealing the final solution.
        </p>

        {activeProblem.status !== "detected" && (
          <button className="primary-action" type="button" onClick={openLeetCode}>
            Open LeetCode
          </button>
        )}
      </section>

      {activeProblem.status === "detected" ? (
        <section className="status-card detected" aria-labelledby="status-title">
          <div className="status-dot" aria-hidden="true" />
          <div>
            <h2 id="status-title">Problem page detected</h2>
            <p>
              Connected to
              <span className="inline-code"> {activeProblem.slug}</span>.
            </p>
          </div>
        </section>
      ) : (
        <section className="status-card" aria-labelledby="status-title">
          <div className="status-dot" aria-hidden="true" />
          <div>
            <h2 id="status-title">
              {activeProblem.status === "checking"
                ? "Checking active tab"
                : "Waiting for a problem page"}
            </h2>
            <p>
              For this milestone, LeetCoach targets pages like
              <span className="inline-code"> leetcode.com/problems/two-sum/</span>.
            </p>
          </div>
        </section>
      )}

      <section className="guide-card" aria-labelledby="guide-title">
        {activeProblem.status === "detected" ? (
          <>
            <h2 id="guide-title">Pattern analysis coming next</h2>
            <p>
              LeetCoach can now identify the active problem. The next milestone
              will connect this slug to local pattern data and guided thinking
              steps.
            </p>
          </>
        ) : (
          <>
            <h2 id="guide-title">What this panel will show</h2>
            <ol>
              <li>Problem identity detected from the current LeetCode tab.</li>
              <li>Pattern classification from the local backend database.</li>
              <li>Guided thinking steps from the mock AI provider.</li>
            </ol>
          </>
        )}
      </section>
    </main>
  );
}
