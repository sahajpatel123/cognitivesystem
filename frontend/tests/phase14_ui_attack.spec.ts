import { test, expect } from "@playwright/test";

const CHAT_URL = "/product/chat";

async function startChatPage(page) {
  await page.goto(CHAT_URL);
  await expect(page.getByText("Governed chat")).toBeVisible();
}

async function interceptChat(page, handler) {
  await page.route("**/api/chat", async (route) => {
    const request = route.request();
    const body = request.postDataJSON();
    await handler(route, body, request);
  });
}

// -----------------
// Category A: Payload / Contract attacks
// -----------------

test("A1: request payload remains {user_text} only", async ({ page }) => {
  await startChatPage(page);
  const bodies: any[] = [];
  await interceptChat(page, async (route, body) => {
    bodies.push(body);
    expect(Object.keys(body)).toEqual(["user_text"]);
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "ok" }) });
  });

  await page.getByPlaceholder("Type a governed prompt...").fill("first");
  await page.getByRole("button", { name: "Send" }).click();
  await page.getByPlaceholder("Type a governed prompt...").fill("second");
  await page.getByRole("button", { name: "Send" }).click();

  expect(bodies).toHaveLength(2);
  expect(bodies.every((b) => Object.keys(b).length === 1 && "user_text" in b)).toBeTruthy();
});

test("A2: no local/session metadata sent even after localStorage is populated", async ({ page }) => {
  await startChatPage(page);
  await page.evaluate(() => {
    localStorage.setItem(
      "governed_chat_session_v1",
      JSON.stringify({
        expires_at: Date.now() + 1000 * 60 * 5,
        transcript: [{ role: "user", content: "prior" }],
      })
    );
  });

  await interceptChat(page, async (route, body) => {
    expect(Object.keys(body)).toEqual(["user_text"]);
    expect(JSON.stringify(body)).not.toContain("prior");
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "ok" }) });
  });

  await page.reload();
  await page.getByPlaceholder("Type a governed prompt...").fill("fresh");
  await page.getByRole("button", { name: "Send" }).click();
});

// -----------------
// Category B: Terminal discipline attacks
// -----------------

test("B1: REFUSE makes UI terminal and blocks further send", async ({ page }) => {
  await startChatPage(page);
  const calls: any[] = [];
  await interceptChat(page, async (route) => {
    calls.push(route.request());
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "REFUSE", rendered_text: "no" }) });
  });

  await page.getByPlaceholder("Type a governed prompt...").fill("hi");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("This session is closed by the system’s governance rules.")).toBeVisible();
  await expect(page.getByPlaceholder("Interaction closed")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Send" })).toBeDisabled();

  // Attempt to type and send again should not trigger another call
  await page.getByPlaceholder("Interaction closed").click({ force: true });
  expect(calls).toHaveLength(1);
});

test("B2: CLOSE keeps terminal; retry does not reopen", async ({ page }) => {
  await startChatPage(page);
  const calls: any[] = [];
  await interceptChat(page, async (route) => {
    calls.push(route.request());
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "CLOSE", rendered_text: "bye" }) });
  });

  await page.getByPlaceholder("Type a governed prompt...").fill("bye");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("This session is closed by the system’s governance rules.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Send" })).toBeDisabled();

  // Retry last should be disabled when terminal
  await expect(page.getByRole("button", { name: "Retry last" })).toBeDisabled();
  expect(calls).toHaveLength(1);
});

// -----------------
// Category C: Race / stale responses
// -----------------

test("C1: stale responses ignored with out-of-order fulfillment", async ({ page }) => {
  await startChatPage(page);
  let firstRoute; let secondRoute;
  await page.route("**/api/chat", (route) => {
    const body = route.request().postDataJSON();
    if (body.user_text === "first") {
      firstRoute = route; // hold
      return;
    }
    if (body.user_text === "second") {
      secondRoute = route; // hold
      return;
    }
  });

  await page.getByPlaceholder("Type a governed prompt...").fill("first");
  await page.getByRole("button", { name: "Send" }).click();
  await expect.poll(() => (firstRoute ? 1 : 0)).toBe(1);

  // Reset chat to obtain a new request id, then send second request
  await page.getByRole("button", { name: "Reset chat" }).click();
  await page.getByPlaceholder("Type a governed prompt...").fill("second");
  await page.getByRole("button", { name: "Send" }).click();
  await expect.poll(() => (secondRoute ? 1 : 0)).toBe(1);

  await secondRoute?.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "second-resp" }) });
  await firstRoute?.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "late" }) });

  await expect(page.getByText("second-resp")).toBeVisible();
  await expect(page.getByText("late")).toHaveCount(0);
});

// -----------------
// Category D: In-flight blocking / spam resistance
// -----------------

test("D1: in-flight request blocks additional sends", async ({ page }) => {
  await startChatPage(page);
  let pendingRoute;
  const calls: any[] = [];
  await page.route("**/api/chat", (route) => {
    calls.push(route.request());
    if (!pendingRoute) {
      pendingRoute = route; // hold first
      return;
    }
    return route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "extra" }) });
  });

  await page.getByPlaceholder("Type a governed prompt...").fill("wait");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("button", { name: "Send" })).toBeDisabled();

  // Clicking again should not dispatch another request while pending
  await page.getByRole("button", { name: "Send" }).click({ force: true });
  expect(calls).toHaveLength(1);

  await pendingRoute?.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "done" }) });
  await expect(page.getByText("done")).toBeVisible();
});

// -----------------
// Category E: TTL / session attacks
// -----------------

test("E1: expired TTL resets locally without backend call", async ({ page }) => {
  await startChatPage(page);
  await page.evaluate(() => {
    localStorage.setItem(
      "governed_chat_session_v1",
      JSON.stringify({ expires_at: Date.now() - 1000, transcript: [{ role: "user", content: "old" }] })
    );
  });
  const calls: any[] = [];
  await page.route("**/api/chat", (route) => {
    calls.push(route.request());
    return route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "x" }) });
  });

  await page.reload();
  expect(calls).toHaveLength(0);
});

test("E2: history not replayed to backend after reload", async ({ page }) => {
  await startChatPage(page);
  await page.evaluate(() => {
    localStorage.setItem(
      "governed_chat_session_v1",
      JSON.stringify({ expires_at: Date.now() + 1000 * 60 * 5, transcript: [{ role: "assistant", content: "cached" }] })
    );
  });

  const bodies: any[] = [];
  await interceptChat(page, async (route, body) => {
    bodies.push(body);
    expect(Object.keys(body)).toEqual(["user_text"]);
    expect(JSON.stringify(body)).not.toContain("cached");
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "ok" }) });
  });

  await page.reload();
  await page.getByPlaceholder("Type a governed prompt...").fill("after-reload");
  await page.getByRole("button", { name: "Send" }).click();
  expect(bodies).toHaveLength(1);
});

// -----------------
// Category F: Render-only guarantee
// -----------------

test("F1: UI renders backend text verbatim (unicode/markdown)", async ({ page }) => {
  await startChatPage(page);
  const weird = "**⚠️ caution** — preserve_quotes `code`";
  await interceptChat(page, async (route) => {
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: weird }) });
  });

  await page.getByPlaceholder("Type a governed prompt...").fill("show text");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(weird)).toBeVisible();
});

// -----------------
// Category G: No-agent / no-suggestion
// -----------------

test("G1: no suggestion chips or agent prompts appear", async ({ page }) => {
  await startChatPage(page);
  await expect(page.getByText(/suggest/i)).toHaveCount(0);
  await expect(page.getByText(/assistant is typing/i)).toHaveCount(0);
});
