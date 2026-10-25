import path from "node:path";
import type { NextConfig } from "next";

// The browser always talks to Nova same-origin through `/api/*`; Next rewrites that to the
// FastAPI backend. This keeps CORS a non-issue in the browser and leaves a clean seam to slot
// authentication in at the Next edge later. Override the target with NEXT_PUBLIC_API_BASE.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

// Pin the project root to *this* directory. A stray package-lock.json in $HOME otherwise makes
// Next detect the workspace root as $HOME, so it resolves frontend's node_modules and relative CSS
// imports from the wrong base (MODULE_NOT_FOUND). __dirname is this file's dir under Next's loader.
const PROJECT_ROOT = path.resolve(__dirname);

const nextConfig: NextConfig = {
  output: "standalone", // the Docker image runs the traced server (docker/frontend.Dockerfile)
  devIndicators: false,
  turbopack: { root: PROJECT_ROOT },
  outputFileTracingRoot: PROJECT_ROOT,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_BASE}/:path*` }];
  },
};

export default nextConfig;
