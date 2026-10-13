import { useSyncExternalStore } from "react";
import type { Tokens } from "./types";

export type Session = Tokens & { expires_at: number };
const STORAGE = "jrn.session.v1";
let current: Session | null = restore();
let generation = 0;
const listeners = new Set<() => void>();
const boundaries = new Set<() => void>();

function restore(): Session | null {
  try {
    const value: Partial<Session> = JSON.parse(
      sessionStorage.getItem(STORAGE) || "null",
    );
    return value &&
      typeof value.access_token === "string" &&
      typeof value.refresh_token === "string" &&
      typeof value.expires_at === "number" &&
      typeof value.expires_in === "number"
      ? (value as Session)
      : null;
  } catch {
    return null;
  }
}
export const session = {
  get: () => current,
  generation: () => generation,
  boundary: (fn: () => void) => {
    boundaries.add(fn);
  },
  set(tokens: Tokens | null, boundary = true) {
    if (boundary) {
      generation++;
      boundaries.forEach((fn) => fn());
    }
    current = tokens
      ? { ...tokens, expires_at: Date.now() + tokens.expires_in * 1000 }
      : null;
    try {
      if (current) sessionStorage.setItem(STORAGE, JSON.stringify(current));
      else sessionStorage.removeItem(STORAGE);
    } catch {
      /* In restricted browsers the session remains in memory. */
    }
    listeners.forEach((fn) => fn());
  },
};
export function useSession() {
  return useSyncExternalStore((fn) => {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }, session.get);
}
