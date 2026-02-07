export type Action = 
  | "ANSWER" 
  | "ASK_ONE_QUESTION" 
  | "REFUSE" 
  | "CLOSE" 
  | "FALLBACK"
  | "ANSWER_DEGRADED"
  | "ASK_CLARIFY"
  | "FAIL_GRACEFULLY"
  | "BLOCK";

export type SafeChatResponse = {
  action: Action;
  rendered_text: string;
  failure_type?: string | null;
  failure_reason?: string | null;
};

export class FailClosedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FailClosedError";
  }
}

const MAX_INPUT_CHARS = 2000;
const MAX_RENDERED_CHARS = 20000;
const ALLOWED_ACTIONS: Action[] = [
  "ANSWER", 
  "ASK_ONE_QUESTION", 
  "REFUSE", 
  "CLOSE", 
  "FALLBACK",
  "ANSWER_DEGRADED",
  "ASK_CLARIFY",
  "FAIL_GRACEFULLY",
  "BLOCK",
];

export function validateChatRequest(userText: string): { user_text: string } {
  if (typeof userText !== "string") {
    throw new FailClosedError("invalid user_text type");
  }
  const trimmed = userText.trim();
  if (!trimmed) {
    throw new FailClosedError("empty input");
  }
  if (trimmed.length > MAX_INPUT_CHARS) {
    throw new FailClosedError("input too long");
  }
  return { user_text: trimmed };
}

export function validateChatResponse(raw: unknown): SafeChatResponse {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new FailClosedError("response not object");
  }
  const obj = raw as Record<string, unknown>;
  const { action, rendered_text, failure_type, failure_reason } = obj;

  if (typeof action !== "string" || !ALLOWED_ACTIONS.includes(action as Action)) {
    throw new FailClosedError("invalid action");
  }
  if (typeof rendered_text !== "string" || rendered_text.length === 0 || rendered_text.length > MAX_RENDERED_CHARS) {
    throw new FailClosedError("invalid rendered_text");
  }
  if (failure_type !== undefined && failure_type !== null && typeof failure_type !== "string") {
    throw new FailClosedError("invalid failure_type");
  }
  if (failure_reason !== undefined && failure_reason !== null && typeof failure_reason !== "string") {
    throw new FailClosedError("invalid failure_reason");
  }

  return {
    action: action as Action,
    rendered_text,
    failure_type: (failure_type as string | null | undefined) ?? null,
    failure_reason: (failure_reason as string | null | undefined) ?? null,
  };
}
