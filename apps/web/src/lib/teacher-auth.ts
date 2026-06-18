/**
 * Standalone teacher portal session (separate from Clerk student auth).
 * Token is stored in sessionStorage and cleared when the tab closes.
 */

const STORAGE_KEY = 'teacher_portal_token';

export const TEACHER_PORTAL_EMAIL = 'teacher@gmail.com';
export const TEACHER_PORTAL_PASSWORD = 'admin123';

export function getTeacherToken(): string | null {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(STORAGE_KEY);
}

export function setTeacherToken(token: string): void {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(STORAGE_KEY, token);
}

export function clearTeacherSession(): void {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(STORAGE_KEY);
}

export function hasTeacherSession(): boolean {
  return Boolean(getTeacherToken());
}

export function validateTeacherLogin(email: string, password: string): boolean {
  const normalizedEmail = email.trim().toLowerCase();
  return (
    normalizedEmail === TEACHER_PORTAL_EMAIL.toLowerCase() &&
    password === TEACHER_PORTAL_PASSWORD
  );
}

export function redirectToTeacherLogin(): void {
  if (typeof window === 'undefined') return;
  const path = window.location.pathname;
  if (path.startsWith('/teacher/login')) return;
  window.location.href = '/teacher/login';
}
