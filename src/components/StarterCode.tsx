import { useState } from "react";
import type { SolutionLanguage } from "../api/approachSolution";
import type { GuidanceLevel } from "../api/starterCode";
import { useStarterCode } from "../hooks/useStarterCode";

const languages: { value: SolutionLanguage; label: string }[] = [
  { value: "python", label: "Python" }, { value: "java", label: "Java" },
  { value: "javascript", label: "JavaScript" }, { value: "cpp", label: "C++" }
];
const levels: { value: GuidanceLevel; label: string; description: string }[] = [
  { value: 1, label: "Minimal", description: "Function signature and a basic scaffold. You write the algorithm." },
  { value: 2, label: "Guided", description: "Important variables and data structures, with the algorithm left to you." },
  { value: 3, label: "Strong Scaffold", description: "Loop and control-flow structure, with key logic still left as TODOs." }
];

type StarterCodeProps = {
  slug: string;
  approachId: string | null;
  approachNumber?: number;
};

export function StarterCode({ slug, approachId, approachNumber }: StarterCodeProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [language, setLanguage] = useState<SolutionLanguage>("python");
  const [level, setLevel] = useState<GuidanceLevel>(1);
  const { state, generate, clear } = useStarterCode({ slug, approachId, language, level });

  return (
    <section className="starter-card" aria-labelledby="starter-code-title">
      <div className="section-heading-row">
        <div>
          <p className="section-kicker">Build it yourself</p>
          <div className="hint-title-row">
            <h2 id="starter-code-title">Starter Code</h2>
            {approachNumber !== undefined && (
              <span className="hint-approach-badge" aria-label={`Starter code for Approach ${approachNumber}`}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="6" cy="5" r="2" />
                  <circle cx="6" cy="19" r="2" />
                  <circle cx="18" cy="5" r="2" />
                  <path d="M6 7v10M18 7a6 6 0 0 1-6 6H6" />
                </svg>
                Approach {approachNumber}
              </span>
            )}
          </div>
        </div>
        {state.status !== "idle" && (
          <button className="text-action" type="button" onClick={clear}>Clear starter code</button>
        )}
      </div>
      <button className="secondary-action" type="button" aria-expanded={isExpanded}
        aria-controls="starter-code-options" onClick={() => {
          if (isExpanded) clear();
          setIsExpanded(!isExpanded);
        }}>
        {isExpanded ? "Hide starter code" : "Get starter code"}
      </button>
      <div id="starter-code-options" hidden={!isExpanded}>
        <p className="section-copy">Choose how much structure to reveal. Each level leaves code for you to complete.</p>
        <label className="field-label" htmlFor="starter-language">Starter language</label>
        <div className="language-select-control">
          <select id="starter-language" className="language-select" value={language}
            onChange={(event) => setLanguage(event.target.value as SolutionLanguage)}>
            {languages.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <svg className="language-select-chevron" width="16" height="16" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>
        <fieldset className="starter-levels" aria-describedby="starter-level-description">
          <legend className="field-label">Guidance level</legend>
          <div className="starter-level-options">
            {levels.map((option) => (
              <button key={option.value} type="button" aria-pressed={level === option.value}
                className={level === option.value ? "starter-level selected" : "starter-level"}
                onClick={() => setLevel(option.value)}>
                <span>Level {option.value}</span>
                <span className="starter-level-name">{option.label}</span>
              </button>
            ))}
          </div>
        </fieldset>
        <p className="starter-level-description" id="starter-level-description">
          {levels.find((option) => option.value === level)?.description}
        </p>
        {!approachId && <p className="analysis-message">Choose an approach to generate starter code.</p>}
        <button className="primary-action" type="button" disabled={!approachId || state.status === "loading"}
          onClick={() => void generate()}>
          {state.status === "loading" ? "Generating starter code..." : "Generate Starter Code"}
        </button>
        {state.status === "loading" && <p className="analysis-message" role="status">Loading your scaffold...</p>}
        {state.status === "not_found" && <p className="analysis-message" role="alert">Starter code is not available for this problem and approach yet.</p>}
        {state.status === "invalid_options" && <p className="analysis-message" role="alert">This language or guidance level is not supported. Choose another option and generate again.</p>}
        {state.status === "error" && (
          <div className="answer-error" role="alert">
            <p>Unable to load starter code. Please try again.</p>
            <button className="secondary-action" type="button" onClick={() => void generate()}>Retry starter code</button>
          </div>
        )}
        {state.status === "success" && (
          <article className="starter-result reveal-motion" aria-label="Generated starter code">
            <p className="starter-notice">{state.response.notice}</p>
            <pre className="code-block">
              <span className="code-language">
                {languages.find((option) => option.value === state.response.language)?.label}
                {` · Level ${state.response.level} — ${state.response.levelName}`}
              </span>
              <code>{state.response.code}</code>
            </pre>
          </article>
        )}
      </div>
    </section>
  );
}
