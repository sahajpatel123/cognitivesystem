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

test("A1: request payload has only user_text", async ({ page }) => {
  await startChatPage(page);
  await interceptChat(page, async (route, body) => {
    expect(Object.keys(body)).toEqual(["user_text"]);
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "ok" }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("hi");
  await page.getByRole("button", { name: "Send" }).click();
});

test("A2: empty input blocks send", async ({ page }) => {
  await startChatPage(page);
  const calls = [] as any[];
  await page.route("**/api/chat", (route) => {
    calls.push(route.request());
    return route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "x" }) });
  });
  await expect(page.getByRole("button", { name: "Send" })).toBeDisabled();
  expect(calls.length).toBe(0);
});

test("A3: oversized input blocked", async ({ page }) => {
  await startChatPage(page);
  const long = "x".repeat(2100);
  const calls = [] as any[];
  await page.route("**/api/chat", (route) => {
    calls.push(route.request());
    return route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "x" }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill(long);
  await page.getByRole("button", { name: "Send" }).click();
  expect(calls.length).toBe(0);
});

test("B1: REFUSE makes UI terminal", async ({ page }) => {
  await startChatPage(page);
  const calls = [] as any[];
  await page.route("**/api/chat", async (route) => {
    calls.push(route.request());
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "REFUSE", rendered_text: "no" }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("hi");
  await expect(page.getByRole("button", { name: "Send" })).toBeEnabled();
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("This session is closed by the system’s governance rules.")).toBeVisible();
  const closedInput = page.getByPlaceholder("Interaction closed");
  await expect(closedInput).toBeDisabled();
  await expect(closedInput).toHaveValue("");
  await expect(page.getByRole("button", { name: "Send" })).toBeDisabled();
  expect(calls.length).toBe(1);
});

test("B2: CLOSE makes UI terminal", async ({ page }) => {
  await startChatPage(page);
  await interceptChat(page, async (route) => {
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "CLOSE", rendered_text: "bye" }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("bye");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("This session is closed by the system’s governance rules.")).toBeVisible();
});

test("C1: invalid JSON fail-closed", async ({ page }) => {
  await startChatPage(page);
  await interceptChat(page, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "not-json" });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("hi");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Request failed. Please retry.")).toBeVisible();
});

test("C2: unknown action fail-closed", async ({ page }) => {
  await startChatPage(page);
  await interceptChat(page, async (route) => {
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "WEIRD", rendered_text: "x" }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("hi");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Request failed. Please retry.")).toBeVisible();
});

test("C3: missing rendered_text fail-closed", async ({ page }) => {
  await startChatPage(page);
  await interceptChat(page, async (route) => {
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER" }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("hi");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Request failed. Please retry.")).toBeVisible();
});

test("D1: ask-one renders verbatim even with multiple questions", async ({ page }) => {
  await startChatPage(page);
  const multi = "Q1? Q2?";
  await interceptChat(page, async (route) => {
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "ASK_ONE_QUESTION", rendered_text: multi }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("hi");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(multi)).toBeVisible();
});

test("D2: no suggestion chips are rendered", async ({ page }) => {
  await startChatPage(page);
  const chips = page.getByText(/suggest/i);
  await expect(chips).toHaveCount(0);
});

test("E1: stale response ignored", async ({ page }) => {
  await startChatPage(page);
  let firstRoute; let secondRoute;
  await page.route("**/api/chat", (route) => {
    const body = route.request().postDataJSON();
    if (body.user_text === "first") {
      firstRoute = route;
      return; // delay first
    }
    if (body.user_text === "second") {
      secondRoute = route;
      return; // hold second for manual fulfill
    }
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("first");
  await page.getByRole("button", { name: "Send" }).click();
  await expect.poll(() => (firstRoute ? 1 : 0)).toBe(1);
  await page.getByRole("button", { name: "Reset chat" }).click(); // advance request id and clear state
  await page.getByPlaceholder("Type a governed prompt...").fill("second");
  await page.getByRole("button", { name: "Send" }).click();
  await expect.poll(() => (secondRoute ? 1 : 0)).toBe(1);
  await secondRoute?.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "second-resp" }) });
  // fulfill the stale first after reset; should be ignored by pendingRequestId guard
  await firstRoute?.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "late" }) });
  await expect(page.getByText("second-resp")).toBeVisible();
  await expect(page.getByText("late")).toHaveCount(0);
});

test("F1: session storage never sent", async ({ page }) => {
  await startChatPage(page);
  await interceptChat(page, async (route, body) => {
    expect(Object.keys(body)).toEqual(["user_text"]);
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "ok" }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("hello");
  await page.getByRole("button", { name: "Send" }).click();
});

test("F2: TTL expiry resets session and does not trigger backend", async ({ page }) => {
  await startChatPage(page);
  await page.evaluate(() => {
    const raw = localStorage.getItem("governed_chat_session_v1");
    if (raw) {
      const obj = JSON.parse(raw);
      obj.expires_at = Date.now() - 1000;
      localStorage.setItem("governed_chat_session_v1", JSON.stringify(obj));
    }
  });
  const calls = [] as any[];
  await page.route("**/api/chat", (route) => {
    calls.push(route.request());
    return route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "x" }) });
  });
  await page.reload();
  expect(calls.length).toBe(0);
});

test("G1: manual retry makes exactly one call", async ({ page }) => {
  await startChatPage(page);
  const calls: any[] = [];
  let firstDone = false;
  await page.route("**/api/chat", (route) => {
    calls.push(route.request());
    if (!firstDone) {
      firstDone = true;
      return route.fulfill({ status: 200, body: JSON.stringify({ action: "FALLBACK", rendered_text: "fail" }) });
    }
    return route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "ok" }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("hi");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("button", { name: "Retry last" })).toBeEnabled();
  await page.getByRole("button", { name: "Retry last" }).click();
  expect(calls.length).toBe(2);
});

test("G2: reset clears local transcript only", async ({ page }) => {
  await startChatPage(page);
  await interceptChat(page, async (route) => {
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: "msg" }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("hi");
  await page.getByRole("button", { name: "Send" }).click();
  await page.getByRole("button", { name: "Reset chat" }).click();
  await expect(page.getByText("msg")).toHaveCount(0);
});

test("H1: UI renders exact backend text", async ({ page }) => {
  await startChatPage(page);
  const text = "VERBATIM OUTPUT";
  await interceptChat(page, async (route) => {
    await route.fulfill({ status: 200, body: JSON.stringify({ action: "ANSWER", rendered_text: text }) });
  });
  await page.getByPlaceholder("Type a governed prompt...").fill("hi");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(text)).toBeVisible();
});
