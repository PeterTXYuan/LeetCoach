import { useEffect, useMemo, useRef, useState } from "react";
import { AnalysisStatus } from "./components/AnalysisStatus";
import { ApproachDetails } from "./components/ApproachDetails";
import { ApproachSelector } from "./components/ApproachSelector";
import { GenerateAnswer } from "./components/GenerateAnswer";
import { HintPanel } from "./components/HintPanel";
import { ProblemHeader } from "./components/ProblemHeader";
import { PracticePanel } from "./components/PracticePanel";
import { RecognitionSignals } from "./components/RecognitionSignals";
import { SectionNav, type SectionId, type SectionOption } from "./components/SectionNav";
import { StarterCode } from "./components/StarterCode";
import { ThinkingProcess } from "./components/ThinkingProcess";
import { useApproachHints } from "./hooks/useApproachHints";
import { useGuidanceBundle } from "./hooks/useGuidanceBundle";
import { useCoachWorkspaces } from "./hooks/useCoachWorkspaces";
import { collapseWorkspaceDisclosure, emptySolution, emptyStarter } from "./coachWorkspaceStorage";
import { useActiveProblem, type ActiveProblemState } from "./useActiveProblem";
import { useProblemAnalysis, type ProblemAnalysisState } from "./useProblemAnalysis";

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
type DetectedProblem = Extract<ActiveProblemState, { status: "detected" }>;

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
  const hasProblem = activeProblem.status === "detected";
  const [lastDetectedProblem, setLastDetectedProblem] = useState<DetectedProblem | null>(null);
  const [awaySection, setAwaySection] = useState<"progress" | "about" | null>(null);
  const { ready: workspaceReady, workspaceFor, updateWorkspace, updateHints } = useCoachWorkspaces();
  const handledNavigationRevision = useRef(0);

  useEffect(() => {
    if (activeProblem.status !== "detected") return;
    setLastDetectedProblem(activeProblem);
    setAwaySection(null);
  }, [activeProblem]);

  useEffect(() => {
    if (!workspaceReady || activeProblem.status === "checking" ||
        !activeProblem.navigationRevision ||
        handledNavigationRevision.current === activeProblem.navigationRevision) return;
    handledNavigationRevision.current = activeProblem.navigationRevision;
    const slugs = new Set<string>();
    if (lastDetectedProblem && lastDetectedProblem.tabId === activeProblem.tabId) {
      slugs.add(lastDetectedProblem.slug);
    }
    if (activeProblem.status === "detected") slugs.add(activeProblem.slug);
    for (const slug of slugs) updateWorkspace(slug, collapseWorkspaceDisclosure);
  }, [activeProblem, lastDetectedProblem, updateWorkspace, workspaceReady]);

  const workspaceProblem = activeProblem.status === "detected"
    ? activeProblem
    : lastDetectedProblem;
  const workspaceSlug = workspaceProblem?.slug;
  const workspace = workspaceFor(workspaceSlug);
  const activeSection: SectionId = hasProblem
    ? workspace?.activeSection ?? "coach"
    : awaySection ?? (workspace?.activeSection === "about" ? "about" : "progress");
  const showSections = activeProblem.status !== "checking" && (!hasProblem || workspaceReady);

  const handleSelectSection = (section: SectionId) => {
    if (workspaceSlug && workspaceReady) {
      updateWorkspace(workspaceSlug, (current) => current.activeSection === section
        ? current
        : { ...current, activeSection: section });
    }
    if (!hasProblem && (section === "progress" || section === "about")) {
      setAwaySection(section);
    }
  };

  const { analysisState: problemAnalysis, retry: retryProblemAnalysis } =
    useProblemAnalysis(workspaceSlug);
  const visibleProblemAnalysis: ProblemAnalysisState =
    problemAnalysis.status === "success" && problemAnalysis.analysis.slug !== workspaceSlug
      ? { status: "loading" }
      : problemAnalysis;
  const approaches = visibleProblemAnalysis.status === "success"
    ? visibleProblemAnalysis.analysis.approaches
    : [];
  const storedSelectedApproachId = workspace?.selectedApproachId ?? null;
  const selectedApproachId = approaches.some((approach) => approach.id === storedSelectedApproachId)
    ? storedSelectedApproachId
    : null;
  const isThinkingExpanded = workspace?.isThinkingExpanded ?? false;

  useEffect(() => {
    if (!workspaceReady || !workspaceSlug || visibleProblemAnalysis.status !== "success" ||
        !storedSelectedApproachId || selectedApproachId) return;
    updateWorkspace(workspaceSlug, (current) => current.selectedApproachId === storedSelectedApproachId
      ? { ...current, selectedApproachId: null, isThinkingExpanded: false }
      : current);
  }, [workspaceReady, workspaceSlug, visibleProblemAnalysis.status,
    storedSelectedApproachId, selectedApproachId, updateWorkspace]);

  const primaryApproachId = approaches.find((approach) => approach.isPrimary)?.id ?? null;
  const approachHints = useApproachHints({
    slug: workspaceReady && visibleProblemAnalysis.status === "success" ? workspaceSlug : undefined,
    selectedApproachId,
    primaryApproachId,
    hintsByApproach: workspace?.hintsByApproach,
    updateHints,
    disclosureRevision: workspace?.disclosureRevision ?? 0
  });
  const hintApproachId = approachHints.hintState.status === "success"
    ? approachHints.hintState.response.approachId
    : selectedApproachId ?? primaryApproachId;
  const hintApproachNumber = approaches.findIndex((approach) => approach.id === hintApproachId) + 1;
  const starterApproachId = selectedApproachId ?? primaryApproachId;
  const starterApproachNumber = approaches.findIndex((approach) => approach.id === starterApproachId) + 1;
  const guidance = useGuidanceBundle(workspace ?? undefined, updateWorkspace);
  const solutionSaved = selectedApproachId
    ? workspace?.solutionByApproach[selectedApproachId] ?? emptySolution() : emptySolution();
  const solutionLanguage = solutionSaved.language;
  const answerBundle = guidance.bundleFor(selectedApproachId, solutionLanguage);
  const answerStatus = workspaceSlug
    ? guidance.statusFor(workspaceSlug, selectedApproachId, solutionLanguage, "answer") : { status: "idle" as const };
  const answerVisible = Boolean(solutionSaved.visibleByLanguage[solutionLanguage] && answerBundle?.solution);
  const answerResponse = answerBundle?.solution && workspaceSlug && selectedApproachId ? {
    slug: workspaceSlug, approachId: selectedApproachId, language: solutionLanguage,
    isAiGenerated: answerBundle.isAiGenerated,
    warning: answerBundle.kind === "linked"
      ? "Full solution revealed. Try solving the problem yourself before relying on this answer."
      : "Offline curated full answer; it was prepared separately from this starter code.",
    ...answerBundle.solution
  } : null;
  const solutionState = answerVisible && answerResponse
    ? { status: "success" as const, response: answerResponse }
    : answerStatus.status === "loading" ? { status: "loading" as const }
    : answerStatus.status === "not_found" ? { status: "not_found" as const }
    : answerStatus.status === "error" ? { status: "error" as const,
        message: answerStatus.message ?? "Unable to generate guidance. Please retry." }
    : { status: "idle" as const };
  const requestAnswer = (force: boolean) => {
    if (workspaceSlug && selectedApproachId)
      void guidance.request(workspaceSlug, selectedApproachId, solutionLanguage, "answer", force);
  };
  const changeSolutionLanguage = (language: typeof solutionLanguage) => {
    if (!workspaceSlug || !selectedApproachId) return;
    updateWorkspace(workspaceSlug, (current) => {
      const previous = current.solutionByApproach[selectedApproachId] ?? emptySolution();
      return { ...current, solutionByApproach: { ...current.solutionByApproach,
        [selectedApproachId]: { ...previous, language } } };
    });
  };
  const hideAnswer = () => {
    if (!workspaceSlug || !selectedApproachId) return;
    guidance.cancelDisclosure(workspaceSlug, selectedApproachId, solutionLanguage, "answer");
    updateWorkspace(workspaceSlug, (current) => {
      const previous = current.solutionByApproach[selectedApproachId] ?? emptySolution();
      return { ...current,
        solutionByApproach: { ...current.solutionByApproach,
        [selectedApproachId]: { ...previous,
          visibleByLanguage: { ...previous.visibleByLanguage, [solutionLanguage]: false } } } };
    });
  };

  const selectedApproach = useMemo(() => {
    if (visibleProblemAnalysis.status !== "success" || !selectedApproachId) {
      return null;
    }

    return (
      visibleProblemAnalysis.analysis.approaches.find(
        (approach) => approach.id === selectedApproachId
      ) ?? null
    );
  }, [visibleProblemAnalysis, selectedApproachId]);

  useEffect(() => {
    window.localStorage.setItem(themeStorageKey, theme);
  }, [theme]);

  const clearSelectedApproach = () => {
    if (workspaceSlug) updateWorkspace(workspaceSlug, (current) => ({
      ...collapseWorkspaceDisclosure(current), selectedApproachId: null
    }));
  };

  const handleSelectApproach = (approachId: string) => {
    if (approachId === selectedApproachId) {
      clearSelectedApproach();
      return;
    }

    if (workspaceSlug) updateWorkspace(workspaceSlug, (current) => ({
      ...collapseWorkspaceDisclosure(current), selectedApproachId: approachId
    }));
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

      {(activeProblem.status === "checking" || (hasProblem && !workspaceReady))
        ? <p className="analysis-message" role="status">
            {hasProblem ? "Restoring Coach workspace..." : "Checking the active tab..."}
          </p>
        : <SectionNav
            sections={hasProblem ? problemSections : globalSections}
            activeSection={activeSection}
            onSelect={handleSelectSection}
          />}

      {/* Keep the last problem workspace mounted while another browser tab is active. */}
      {workspaceReady && workspaceProblem && (
        <div className="coach-page" role="tabpanel" id="section-panel-coach"
          aria-labelledby="section-tab-coach" hidden={!hasProblem || activeSection !== "coach"} tabIndex={0}>
          <ProblemHeader title={workspaceProblem.title} />
          <section
            className={
              visibleProblemAnalysis.status === "success"
                ? "guide-content"
                : "guide-card"
            }
            aria-label="Problem guidance"
          >
            <AnalysisStatus
              analysisState={visibleProblemAnalysis}
              onRetry={retryProblemAnalysis}
            >
              {visibleProblemAnalysis.status === "success" && (
                <div className="analysis-stack">
                  <HintPanel
                    approachNumber={hintApproachNumber || undefined}
                    hintState={approachHints.hintState}
                    onRequestFirstHint={approachHints.requestFirstHint}
                    onResetHints={approachHints.resetHints}
                    onRetryHints={approachHints.retryHints}
                    onRegenerateHints={approachHints.regenerateHints}
                    regenerationStatus={approachHints.regenerationStatus}
                    onShowNextHint={approachHints.showNextHint}
                    visibleHintCount={approachHints.visibleHintCount}
                  />
                  {visibleProblemAnalysis.analysis.slug === workspaceSlug && (
                    <StarterCode
                      key={JSON.stringify([workspaceSlug, selectedApproachId, workspace?.disclosureRevision])}
                      slug={visibleProblemAnalysis.analysis.slug}
                      approachId={starterApproachId}
                      approachNumber={starterApproachNumber || undefined}
                      saved={starterApproachId ? workspace?.starterByApproach[starterApproachId] ?? emptyStarter() : undefined}
                      linkedBundles={starterApproachId ? workspace?.guidanceByApproach?.[starterApproachId] : undefined}
                      linkedStatus={(language) => guidance.statusFor(workspaceSlug ?? "", starterApproachId, language, "starter")}
                      onRequestLinked={(language, force) => {
                        if (workspaceSlug && starterApproachId)
                          void guidance.request(workspaceSlug, starterApproachId, language, "starter", force);
                      }}
                      onHideLinked={() => {
                        if (workspaceSlug && starterApproachId) {
                          const language = (workspace?.starterByApproach[starterApproachId] ?? emptyStarter()).language;
                          guidance.cancelDisclosure(workspaceSlug, starterApproachId, language, "starter");
                        }
                      }}
                      onSave={(update) => {
                        if (!workspaceSlug || !starterApproachId) return;
                        updateWorkspace(workspaceSlug, (current) => ({
                          ...current,
                          starterByApproach: {
                            ...current.starterByApproach,
                            [starterApproachId]: update(current.starterByApproach[starterApproachId] ?? emptyStarter())
                          }
                        }));
                      }}
                    />
                  )}
                  <section className="strategy-card" aria-label="Solution strategies">
                    <ApproachSelector
                      approaches={visibleProblemAnalysis.analysis.approaches}
                      onSelectApproach={handleSelectApproach}
                      selectedApproachId={selectedApproachId}
                    />
                    {selectedApproach && (
                      <>
                        <ApproachDetails
                          approach={selectedApproach}
                          onClose={clearSelectedApproach}
                        />
                        {selectedApproach.recognitionSignals && visibleProblemAnalysis.analysis.slug === workspaceSlug && (
                          <RecognitionSignals
                            slug={visibleProblemAnalysis.analysis.slug}
                            signals={selectedApproach.recognitionSignals}
                            isRevealed={Boolean(workspace?.recognitionRevealedByApproach[selectedApproach.id])}
                            onToggle={() => workspaceSlug && updateWorkspace(workspaceSlug, (current) => ({
                              ...current,
                              recognitionRevealedByApproach: {
                                ...current.recognitionRevealedByApproach,
                                [selectedApproach.id]: !current.recognitionRevealedByApproach[selectedApproach.id]
                              }
                            }))}
                          />
                        )}
                        <GenerateAnswer
                          language={solutionLanguage}
                          onLanguageChange={changeSolutionLanguage}
                          onGenerate={() => requestAnswer(false)}
                          onRetry={() => requestAnswer(false)}
                          onRegenerate={() => requestAnswer(true)}
                          regenerationStatus={answerVisible && answerStatus.status === "loading"
                            ? { status: "loading" } : answerVisible && answerStatus.status === "error"
                              ? { status: "error", message: answerStatus.message } : null}
                          onHide={hideAnswer}
                          solutionState={solutionState}
                          verification={answerBundle?.verification}
                          warnings={answerBundle?.warnings}
                        />
                        <ThinkingProcess
                          approach={selectedApproach}
                          isExpanded={isThinkingExpanded}
                          onToggle={() => workspaceSlug && updateWorkspace(workspaceSlug,
                            (current) => ({
                              ...current, isThinkingExpanded: !current.isThinkingExpanded
                            }))}
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

      {workspaceReady && workspaceProblem && (
        <section className="practice-page" role="tabpanel" id="section-panel-practice"
          aria-labelledby="section-tab-practice" hidden={!hasProblem || activeSection !== "practice"} tabIndex={0}>
          <ProblemHeader title={workspaceProblem.title} titleId="practice-problem-title" />
          <PracticePanel slug={workspaceProblem.slug} isActive={hasProblem && activeSection === "practice"} />
        </section>
      )}
      <section className="guide-card section-page" role="tabpanel" id="section-panel-progress"
        aria-labelledby="section-tab-progress" hidden={!showSections || activeSection !== "progress"} tabIndex={0}>
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
        aria-labelledby="section-tab-about" hidden={!showSections || activeSection !== "about"} tabIndex={0}>
        <h2>About LeetCoach</h2>
        <p>Learn the pattern before the answer. LeetCoach helps you work through LeetCode problems with guidance you reveal at your own pace.</p>
        <ul>
          <li>Reveal hints one step at a time.</li>
          <li>Build your solution with progressive starter code.</li>
          <li>Explore approaches and their thinking process.</li>
          <li>View a full answer when you are ready.</li>
        </ul>
        <p>Guidance and related practice problems are currently curated for a small set of problems. Progress tracking is coming soon.</p>
      </section>
    </main>
  );
}
