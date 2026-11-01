/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  // a running dev server and the gate's `next build` must not share a build folder
  distDir: process.env.NODE_ENV === "development" ? ".next-dev" : ".next",
  // the gate type-checks with `tsc --noEmit`; the vendored app ships no ESLint config
  eslint: { ignoreDuringBuilds: true },
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
