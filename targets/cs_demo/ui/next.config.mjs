/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  // Bylaw: replays (and, after VZ3 phase 2, the live chat) come from the Bylaw API, bylaw/api.py.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: (process.env.BYLAW_API_URL ?? "http://127.0.0.1:8000") + "/api/:path*",
      },
    ];
  },
};

export default nextConfig;
