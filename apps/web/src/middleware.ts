import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Routes that require Clerk student authentication.
 * Admin ops portal (/admin/*) uses standalone email/password — excluded here.
 */
const isProtectedRoute = createRouteMatcher([
  '/home(.*)',
  '/library(.*)',
  '/notebook(.*)',
  '/profile(.*)',
  '/dashboard(.*)',
  '/tutor(.*)',
  '/tutor-mode(.*)',
  '/problem-solver(.*)',
  '/studio(.*)',
  '/notes(.*)',
  '/studios(.*)',
  '/assets(.*)',
  '/study-planner(.*)',
  '/analytics',
  '/api/v1/(.*)',
]);

const isAdminRoute = createRouteMatcher(['/admin(.*)']);

// Hosts to treat as "development" (no subdomain)
const IGNORED_HOSTS = ['localhost', '127.0.0.1'];

function getTenantIdFromHost(host: string): string {
  if (!host) return 'default';
  if (IGNORED_HOSTS.some(h => host.includes(h))) return 'default';

  const parts = host.split('.');
  return parts.length > 2 ? parts[0] : 'default';
}

export default clerkMiddleware((auth, req) => {
  const host = req.headers.get('host') || '';
  const tenantId = getTenantIdFromHost(host);

  if (isProtectedRoute(req) && !isAdminRoute(req)) {
    auth().protect();
  }

  const res = NextResponse.next();

  res.headers.set('x-tenant-id', tenantId);

  res.cookies.set('tenantId', tenantId, {
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production'
  });

  return res;
});

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
