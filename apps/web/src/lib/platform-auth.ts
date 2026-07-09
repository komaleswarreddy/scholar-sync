/**
 * Platform auth session — unified username/password login token.
 */

const TOKEN_KEY = 'platform_token';
const SESSION_COOKIE = 'platform_session';
const ROLE_COOKIE = 'platform_role';
const PROFILE_SYNCED_AT_KEY = 'platform_user_synced_at';

export const SIGN_OUT_QUERY = 'signed_out';
export const PLATFORM_SESSION_CHANGED = 'platform-session-changed';

function notifyPlatformSessionChanged(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(PLATFORM_SESSION_CHANGED));
}

export type PlatformUser = {
  id: string;
  username?: string | null;
  email?: string | null;
  role: string;
  first_name?: string | null;
  last_name?: string | null;
  mobile?: string | null;
  institute?: string | null;
  class_level?: string | null;
  expertise_tier?: string | null;
  is_bootstrap_admin?: boolean;
  is_active?: boolean;
};

export function getPlatformToken(): string | null {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setPlatformToken(token: string, role?: string | null): void {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(TOKEN_KEY, token);
  document.cookie = `${SESSION_COOKIE}=1; path=/; SameSite=Lax; max-age=${60 * 60 * 24}`;
  if (role) {
    document.cookie = `${ROLE_COOKIE}=${encodeURIComponent(role)}; path=/; SameSite=Lax; max-age=${60 * 60 * 24}`;
  }
}

/** Persist token + user profile and role cookie (used after login). */
export function establishPlatformSession(token: string, user: PlatformUser): void {
  if (!token?.trim()) {
    throw new Error('establishPlatformSession: missing access token');
  }
  if (!user?.id) {
    throw new Error('establishPlatformSession: login response missing user.id');
  }
  const role =
    user.is_bootstrap_admin || user.role === 'schooladmin' ? 'schooladmin' : user.role || 'student';
  setPlatformToken(token, role);
  setStoredPlatformUser(user);
  try {
    sessionStorage.setItem(PROFILE_SYNCED_AT_KEY, String(Date.now()));
  } catch {
    /* ignore */
  }
  notifyPlatformSessionChanged();
}

/** Timestamp (ms) of the last time the user profile was known-fresh (login or /auth/me). */
export function getStoredProfileSyncedAt(): number | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = sessionStorage.getItem(PROFILE_SYNCED_AT_KEY);
    return raw ? Number(raw) : null;
  } catch {
    return null;
  }
}

export function clearPlatformSession(): void {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem('platform_user');
  sessionStorage.removeItem(PROFILE_SYNCED_AT_KEY);
  document.cookie = `${SESSION_COOKIE}=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  document.cookie = `${ROLE_COOKIE}=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  notifyPlatformSessionChanged();
}

/** Full sign-out: clear platform + legacy admin tokens, land on login (not student app). */
export function signOutAndRedirect(): void {
  if (typeof window === 'undefined') return;
  clearPlatformSession();
  try {
    sessionStorage.removeItem('admin_portal_token');
  } catch {
    /* ignore */
  }
  window.location.href = `/sign-in?${SIGN_OUT_QUERY}=1`;
}

export function hasPlatformSession(): boolean {
  return Boolean(getPlatformToken());
}

export function getStoredPlatformUser(): PlatformUser | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = sessionStorage.getItem('platform_user');
    return raw ? (JSON.parse(raw) as PlatformUser) : null;
  } catch {
    return null;
  }
}

export function setStoredPlatformUser(user: PlatformUser): void {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem('platform_user', JSON.stringify(user));
}

export function getRoleFromToken(token: string | null): string | null {
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.role ?? null;
  } catch {
    return null;
  }
}

export function isSchoolAdmin(user: PlatformUser | null, token?: string | null): boolean {
  if (!user) return false;
  if (user.role === 'schooladmin' || user.is_bootstrap_admin) return true;
  const role = getRoleFromToken(token ?? getPlatformToken());
  return role === 'schooladmin';
}

export function redirectToSignIn(): void {
  if (typeof window === 'undefined') return;
  if (window.location.pathname.startsWith('/sign-in')) return;
  window.location.href = `/sign-in?${SIGN_OUT_QUERY}=1`;
}
