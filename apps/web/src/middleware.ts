import { clerkMiddleware } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Hosts to treat as "development" (no subdomain)
const IGNORED_HOSTS = ['localhost', '127.0.0.1'];

/**
 * Extract tenant ID from host.
 * Returns "default" for localhost or unknown host.
 */
function getTenantIdFromHost(host: string): string {
  if (!host) return 'default';
  if (IGNORED_HOSTS.some(h => host.includes(h))) return 'default';

  const parts = host.split('.');
  // e.g., tenant.example.com => tenant
  return parts.length > 2 ? parts[0] : 'default';
}

/**
 * Custom middleware to add tenant info
 */
function subdomainMiddleware(req: NextRequest) {
  const host = req.headers.get('host') || '';
  const tenantId = getTenantIdFromHost(host);

  
  // Add tenantId to request headers for API requests
  const res = NextResponse.next();
  res.headers.set('x-tenant-id', tenantId);

  // Add tenantId cookie for frontend JS access
  res.cookies.set('tenantId', tenantId, { path: '/' });

  return res;
}

/**
 * Combined middleware: Clerk + subdomain
 */
export default function middleware(req: NextRequest) {
  // Run Clerk middleware first (auth handling)
  const clerkResponse = clerkMiddleware()(req, {} as any);
  if (clerkResponse instanceof NextResponse) return clerkResponse;

  // Run subdomain detection
  return subdomainMiddleware(req);
}

/**
 * Apply middleware to all paths except Next.js internals
 */
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};

