import { useEffect, useState } from "react";
import {
  type ProblemApproach,
  unavailableProblemMessage
} from "./api/problemAnalysis";
import { useActiveProblem } from "./useActiveProblem";
import { useProblemAnalysis } from "./useProblemAnalysis";

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
  const { analysisState: problemAnalysis, retry: retryProblemAnalysis } =
    useProblemAnalysis(
    activeProblem.status === "detected" ? activeProblem.slug : undefined
  );

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

      {activeProblem.status !== "detected" && (
        <section className="hero-card" aria-labelledby="welcome-title">
          <p className="eyebrow">LeetCoach MVP</p>
          <h1 id="welcome-title">Learn the pattern before the answer.</h1>
          <p className="hero-copy">
            Open a LeetCode problem and LeetCoach will help you recognize the
            pattern, read the signals, and build an interview-style thinking
            process without revealing the final solution.
          </p>

          <button className="primary-action" type="button" onClick={openLeetCode}>
            Open LeetCode
          </button>
        </section>
      )}

      {activeProblem.status === "detected" ? (
        <section className="problem-card detected" aria-labelledby="problem-title">
          <div className="problem-heading-row">
            <div
              className="status-dot"
              aria-label="LeetCode problem page detected"
              role="img"
            />
            <h2 id="problem-title" className="problem-title">
              {activeProblem.title}
            </h2>
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
          <AnalysisContent
            analysisState={problemAnalysis}
            onRetry={retryProblemAnalysis}
            problemSlug={activeProblem.slug}
          />
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

type AnalysisContentProps = {
  analysisState: ReturnType<typeof useProblemAnalysis>["analysisState"];
  onRetry: () => void;
  problemSlug: string;
};

function AnalysisContent({
  analysisState,
  onRetry,
  problemSlug
}: AnalysisContentProps) {
  const [selectedApproachId, setSelectedApproachId] = useState<string | null>(
    null
  );
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);

  useEffect(() => {
    setSelectedApproachId(null);
    setIsThinkingExpanded(false);
  }, [problemSlug]);

  if (analysisState.status === "loading") {
    return <p className="analysis-message">Loading pattern analysis...</p>;
  }

  if (analysisState.status === "not_found") {
    return <p className="analysis-message">{unavailableProblemMessage}</p>;
  }

  if (analysisState.status === "error") {
    return (
      <>
        <p className="analysis-message">
          Unable to connect to the local LeetCoach backend.
        </p>
        <button className="secondary-action" type="button" onClick={onRetry}>
          Retry
        </button>
      </>
    );
  }

  if (analysisState.status !== "success") {
    return null;
  }

  const selectedApproach =
    analysisState.analysis.approaches.find(
      (approach) => approach.id === selectedApproachId
    ) ?? null;

  if (analysisState.analysis.approaches.length === 0) {
    return (
      <p className="analysis-message">
        This problem does not have any approaches in the local LeetCoach dataset
        yet.
      </p>
    );
  }

  return (
    <>
      <h2 id="guide-title">Choose an approach</h2>
      <div className="approach-button-group" aria-label="Available approaches">
        {analysisState.analysis.approaches.map((approach, index) => (
          <button
            className={
              selectedApproachId === approach.id
                ? "approach-button selected"
                : "approach-button"
            }
            key={approach.id}
            type="button"
            onClick={() => {
              setSelectedApproachId(approach.id);
              setIsThinkingExpanded(false);
            }}
          >
            Approach {index + 1}
          </button>
        ))}
      </div>

      {selectedApproach && (
        <SelectedApproach
          approach={selectedApproach}
          isThinkingExpanded={isThinkingExpanded}
          onToggleThinking={() =>
            setIsThinkingExpanded((isExpanded) => !isExpanded)
          }
        />
      )}
    </>
  );
}

type SelectedApproachProps = {
  approach: ProblemApproach;
  isThinkingExpanded: boolean;
  onToggleThinking: () => void;
};

function SelectedApproach({
  approach,
  isThinkingExpanded,
  onToggleThinking
}: SelectedApproachProps) {
  return (
    <section className="selected-approach" aria-label={approach.name}>
      <p className="analysis-label">Selected approach</p>
      <h3 className="approach-title">{approach.name}</h3>
      <dl className="approach-details">
        <div>
          <dt>Pattern</dt>
          <dd>{approach.pattern}</dd>
        </div>
        <div>
          <dt>Summary</dt>
          <dd>{approach.summary}</dd>
        </div>
      </dl>

      <button
        className="secondary-action"
        type="button"
        onClick={onToggleThinking}
      >
        {isThinkingExpanded ? "Hide thinking process" : "Show thinking process"}
      </button>

      {isThinkingExpanded && (
        <ol className="thinking-steps">
          {approach.thinkingSteps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      )}
    </section>
  );
}
