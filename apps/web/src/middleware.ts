import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PROTECTED_PREFIXES = [
  '/home',
  '/library',
  '/notebook',
  '/profile',
  '/dashboard',
  '/tutor',
  '/tutor-mode',
  '/problem-solver',
  '/studio',
  '/notes',
  '/studios',
  '/assets',
  '/study-planner',
  '/analytics',
  '/admin',
];

const AUTH_PATHS = ['/sign-in', '/sign-up'];

const IGNORED_HOSTS = ['localhost', '127.0.0.1'];

function getTenantIdFromHost(host: string): string {
  if (!host) return 'default';
  if (IGNORED_HOSTS.some((h) => host.includes(h))) return 'default';
  const parts = host.split('.');
  return parts.length > 2 ? parts[0] : 'default';
}

function isProtected(pathname: string): boolean {
  return PROTECTED_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

export function middleware(req: NextRequest) {
  const host = req.headers.get('host') || '';
  const tenantId = getTenantIdFromHost(host);
  const pathname = req.nextUrl.pathname;
  const signedOut = req.nextUrl.searchParams.get('signed_out') === '1';
  const hasSession = req.cookies.get('platform_session')?.value === '1';

  if (isProtected(pathname) && !hasSession && !pathname.startsWith('/admin/login')) {
    const signIn = new URL('/sign-in', req.url);
    signIn.searchParams.set('redirect', pathname);
    return NextResponse.redirect(signIn);
  }

  if (AUTH_PATHS.includes(pathname)) {
    if (signedOut) {
      const res = NextResponse.next();
      res.cookies.set('platform_session', '', { path: '/', maxAge: 0 });
      res.cookies.set('platform_role', '', { path: '/', maxAge: 0 });
      res.headers.set('x-tenant-id', tenantId);
      res.cookies.set('tenantId', tenantId, {
        path: '/',
        sameSite: 'lax',
        secure: process.env.NODE_ENV === 'production',
      });
      return res;
    }
    if (hasSession) {
      const role = req.cookies.get('platform_role')?.value;
      const dest = role === 'schooladmin' ? '/admin/users' : '/home';
      return NextResponse.redirect(new URL(dest, req.url));
    }
  }

  const res = NextResponse.next();
  res.headers.set('x-tenant-id', tenantId);
  res.cookies.set('tenantId', tenantId, {
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  });
  return res;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
