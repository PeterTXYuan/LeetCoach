import { useRelatedProblems } from "../hooks/useRelatedProblems";
import { RelatedProblemCard } from "./RelatedProblemCard";

const groups = [
  { key: "easier", label: "Easier" },
  { key: "similar", label: "Similar" },
  { key: "harder", label: "Harder" }
] as const;

export function PracticePanel({ slug, isActive }: { slug: string; isActive: boolean }) {
  const { state, retry } = useRelatedProblems(slug, isActive);

  return (
    <section className="guide-card related-problems-section" aria-labelledby="related-problems-title">
      <h2 id="related-problems-title">Related problems</h2>
      <p className="section-copy">Hand-picked problems to practice related ideas.</p>
      {(state.status === "idle" || state.status === "loading") && <p role="status">Loading related problems...</p>}
      {state.status === "not_found" && <p className="analysis-message">Related problems are not available for this problem yet.</p>}
      {state.status === "error" && (
        <div role="alert">
          <p>Unable to load related problems. Please try again.</p>
          <button className="secondary-action" type="button" onClick={retry}>Retry related problems</button>
        </div>
      )}
      {state.status === "success" && groups.map(({ key, label }) => (
        <section className="related-group" key={key} aria-labelledby={`related-${key}`}>
          <h3 id={`related-${key}`}>{label}</h3>
          {state.response[key].length ? (
            <div className="related-problem-list">
              {state.response[key].map((problem) => <RelatedProblemCard key={problem.slug} problem={problem} />)}
            </div>
          ) : <p className="section-copy">No {label.toLowerCase()} problems listed yet.</p>}
        </section>
      ))}
    </section>
  );
}
