const leetCodeProblemsUrl = "https://leetcode.com/problemset/";

function openLeetCode() {
  if (typeof chrome !== "undefined" && chrome.tabs?.create) {
    chrome.tabs.create({ url: leetCodeProblemsUrl });
    return;
  }

  window.open(leetCodeProblemsUrl, "_blank", "noopener,noreferrer");
}

export default function App() {
  return (
    <main className="app-shell">
      <section className="hero-card" aria-labelledby="welcome-title">
        <p className="eyebrow">LeetCoach MVP</p>
        <h1 id="welcome-title">Learn the pattern before the answer.</h1>
        <p className="hero-copy">
          Open a LeetCode problem and LeetCoach will help you recognize the
          pattern, read the signals, and build an interview-style thinking
          process without revealing the final solution.
        </p>

        <button className="primary-action" type="button" onClick={openLeetCode}>
          Open LeetCode
        </button>
      </section>

      <section className="status-card" aria-labelledby="status-title">
        <div className="status-dot" aria-hidden="true" />
        <div>
          <h2 id="status-title">Waiting for a problem page</h2>
          <p>
            For the first milestone, LeetCoach targets pages like
            <span className="inline-code"> leetcode.com/problems/two-sum/</span>.
          </p>
        </div>
      </section>

      <section className="guide-card" aria-labelledby="guide-title">
        <h2 id="guide-title">What this panel will show</h2>
        <ol>
          <li>Problem identity detected from the current LeetCode tab.</li>
          <li>Pattern classification from the local backend database.</li>
          <li>Guided thinking steps from the mock AI provider.</li>
        </ol>
      </section>
    </main>
  );
}
