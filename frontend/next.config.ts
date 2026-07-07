import path from "node:path";
import type { NextConfig } from "next";

// The browser always talks to Nova same-origin through `/api/*`; Next rewrites that to the
// FastAPI backend. This keeps CORS a non-issue in the browser and leaves a clean seam to slot
// authentication in at the Next edge later. Override the target with NEXT_PUBLIC_API_BASE.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Pin the project root so Turbopack doesn't walk up to a stray lockfile in $HOME.
  turbopack: { root: path.resolve(__dirname) },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_BASE}/:path*` }];
  },
};

export default nextConfig;
