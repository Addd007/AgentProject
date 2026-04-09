const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export const API_ENDPOINTS = {
  health: `${API_BASE}/health`,
  authRegister: `${API_BASE}/api/auth/register`,
  authLogin: `${API_BASE}/api/auth/login`,
  authLogout: `${API_BASE}/api/auth/logout`,
  authMe: `${API_BASE}/api/auth/me`,
  chat: `${API_BASE}/api/chat`,
  chatStream: `${API_BASE}/api/chat/stream`,
  sessions: `${API_BASE}/api/sessions`,
  session: (sessionId: string) => `${API_BASE}/api/session/${sessionId}`,
};

export { API_BASE };
