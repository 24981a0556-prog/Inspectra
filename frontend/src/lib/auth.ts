/**
 * Auth helpers — manage JWT token and current user in sessionStorage.
 * sessionStorage clears on tab close, which is better for security than localStorage
 * on a shared government workstation.
 */

import type { User } from '@/types';

const TOKEN_KEY = 'inspectra_token';
const USER_KEY = 'inspectra_user';

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export function getCurrentUser(): User | null {
  const raw = sessionStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function setCurrentUser(user: User): void {
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
