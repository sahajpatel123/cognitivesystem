"use client";

export function RollingTape() {
  const features = [
    "Verified mode",
    "Policy checks",
    "Tool allowlists",
    "Audit trail",
    "Deterministic runs",
    "Trace IDs",
    "Export summaries",
    "Privacy boundaries",
    "Least-privilege tools",
    "No hidden bypasses",
  ];

  return (
    <div className="rolling-tape-wrapper">
      <div className="rolling-tape-track">
        <div className="rolling-tape-content">
          {features.map((feature, index) => (
            <span key={`first-${index}`} className="rolling-tape-item">
              {feature}
            </span>
          ))}
        </div>
        <div className="rolling-tape-content" aria-hidden="true">
          {features.map((feature, index) => (
            <span key={`second-${index}`} className="rolling-tape-item">
              {feature}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
