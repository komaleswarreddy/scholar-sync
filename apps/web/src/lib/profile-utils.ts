import type { PlatformUser } from '@/lib/platform-auth';

const PROFILE_FIELDS: (keyof PlatformUser)[] = [
  'username',
  'first_name',
  'last_name',
  'email',
  'mobile',
  'institute',
  'class_level',
];

export function computeProfileCompletion(user: PlatformUser | null): number {
  if (!user) return 0;
  const filled = PROFILE_FIELDS.filter((key) => {
    const v = user[key];
    return typeof v === 'string' && v.trim().length > 0;
  }).length;
  return Math.round((filled / PROFILE_FIELDS.length) * 100);
}

export function profileDisplayName(user: PlatformUser | null): string {
  if (!user) return 'Student';
  const parts = [user.first_name, user.last_name].filter(Boolean);
  if (parts.length) return parts.join(' ');
  if (user.username?.trim()) return user.username.trim();
  if (user.email?.includes('@')) return user.email.split('@')[0];
  return 'Student';
}

/** Short name for home greeting — never shows a raw email address. */
export function profileGreetingName(user: PlatformUser | null): string {
  if (!user) return 'there';
  if (user.first_name?.trim()) return user.first_name.trim();
  if (user.username?.trim()) return user.username.trim();
  if (user.email?.includes('@')) return user.email.split('@')[0];
  return 'there';
}

export function profileInitials(user: PlatformUser | null): string {
  if (!user) return 'U';
  const first = user.first_name?.[0] ?? '';
  const last = user.last_name?.[0] ?? '';
  if (first && last) return `${first}${last}`.toUpperCase();
  if (user.username?.[0]) return user.username[0].toUpperCase();
  return 'U';
}

export function profileClassBoardLine(user: PlatformUser | null): string {
  if (!user) return '';
  const parts = [user.class_level, user.institute].filter(Boolean);
  return parts.join(' • ');
}

export function emptyProfileLabel(value: string | null | undefined, fallback = 'Not set'): string {
  const v = (value ?? '').trim();
  return v || fallback;
}
