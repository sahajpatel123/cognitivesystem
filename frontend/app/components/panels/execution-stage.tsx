import { ExecutionRun } from "../../lib/static-data";

export function ExecutionStage({ run }: { run: ExecutionRun }) {
  return (
    <div className="stage-grid">
      <div className="stage-panel surface-entrance" data-motion="panel" aria-label="Reasoning stage">
        <header>
          <h3>Reasoning stage</h3>
          <span className="badge badge-neutral">Trace</span>
        </header>
        <p>{run.reasoningTrace.summary}</p>
        <div>
          <h4 className="section-subheading">Steps</h4>
          <ul className="list-minor">
            {run.reasoningTrace.steps.map((step) => (
              <li key={step.id}>
                <span className="code-chip">{step.status}</span> {step.description}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="stage-panel surface-entrance" data-motion="panel" aria-label="Hypothesis deltas">
        <header>
          <h3>Hypothesis deltas</h3>
          <span className="badge badge-neutral">Session-local</span>
        </header>
        <ul className="list-minor">
          {run.hypotheses.map((hypothesis) => (
            <li key={hypothesis.id}>
              <strong>{hypothesis.claim}</strong>
              <div className="tag-row">
                <span className="code-chip">Δsupport: {hypothesis.supportScoreDelta.toFixed(2)}</span>
                <span className="code-chip">Δrefute: {hypothesis.refuteScoreDelta.toFixed(2)}</span>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="stage-panel surface-entrance" data-motion="panel" aria-label="Expression stage">
        <header>
          <h3>Expression stage</h3>
          <span className="badge badge-neutral">Plan + output</span>
        </header>
        <div>
          <h4 className="section-subheading">Plan</h4>
          <p className="tooltip">Tone: {run.expressionPlan.targetTone}</p>
          <div className="tag-row">
            {run.expressionPlan.structure.map((item) => (
              <span key={item} className="code-chip">
                {item}
              </span>
            ))}
          </div>
        </div>
        <div>
          <h4 className="section-subheading">Rendered reply</h4>
          <p>{run.renderedReply}</p>
        </div>
      </div>
    </div>
  );
}
