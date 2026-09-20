type ProblemHeaderProps = {
  title: string;
  titleId?: string;
};

export function ProblemHeader({ title, titleId = "problem-title" }: ProblemHeaderProps) {
  return (
    <section className="problem-card detected" aria-labelledby={titleId}>
      <div className="problem-heading-row">
        <div
          className="status-dot"
          aria-label="LeetCode problem page detected"
          role="img"
        />
        <h2 id={titleId} className="problem-title">
          {title}
        </h2>
      </div>
    </section>
  );
}
