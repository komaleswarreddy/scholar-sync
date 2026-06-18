/**
 * Standalone admin portal session (separate from Clerk student auth).
 * Token is stored in sessionStorage and cleared when the tab closes.
 */

const STORAGE_KEY = 'admin_portal_token';

export function getAdminToken(): string | null {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(STORAGE_KEY);
}

export function setAdminToken(token: string): void {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(STORAGE_KEY, token);
}

export function clearAdminSession(): void {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(STORAGE_KEY);
}

export function hasAdminSession(): boolean {
  return Boolean(getAdminToken());
}

export function redirectToAdminLogin(): void {
  if (typeof window === 'undefined') return;
  const path = window.location.pathname;
  if (path.startsWith('/admin/login')) return;
  window.location.href = '/admin/login';
}
