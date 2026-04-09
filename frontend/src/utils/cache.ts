import { STORAGE_KEYS } from '../constants/storage';
import type { LocalSessionCache } from '../types/cache';

const emptyCache = (): LocalSessionCache => ({
  activeSessionId: null,
  sessions: [],
  messagesBySession: {},
  updatedAt: Date.now(),
});

export function loadSessionCache(): LocalSessionCache {
  const raw = localStorage.getItem(STORAGE_KEYS.sessionCache);
  if (!raw) {
    return emptyCache();
  }

  try {
    const parsed = JSON.parse(raw) as LocalSessionCache;
    return {
      activeSessionId: parsed.activeSessionId ?? null,
      sessions: parsed.sessions ?? [],
      messagesBySession: parsed.messagesBySession ?? {},
      updatedAt: parsed.updatedAt ?? Date.now(),
    };
  } catch {
    return emptyCache();
  }
}

export function saveSessionCache(cache: LocalSessionCache) {
  localStorage.setItem(STORAGE_KEYS.sessionCache, JSON.stringify({
    ...cache,
    updatedAt: Date.now(),
  }));
}

export function clearSessionCache() {
  localStorage.removeItem(STORAGE_KEYS.sessionCache);
}
