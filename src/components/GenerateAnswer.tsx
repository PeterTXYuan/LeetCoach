import type { SolutionLanguage } from "../api/approachSolution";
import type { GuidanceWarning } from "../api/guidanceBundle";
import type { ApproachSolutionState } from "../hooks/useApproachSolution";

type GenerateAnswerProps = {
  solutionState: ApproachSolutionState;
  language: SolutionLanguage;
  onGenerate: () => void;
  onRetry: () => void;
  onRegenerate: () => void;
  regenerationStatus: { status: "idle" | "loading" | "error"; message?: string } | null;
  onLanguageChange: (language: SolutionLanguage) => void;
  onHide: () => void;
  verification?: { status: "PASS" | "FAIL" | "NOT_RUN"; summary: string };
  warnings?: GuidanceWarning[];
};

const languageOptions: Array<{
  value: SolutionLanguage;
  label: string;
}> = [
  { value: "python", label: "Python" },
  { value: "java", label: "Java" },
  { value: "javascript", label: "JavaScript" },
  { value: "cpp", label: "C++" }
];

export function GenerateAnswer({
  solutionState,
  language,
  onGenerate,
  onRetry,
  onRegenerate,
  regenerationStatus,
  onLanguageChange,
  onHide,
  verification,
  warnings
}: GenerateAnswerProps) {
  const isLoading = solutionState.status === "loading" || regenerationStatus?.status === "loading";
  const visibleWarnings = warnings?.filter((warning) =>
    warning.scope === "solution" || warning.scope === "bundle") ?? [];

  return (
    <section className="generate-answer" aria-labelledby="generate-answer-title">
      <div className="section-heading-row">
        <h2 id="generate-answer-title">Generate Answer</h2>
        {solutionState.status === "success" && (
          <button className="text-action" type="button" onClick={onHide}>Hide answer</button>
        )}
      </div>
      <p className="section-copy">
        Reveal the complete solution for the selected approach when you are ready.
      </p>

      <label className="field-label" htmlFor="solution-language">
        Language
      </label>
      <div className="language-select-control">
        <select
          id="solution-language"
          className="language-select"
          value={language}
          onChange={(event) => {
            onLanguageChange(event.target.value as SolutionLanguage);
          }}
        >
          {languageOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <svg
          className="language-select-chevron"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </div>

      <button
        className="primary-action generate-button"
        type="button"
        disabled={isLoading}
        aria-label={`Generate answer in ${getLanguageLabel(language)}`}
        onClick={onGenerate}
      >
        {isLoading ? "Generating answer..." : "Generate answer"}
      </button>

      {solutionState.status === "loading" && (
        <p className="analysis-message" role="status">
          Generating approach-specific answer...
        </p>
      )}

      {solutionState.status === "not_found" && (
        <p className="analysis-message" role="alert">
          This problem or approach is not available in the local LeetCoach
          dataset yet.
        </p>
      )}

      {solutionState.status === "unsupported_language" && (
        <p className="analysis-message" role="alert">
          This language is not supported by the local LeetCoach backend.
        </p>
      )}

      {solutionState.status === "error" && (
        <div className="answer-error" role="alert">
          <p>{solutionState.message}</p>
          <button className="secondary-action" type="button" onClick={onRetry}>
            Retry
          </button>
        </div>
      )}

      {solutionState.status === "success" && (
        <article
          className="generated-answer reveal-motion"
          aria-label="Generated answer"
        >
          <p className="answer-warning" role="note">
            {solutionState.response.warning}
          </p>
          {visibleWarnings.length > 0 && (
            <div className="guidance-feedback" role="note" aria-label="Full answer warnings">
              <strong>Review this generated answer before using it.</strong>
              <ul>{visibleWarnings.map((warning) =>
                <li key={`${warning.scope}:${warning.code}`}>{warning.message}</li>)}</ul>
            </div>
          )}
          {verification && <p className="section-copy" role="note">
            Representative checks: {verification.status === "PASS" ? "passed" :
              verification.status === "NOT_RUN" ? "not tested" : "failed"}. {verification.summary}
          </p>}
          <pre className="code-block">
            <span className="code-language">{getLanguageLabel(solutionState.response.language)}</span>
            <code>{solutionState.response.code}</code>
          </pre>
          <dl className="solution-details">
            <div>
              <dt>Explanation</dt>
              <dd>{solutionState.response.explanation}</dd>
            </div>
            <div>
              <dt>Time Complexity</dt>
              <dd>{solutionState.response.timeComplexity}</dd>
            </div>
            <div>
              <dt>Space Complexity</dt>
              <dd>{solutionState.response.spaceComplexity}</dd>
            </div>
          </dl>
          <button className="secondary-action" type="button" onClick={onRegenerate} disabled={isLoading}>
            {regenerationStatus?.status === "loading" ? "Regenerating answer..." : "Regenerate answer"}
          </button>
          {verification && <p className="section-copy">Regenerating refreshes the full answer and all three Starter Code levels together.</p>}
          {regenerationStatus?.status === "loading" && (
            <p className="analysis-message" role="status">Generating a new answer...</p>
          )}
          {regenerationStatus?.status === "error" && (
            <p className="analysis-message" role="alert">{regenerationStatus.message}</p>
          )}
        </article>
      )}
    </section>
  );
}

function getLanguageLabel(language: SolutionLanguage) {
  return (
    languageOptions.find((option) => option.value === language)?.label ??
    language
  );
}
