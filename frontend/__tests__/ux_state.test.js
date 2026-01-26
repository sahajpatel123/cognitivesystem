const { test, strictEqual } = require("node:test");
const assert = require("node:assert");
const { normalizeUxState, clampCooldownSeconds, getUxCopy } = require("../app/lib/ux_state_runtime");

test("normalizeUxState is case-insensitive and defaults to ERROR", () => {
  strictEqual(normalizeUxState("ok"), "OK");
  strictEqual(normalizeUxState("Needs_Input"), "ERROR");
  strictEqual(normalizeUxState(null), "ERROR");
});

test("clampCooldownSeconds clamps and nulls invalid", () => {
  strictEqual(clampCooldownSeconds("not"), null);
  strictEqual(clampCooldownSeconds(-1), null);
  strictEqual(clampCooldownSeconds(0), null);
  strictEqual(clampCooldownSeconds(5.8), 5);
  strictEqual(clampCooldownSeconds(999999), 86400);
});

test("getUxCopy produces stable copy and includes cooldown text for rate limited", () => {
  const ok = getUxCopy("OK", null);
  strictEqual(ok.title, "Ready");
  const rl = getUxCopy("RATE_LIMITED", 12);
  assert.match(rl.body || "", /12s/);
});
