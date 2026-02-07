import { ChatSession } from "./ChatHistory";

const STORAGE_KEY = "cognitive_chat_sessions";
const CURRENT_SESSION_KEY = "cognitive_current_session_id";

export function loadChatSessions(): ChatSession[] {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    return JSON.parse(stored);
  } catch {
    return [];
  }
}

export function saveChatSessions(sessions: ChatSession[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch {
    // Silent fail
  }
}

export function getCurrentSessionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(CURRENT_SESSION_KEY);
  } catch {
    return null;
  }
}

export function setCurrentSessionId(sessionId: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (sessionId) {
      localStorage.setItem(CURRENT_SESSION_KEY, sessionId);
    } else {
      localStorage.removeItem(CURRENT_SESSION_KEY);
    }
  } catch {
    // Silent fail
  }
}

export function createSessionTitle(firstUserMessage: string): string {
  const cleaned = firstUserMessage.trim();
  if (cleaned.length <= 50) return cleaned;
  return cleaned.substring(0, 47) + "...";
}

export function addOrUpdateSession(session: ChatSession): void {
  const sessions = loadChatSessions();
  const existingIndex = sessions.findIndex((s) => s.id === session.id);
  if (existingIndex >= 0) {
    sessions[existingIndex] = session;
  } else {
    sessions.unshift(session);
  }
  saveChatSessions(sessions);
}

export function deleteSession(sessionId: string): void {
  const sessions = loadChatSessions();
  const filtered = sessions.filter((s) => s.id !== sessionId);
  saveChatSessions(filtered);
  if (getCurrentSessionId() === sessionId) {
    setCurrentSessionId(null);
  }
}

export function getSessionById(sessionId: string): ChatSession | null {
  const sessions = loadChatSessions();
  return sessions.find((s) => s.id === sessionId) || null;
}
