import { useState } from "react";
import type { SolutionLanguage } from "../api/approachSolution";
import type { ApproachSolutionState } from "../hooks/useApproachSolution";

type GenerateAnswerProps = {
  solutionState: ApproachSolutionState;
  onGenerate: (language: SolutionLanguage) => void;
  onRetry: () => void;
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
  onGenerate,
  onRetry
}: GenerateAnswerProps) {
  const [language, setLanguage] = useState<SolutionLanguage>("python");
  const isLoading = solutionState.status === "loading";

  return (
    <section className="generate-answer" aria-labelledby="generate-answer-title">
      <h2 id="generate-answer-title">Generate Answer</h2>
      <p className="section-copy">
        Generate a mock answer for the selected approach only.
      </p>

      <label className="field-label" htmlFor="solution-language">
        Language
      </label>
      <select
        id="solution-language"
        className="language-select"
        value={language}
        onChange={(event) =>
          setLanguage(event.target.value as SolutionLanguage)
        }
      >
        {languageOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <button
        className="primary-action generate-button"
        type="button"
        disabled={isLoading}
        aria-label={`Generate answer in ${getLanguageLabel(language)}`}
        onClick={() => onGenerate(language)}
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
          This language is not supported by the local mock backend yet.
        </p>
      )}

      {solutionState.status === "error" && (
        <div className="answer-error" role="alert">
          <p>Unable to connect to the local LeetCoach backend.</p>
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
          <pre className="code-block">
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
