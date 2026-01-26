const allowedStates = ["OK", "NEEDS_INPUT", "RATE_LIMITED", "QUOTA_EXCEEDED", "DEGRADED", "BLOCKED", "ERROR"];

function normalizeUxState(v) {
  if (!v || typeof v !== "string") return "ERROR";
  const upper = v.toUpperCase();
  return allowedStates.includes(upper) ? upper : "ERROR";
}

function clampCooldownSeconds(n) {
  const num = typeof n === "number" ? n : Number(n);
  if (!Number.isFinite(num)) return null;
  const floored = Math.floor(num);
  const clamped = Math.max(0, Math.min(86400, floored));
  if (clamped <= 0) return null;
  return clamped;
}

function getUxCopy(state, cooldownSeconds) {
  switch (state) {
    case "OK":
      return { title: "Ready", tone: "success" };
    case "NEEDS_INPUT":
      return {
        title: "Need a bit more detail",
        body: "Add outcome, constraints/examples, and priority.",
        tone: "neutral",
      };
    case "RATE_LIMITED": {
      const suffix = cooldownSeconds ? ` Try again in ${cooldownSeconds}s.` : "";
      return { title: "Slow down", body: `Please wait.${suffix}`, tone: "warn" };
    }
    case "QUOTA_EXCEEDED":
      return { title: "Quota exceeded", body: "Try later or upgrade your plan.", tone: "warn" };
    case "DEGRADED":
      return { title: "Degraded mode", body: "Quality may be reduced temporarily.", tone: "warn" };
    case "BLOCKED":
      return { title: "Request blocked", body: "This request can’t be processed.", tone: "error" };
    case "ERROR":
    default:
      return { title: "Something went wrong", body: "Retry in a moment.", tone: "error" };
  }
}

module.exports = { normalizeUxState, clampCooldownSeconds, getUxCopy };
