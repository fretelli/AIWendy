const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname),

  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
    ],
    formats: ['image/avif', 'image/webp'],
  },

  // Headers for security
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ];
  },

  async redirects() {
    return [
      { source: '/agent/capital', destination: '/agent/market/capital', permanent: true },
      { source: '/agent/capital/macro', destination: '/agent/market/macro', permanent: true },
      { source: '/agent/capital/futures', destination: '/agent/market/futures', permanent: true },
      { source: '/agent/capital/options', destination: '/agent/market/options', permanent: true },
      { source: '/agent/market/opportunities', destination: '/agent/opportunities', permanent: true },
    ];
  },

};

module.exports = nextConfig;
