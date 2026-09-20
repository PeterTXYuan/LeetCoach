import type { RelatedProblem } from "../api/relatedProblems";

export function RelatedProblemCard({ problem }: { problem: RelatedProblem }) {
  const openProblem = () => {
    const url = `https://leetcode.com/problems/${encodeURIComponent(problem.slug)}/`;
    if (typeof chrome !== "undefined" && chrome.tabs?.create) {
      void chrome.tabs.create({ url });
    } else {
      window.open(url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <article className="related-problem-card" aria-label={problem.title}>
      <div className="related-problem-heading">
        <h4>{problem.title}</h4>
        <span className={`problem-difficulty difficulty-${problem.difficulty.toLowerCase()}`}>{problem.difficulty}</span>
      </div>
      {problem.reason && <p>{problem.reason}</p>}
      <button className="secondary-action related-open" type="button"
        aria-label={`Open Problem: ${problem.title}`} onClick={openProblem}>Open Problem</button>
    </article>
  );
}
