/** @type {import('next').NextConfig} */
const adminRedirects = [
  'users',
  'documents',
  'ncert-global',
  'queries',
  'rag-metrics',
  'agents',
  'guardrails',
  'endpoints',
  'cost-tokens',
  'alerts',
  'logs',
  'pipeline',
].map((segment) => ({
  source: `/analytics/${segment}`,
  destination: `/admin/${segment}`,
  permanent: false,
}));

// Security headers applied to every response.
// NOTE: The Content-Security-Policy here only restricts framing (anti-clickjacking).
// A full resource CSP (script-src/style-src/connect-src for Clerk + KaTeX + the API)
// should be layered on once each allowed origin is enumerated, to avoid breaking
// Clerk widgets, KaTeX, and Next.js assets.
const securityHeaders = [
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
  { key: 'Content-Security-Policy', value: "frame-ancestors 'none'" },
];

// HSTS only makes sense over HTTPS — enable in production deployments.
if (process.env.NODE_ENV === 'production') {
  securityHeaders.push({
    key: 'Strict-Transport-Security',
    value: 'max-age=31536000; includeSubDomains',
  });
}

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false, // do not advertise the framework via X-Powered-By
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/:path*',
      },
    ];
  },
  async redirects() {
    return adminRedirects;
  },
};

module.exports = nextConfig;
