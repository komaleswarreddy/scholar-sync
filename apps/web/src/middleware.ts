import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Task A.a: Define routes that require authentication.
 * This protects /dashboard, /studio, /notes, and all their sub-paths.
 */
const isProtectedRoute = createRouteMatcher([
  '/dashboard(.*)',
  '/tutor-mode(.*)',
  '/studio(.*)',
  '/notes(.*)',
  '/analytics(.*)',
  '/api/v1/(.*)', // Optional: Protect API routes if they aren't handled by backend middleware
]);

// Hosts to treat as "development" (no subdomain)
const IGNORED_HOSTS = ['localhost', '127.0.0.1'];

/**
 * Extract tenant ID from host.
 */
function getTenantIdFromHost(host: string): string {
  if (!host) return 'default';
  if (IGNORED_HOSTS.some(h => host.includes(h))) return 'default';

  const parts = host.split('.');
  // e.g., tenant.scholarsync.com => tenant
  return parts.length > 2 ? parts[0] : 'default';
}

/**
 * Main Middleware: Combines Auth (Clerk) and Tenant logic.
 */
export default clerkMiddleware((auth, req) => {
  const host = req.headers.get('host') || '';
  const tenantId = getTenantIdFromHost(host);

  // --- 1. ROUTE PROTECTION (Tasks A.a, A.b, A.c) ---
  if (isProtectedRoute(req)) {
    /**
     * auth().protect() handles three things:
     * a. Checks if a session exists (Task A.a).
     * b. If not, redirects to your sign-in page (Task A.b).
     * c. Appends the current URL as a redirect_url so the user
     * returns here after login (Task A.c - Deep Linking).
     */
    auth().protect();
  }

  // --- 2. TENANT INJECTION ---
  const res = NextResponse.next();

  // Pass tenant info to backend via headers
  res.headers.set('x-tenant-id', tenantId);

  // Store in cookie for client-side components to use (UI branding, etc.)
  res.cookies.set('tenantId', tenantId, {
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production'
  });

  return res;
});

/**
 * Apply middleware to all paths except:
 * - Next.js internals (_next)
 * - Static files (images, favicon)
 * - Public landing pages (/)
 */
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
