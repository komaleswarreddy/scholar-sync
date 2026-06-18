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

const nextConfig = {
  reactStrictMode: true,
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
