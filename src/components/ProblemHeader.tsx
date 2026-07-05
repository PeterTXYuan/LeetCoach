type ProblemHeaderProps = {
  title: string;
};

export function ProblemHeader({ title }: ProblemHeaderProps) {
  return (
    <section className="problem-card detected" aria-labelledby="problem-title">
      <div className="problem-heading-row">
        <div
          className="status-dot"
          aria-label="LeetCode problem page detected"
          role="img"
        />
        <h2 id="problem-title" className="problem-title">
          {title}
        </h2>
      </div>
    </section>
  );
}
