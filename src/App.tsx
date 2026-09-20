import { useEffect, useMemo, useState } from "react";
import { AnalysisStatus } from "./components/AnalysisStatus";
import { ApproachDetails } from "./components/ApproachDetails";
import { ApproachSelector } from "./components/ApproachSelector";
import { GenerateAnswer } from "./components/GenerateAnswer";
import { HintPanel } from "./components/HintPanel";
import { ProblemHeader } from "./components/ProblemHeader";
import { StarterCode } from "./components/StarterCode";
import { ThinkingProcess } from "./components/ThinkingProcess";
import { useApproachHints } from "./hooks/useApproachHints";
import { useApproachSolution } from "./hooks/useApproachSolution";
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
  const [selectedApproachId, setSelectedApproachId] = useState<string | null>(
    null
  );
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);
  const activeProblem = useActiveProblem();
  const detectedSlug =
    activeProblem.status === "detected" ? activeProblem.slug : undefined;
  const { analysisState: problemAnalysis, retry: retryProblemAnalysis } =
    useProblemAnalysis(detectedSlug);
  const approaches = problemAnalysis.status === "success"
    ? problemAnalysis.analysis.approaches
    : [];
  const primaryApproachId = approaches.find((approach) => approach.isPrimary)?.id ?? null;
  const approachHints = useApproachHints({
    slug: problemAnalysis.status === "success" ? detectedSlug : undefined,
    selectedApproachId,
    primaryApproachId
  });
  const hintApproachId = approachHints.hintState.status === "success"
    ? approachHints.hintState.response.approachId
    : selectedApproachId ?? primaryApproachId;
  const hintApproachNumber = approaches.findIndex((approach) => approach.id === hintApproachId) + 1;
  const starterApproachId = selectedApproachId ?? primaryApproachId;
  const starterApproachNumber = approaches.findIndex((approach) => approach.id === starterApproachId) + 1;
  const approachSolution = useApproachSolution({
    slug: problemAnalysis.status === "success" ? detectedSlug : undefined,
    approachId: selectedApproachId
  });

  const selectedApproach = useMemo(() => {
    if (problemAnalysis.status !== "success" || !selectedApproachId) {
      return null;
    }

    return (
      problemAnalysis.analysis.approaches.find(
        (approach) => approach.id === selectedApproachId
      ) ?? null
    );
  }, [problemAnalysis, selectedApproachId]);

  useEffect(() => {
    window.localStorage.setItem(themeStorageKey, theme);
  }, [theme]);

  useEffect(() => {
    setSelectedApproachId(null);
    setIsThinkingExpanded(false);
  }, [detectedSlug]);

  const clearSelectedApproach = () => {
    setSelectedApproachId(null);
    setIsThinkingExpanded(false);
    approachHints.resetHints();
  };

  const handleSelectApproach = (approachId: string) => {
    if (approachId === selectedApproachId) {
      clearSelectedApproach();
      return;
    }

    setSelectedApproachId(approachId);
    setIsThinkingExpanded(false);
  };

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
        <ProblemHeader title={activeProblem.title} />
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

      <section
        className={
          activeProblem.status === "detected" && problemAnalysis.status === "success"
            ? "guide-content"
            : "guide-card"
        }
        aria-label="Problem guidance"
      >
        {activeProblem.status === "detected" ? (
          <AnalysisStatus
            analysisState={problemAnalysis}
            onRetry={retryProblemAnalysis}
          >
            {problemAnalysis.status === "success" && (
              <div className="analysis-stack">
                <HintPanel
                  approachNumber={hintApproachNumber || undefined}
                  hintState={approachHints.hintState}
                  onRequestFirstHint={approachHints.requestFirstHint}
                  onResetHints={approachHints.resetHints}
                  onRetryHints={approachHints.retryHints}
                  onShowNextHint={approachHints.showNextHint}
                  visibleHintCount={approachHints.visibleHintCount}
                />
                {problemAnalysis.analysis.slug === detectedSlug && (
                  <StarterCode
                    key={JSON.stringify([detectedSlug, selectedApproachId])}
                    slug={problemAnalysis.analysis.slug}
                    approachId={starterApproachId}
                    approachNumber={starterApproachNumber || undefined}
                  />
                )}
                <section className="strategy-card" aria-label="Solution strategies">
                  <ApproachSelector
                    approaches={problemAnalysis.analysis.approaches}
                    onSelectApproach={handleSelectApproach}
                    selectedApproachId={selectedApproachId}
                  />
                  {selectedApproach && (
                    <>
                      <ApproachDetails
                        approach={selectedApproach}
                        onClose={clearSelectedApproach}
                      />
                      <GenerateAnswer
                        onLanguageChange={approachSolution.resetSolution}
                        onGenerate={approachSolution.generateSolution}
                        onRetry={approachSolution.retrySolution}
                        solutionState={approachSolution.solutionState}
                      />
                      <ThinkingProcess
                        approach={selectedApproach}
                        isExpanded={isThinkingExpanded}
                        onToggle={() =>
                          setIsThinkingExpanded((isExpanded) => !isExpanded)
                        }
                      />
                    </>
                  )}
                </section>
              </div>
            )}
          </AnalysisStatus>
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
