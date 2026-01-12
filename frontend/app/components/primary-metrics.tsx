import { PipelineState } from "../lib/static-data";

interface MetricConfig {
  label: string;
  value: string;
  tooltip: string;
  state?: PipelineState;
}

export function PrimaryMetrics({ metrics }: { metrics: MetricConfig[] }) {
  return (
    <header className="persistent-header">
      {metrics.map((metric) => (
        <div key={metric.label} className="persistent-card surface-entrance" data-motion="card">
          <h2>{metric.label}</h2>
          {metric.state ? (
            <div className="value state-indicator" data-state={metric.state}>
              <span /> State: {metric.value}
            </div>
          ) : (
            <div className="value">{metric.value}</div>
          )}
          <p className="tooltip">{metric.tooltip}</p>
        </div>
      ))}
    </header>
  );
}
