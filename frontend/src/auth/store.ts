import type { AuthSession, CurrentUser } from './types';

const STORAGE_KEY = 'call-analyzer.auth';

type Listener = () => void;

function isBrowser() {
  return typeof window !== 'undefined';
}

function readStoredSession(): AuthSession | null {
  if (!isBrowser()) {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}

let currentSession: AuthSession | null = readStoredSession();
const listeners = new Set<Listener>();

function persistSession(session: AuthSession | null) {
  if (!isBrowser()) {
    return;
  }
  if (session) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

function emit() {
  listeners.forEach((listener) => listener());
}

export const authStore = {
  getSnapshot: () => currentSession,
  subscribe(listener: Listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  setSession(session: AuthSession | null) {
    currentSession = session;
    persistSession(session);
    emit();
  },
  setUser(user: CurrentUser | null) {
    if (!currentSession) {
      return;
    }
    currentSession = { ...currentSession, user };
    persistSession(currentSession);
    emit();
  },
  clear() {
    currentSession = null;
    persistSession(null);
    emit();
  },
};
