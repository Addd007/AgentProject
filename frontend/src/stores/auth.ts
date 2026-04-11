import { ref } from 'vue';
import { defineStore } from 'pinia';

import { API_ENDPOINTS } from '../constants/api';
import { STORAGE_KEYS } from '../constants/storage';
import { clearSessionCache } from '../utils/cache';
import type { AuthResponse, AuthUser } from '../types/auth';

function getErrorMessage(payload: unknown): string {
    if (!payload || typeof payload !== 'object') {
        return '请求失败';
    }

    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === 'string') {
        return detail;
    }

    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as { msg?: unknown };
        if (typeof first?.msg === 'string') {
            return first.msg;
        }
    }

    return '请求失败';
}

function loadCachedUser(): AuthUser | null {
    const raw = localStorage.getItem(STORAGE_KEYS.authCache);
    if (!raw) {
        return null;
    }

    try {
        const parsed = JSON.parse(raw) as AuthUser;
        return parsed?.user_id && parsed?.username ? parsed : null;
    } catch {
        return null;
    }
}

export const useAuthStore = defineStore('auth', () => {
    const user = ref<AuthUser | null>(loadCachedUser());
    const isHydrated = ref(false);
    const isSubmitting = ref(false);

    function persistUser(nextUser: AuthUser | null) {
        user.value = nextUser;
        if (nextUser) {
            localStorage.setItem(STORAGE_KEYS.authCache, JSON.stringify(nextUser));
            return;
        }

        localStorage.removeItem(STORAGE_KEYS.authCache);
    }

    async function restoreSession() {
        if (isHydrated.value) {
            return user.value;
        }

        try {
            const response = await fetch(API_ENDPOINTS.authMe, {
                credentials: 'include',
            });
            if (!response.ok) {
                persistUser(null);
                clearSessionCache();
                isHydrated.value = true;
                return null;
            }

            const data = (await response.json()) as AuthResponse;
            if (!data.user) {
                persistUser(null);
                clearSessionCache();
                isHydrated.value = true;
                return null;
            }
            persistUser(data.user);
            isHydrated.value = true;
            return data.user;
        } catch {
            persistUser(null);
            clearSessionCache();
            isHydrated.value = true;
            return null;
        }
    }

    async function validateSession() {
        try {
            const response = await fetch(API_ENDPOINTS.authMe, {
                credentials: 'include',
            });
            if (!response.ok) {
                persistUser(null);
                clearSessionCache();
                isHydrated.value = true;
                return null;
            }

            const data = (await response.json()) as AuthResponse;
            if (!data.user) {
                persistUser(null);
                clearSessionCache();
                isHydrated.value = true;
                return null;
            }

            persistUser(data.user);
            isHydrated.value = true;
            return data.user;
        } catch {
            persistUser(null);
            clearSessionCache();
            isHydrated.value = true;
            return null;
        }
    }

    async function submitAuth(endpoint: string, username: string, password: string) {
        isSubmitting.value = true;
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ username, password }),
            });

            const payload = await response.json().catch(() => ({ detail: '请求失败' }));
            if (!response.ok) {
                throw new Error(getErrorMessage(payload));
            }

            clearSessionCache();
            const data = payload as AuthResponse;
            persistUser(data.user);
            isHydrated.value = true;
            return data.user;
        } finally {
            isSubmitting.value = false;
        }
    }

    async function login(username: string, password: string) {
        return submitAuth(API_ENDPOINTS.authLogin, username, password);
    }

    async function register(username: string, password: string) {
        return submitAuth(API_ENDPOINTS.authRegister, username, password);
    }

    async function logout() {
        try {
            await fetch(API_ENDPOINTS.authLogout, {
                method: 'POST',
                credentials: 'include',
            });
        } finally {
            persistUser(null);
            clearSessionCache();
            isHydrated.value = true;
        }
    }

    return {
        user,
        isHydrated,
        isSubmitting,
        restoreSession,
        validateSession,
        login,
        register,
        logout,
    };
});