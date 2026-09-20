import { useEffect, useMemo, useState } from "react";
import { AnalysisStatus } from "./components/AnalysisStatus";
import { ApproachDetails } from "./components/ApproachDetails";
import { ApproachSelector } from "./components/ApproachSelector";
import { GenerateAnswer } from "./components/GenerateAnswer";
import { HintPanel } from "./components/HintPanel";
import { ProblemHeader } from "./components/ProblemHeader";
import { SectionNav, type SectionId, type SectionOption } from "./components/SectionNav";
import { StarterCode } from "./components/StarterCode";
import { ThinkingProcess } from "./components/ThinkingProcess";
import { useApproachHints } from "./hooks/useApproachHints";
import { useApproachSolution } from "./hooks/useApproachSolution";
import { useActiveProblem } from "./useActiveProblem";
import { useProblemAnalysis } from "./useProblemAnalysis";

const leetCodeProblemsUrl = "https://leetcode.com/problemset/";
const themeStorageKey = "leetcoach-theme";

const globalSections: SectionOption[] = [
  { id: "progress", label: "Progress" },
  { id: "about", label: "About" }
];
const problemSections: SectionOption[] = [
  { id: "coach", label: "Coach" },
  { id: "practice", label: "Practice" },
  ...globalSections
];

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
  const hasProblem = activeProblem.status === "detected";
  const [activeSection, setActiveSection] = useState<SectionId>("progress");

  useEffect(() => {
    setActiveSection(hasProblem ? "coach" : "progress");
  }, [hasProblem]);
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

      <SectionNav
        sections={hasProblem ? problemSections : globalSections}
        activeSection={activeSection}
        onSelect={setActiveSection}
      />

      {/* Keep Coach mounted across section changes to preserve local UI state. */}
      {activeProblem.status === "detected" && (
        <div className="coach-page" role="tabpanel" id="section-panel-coach"
          aria-labelledby="section-tab-coach" hidden={activeSection !== "coach"} tabIndex={0}>
          <ProblemHeader title={activeProblem.title} />
          <section
            className={
              problemAnalysis.status === "success"
                ? "guide-content"
                : "guide-card"
            }
            aria-label="Problem guidance"
          >
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
          </section>
        </div>
      )}

      {hasProblem && (
        <section className="guide-card section-page" role="tabpanel" id="section-panel-practice"
          aria-labelledby="section-tab-practice" hidden={activeSection !== "practice"} tabIndex={0}>
          <h2>Practice</h2>
          <p>A space to practice what you have learned is coming soon.</p>
        </section>
      )}
      <section className="guide-card section-page" role="tabpanel" id="section-panel-progress"
        aria-labelledby="section-tab-progress" hidden={activeSection !== "progress"} tabIndex={0}>
        <h2>Progress</h2>
        <p>Your learning progress will appear here in a future update.</p>
        {!hasProblem && (
          <>
            <p>{activeProblem.status === "checking"
              ? "Checking the active tab..."
              : "Open a LeetCode problem to use Coach and Practice."}</p>
            <button className="secondary-action" type="button" onClick={openLeetCode}>Open LeetCode</button>
          </>
        )}
      </section>
      <section className="guide-card section-page" role="tabpanel" id="section-panel-about"
        aria-labelledby="section-tab-about" hidden={activeSection !== "about"} tabIndex={0}>
        <h2>About LeetCoach</h2>
        <p>Learn the pattern before the answer. LeetCoach helps you work through LeetCode problems with guidance you reveal at your own pace.</p>
        <ul>
          <li>Reveal hints one step at a time.</li>
          <li>Build your solution with progressive starter code.</li>
          <li>Explore approaches and their thinking process.</li>
          <li>View a full answer when you are ready.</li>
        </ul>
        <p>Guidance currently uses curated examples for a small set of problems. Practice and progress tracking are coming soon.</p>
      </section>
    </main>
  );
}
