import { useState } from "react";
import type { SolutionLanguage } from "../api/approachSolution";
import type { GuidanceLevel } from "../api/starterCode";
import { emptyStarter, starterResponseKey, type SavedStarter } from "../coachWorkspaceStorage";
import { useStarterCode } from "../hooks/useStarterCode";

const languages: { value: SolutionLanguage; label: string }[] = [
  { value: "python", label: "Python" }, { value: "java", label: "Java" },
  { value: "javascript", label: "JavaScript" }, { value: "cpp", label: "C++" }
];
const levels: { value: GuidanceLevel; label: string; description: string }[] = [
  { value: 1, label: "Kickstart", description: "A useful first setup step for this approach; you design the main algorithm." },
  { value: 2, label: "Guided", description: "More state and an initial flow; you decide the key conditions and updates." },
  { value: 3, label: "Strong Scaffold", description: "Most structure is in place, but important decisions and result logic remain yours." }
];

type StarterCodeProps = {
  slug: string;
  approachId: string | null;
  approachNumber?: number;
  saved?: SavedStarter;
  onSave?: (update: (current: SavedStarter) => SavedStarter) => void;
};

export function StarterCode({ slug, approachId, approachNumber, saved, onSave }: StarterCodeProps) {
  const [localSaved, setLocalSaved] = useState<SavedStarter>(emptyStarter);
  const settings = saved ?? localSaved;
  const updateSettings = (update: (current: SavedStarter) => SavedStarter) => {
    if (onSave) onSave(update);
    else setLocalSaved(update);
  };
  const { language, level, isExpanded } = settings;
  const candidate = settings.responses[starterResponseKey(language, level)];
  const cached = candidate?.slug === slug && candidate.approachId === approachId ? candidate : undefined;
  const { state, generate, clear } = useStarterCode({ slug, approachId, language, level,
    onResult: (response) => updateSettings((current) => ({
      ...current, isVisible: true,
      responses: { ...current.responses, [starterResponseKey(response.language, response.level)]: response }
    }))
  });
  const hideResult = () => {
    clear();
    updateSettings((current) => ({ ...current, isVisible: false }));
  };
  const chooseLanguage = (next: SolutionLanguage) => {
    updateSettings((current) => ({ ...current, language: next,
      isVisible: Boolean(current.responses[starterResponseKey(next, current.level)]) }));
  };
  const chooseLevel = (next: GuidanceLevel) => {
    updateSettings((current) => ({ ...current, level: next,
      isVisible: Boolean(current.responses[starterResponseKey(current.language, next)]) }));
  };
  const handleGenerate = () => {
    if (cached) {
      updateSettings((current) => ({ ...current, isVisible: true }));
    } else void generate();
  };

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
        {(settings.isVisible || state.status !== "idle") && (
          <button className="text-action" type="button" onClick={hideResult}>Hide starter code</button>
        )}
      </div>
      <button className="secondary-action" type="button" aria-expanded={isExpanded}
        aria-controls="starter-code-options" onClick={() => {
          if (isExpanded) hideResult();
          updateSettings((current) => ({ ...current, isExpanded: !current.isExpanded }));
        }}>
        {isExpanded ? "Close starter code options" : "Get starter code"}
      </button>
      <div id="starter-code-options" hidden={!isExpanded}>
        <p className="section-copy">Choose how much structure to reveal. Each level leaves code for you to complete.</p>
        <label className="field-label" htmlFor="starter-language">Starter language</label>
        <div className="language-select-control">
          <select id="starter-language" className="language-select" value={language}
            onChange={(event) => chooseLanguage(event.target.value as SolutionLanguage)}>
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
                onClick={() => chooseLevel(option.value)}>
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
          onClick={handleGenerate}>
          {state.status === "loading" ? "Generating starter code..." : "Generate Starter Code"}
        </button>
        {state.status === "loading" && <p className="analysis-message" role="status">Loading your scaffold...</p>}
        {state.status === "not_found" && <p className="analysis-message" role="alert">Starter code is not available for this problem and approach yet.</p>}
        {state.status === "invalid_options" && <p className="analysis-message" role="alert">This language or guidance level is not supported. Choose another option and generate again.</p>}
        {state.status === "error" && (
          <div className="answer-error" role="alert">
            <p>{settings.isVisible && cached
              ? "Unable to regenerate starter code. Your previous scaffold is still available."
              : "Unable to load starter code. Please try again."}</p>
            {!(settings.isVisible && cached) && (
              <button className="secondary-action" type="button" onClick={() => void generate()}>Retry starter code</button>
            )}
          </div>
        )}
        {settings.isVisible && cached && (
          <article className="starter-result reveal-motion" aria-label="Generated starter code">
            <p className="starter-notice">{cached.notice}</p>
            <pre className="code-block">
              <span className="code-language">
                {languages.find((option) => option.value === cached.language)?.label}
                {` · Level ${cached.level} — ${cached.levelName}`}
              </span>
              <code>{cached.code}</code>
            </pre>
            <button className="secondary-action" type="button" disabled={state.status === "loading"}
              onClick={() => void generate()}>
              {state.status === "loading" ? "Regenerating starter code..." :
                cached.usedFallback ? "Try AI generation again" : "Regenerate starter code"}
            </button>
          </article>
        )}
      </div>
    </section>
  );
}
