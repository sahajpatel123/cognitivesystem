import { Action } from "./contract_runtime";

export type StoredMessage = {
  id: string;
  role: "user" | "system";
  text: string;
  action?: Action;
  failureType?: string | null;
};

type StoredSession = {
  storage_version: 1;
  session_id: string;
  created_at: number;
  expires_at: number;
  messages: StoredMessage[];
};

export type SessionState = {
  sessionId: string;
  createdAt: number;
  expiresAt: number;
};

const STORAGE_KEY = "governed_chat_session_v1";
const STORAGE_VERSION = 1;
export const TTL_MS = 60 * 60 * 1000; // 60 minutes
const MAX_MESSAGES = 200;
const MAX_MESSAGE_CHARS = 4000;

export function startNewSession(): { session: SessionState; messages: StoredMessage[] } {
  const now = Date.now();
  const session: SessionState = {
    sessionId: crypto.randomUUID(),
    createdAt: now,
    expiresAt: now + TTL_MS,
  };
  persist(session, []);
  return { session, messages: [] };
}

export function isExpired(session: SessionState): boolean {
  return Date.now() > session.expiresAt;
}

export function loadSession(): { session: SessionState; messages: StoredMessage[] } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return startNewSession();
    }
    const parsed = JSON.parse(raw) as StoredSession;
    if (!validateStoredSession(parsed)) {
      return startNewSession();
    }
    const session: SessionState = {
      sessionId: parsed.session_id,
      createdAt: parsed.created_at,
      expiresAt: parsed.expires_at,
    };
    if (isExpired(session)) {
      return startNewSession();
    }
    return { session, messages: parsed.messages };
  } catch {
    return startNewSession();
  }
}

export function persist(session: SessionState, messages: StoredMessage[]): void {
  try {
    const bounded = messages.slice(-MAX_MESSAGES).map((m) => ({
      ...m,
      text: m.text.slice(0, MAX_MESSAGE_CHARS),
    }));
    const payload: StoredSession = {
      storage_version: STORAGE_VERSION,
      session_id: session.sessionId,
      created_at: session.createdAt,
      expires_at: session.expiresAt,
      messages: bounded,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Fail quietly; UI will still operate without persistence
  }
}

function validateStoredSession(value: any): value is StoredSession {
  if (!value || typeof value !== "object") return false;
  if (value.storage_version !== STORAGE_VERSION) return false;
  if (typeof value.session_id !== "string" || typeof value.created_at !== "number" || typeof value.expires_at !== "number")
    return false;
  if (!Array.isArray(value.messages)) return false;
  if (value.messages.length > MAX_MESSAGES) return false;
  for (const m of value.messages) {
    if (!m || typeof m !== "object") return false;
    if (typeof m.id !== "string") return false;
    if (m.role !== "user" && m.role !== "system") return false;
    if (typeof m.text !== "string" || m.text.length > MAX_MESSAGE_CHARS) return false;
    if (m.action && typeof m.action !== "string") return false;
    if (m.failureType && typeof m.failureType !== "string") return false;
  }
  return true;
}
