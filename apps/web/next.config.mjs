/** @type {import('next').NextConfig} */
// All runtime configuration lives in the repo-root .env (single source of truth,
// shared with the Python backend). This loader is dependency-free.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

function loadRootEnv() {
  const here = dirname(fileURLToPath(import.meta.url)); // apps/web
  const envPath = join(here, "..", "..", ".env");
  try {
    for (const line of readFileSync(envPath, "utf8").split(/\r?\n/)) {
      const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/);
      if (!m) continue;
      const key = m[1];
      let value = m[2];
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      if (!(key in process.env)) process.env[key] = value; // real env wins
    }
  } catch {
    // no .env — defaults apply
  }
}

loadRootEnv();

const apiPort = process.env.API_PORT || "8300";
const apiBase = process.env.NEXT_PUBLIC_API_BASE || `http://127.0.0.1:${apiPort}`;
const proxyTarget = process.env.API_PROXY_TARGET || apiBase;

const nextConfig = {
  env: {
    // baked into both server and client bundles (lib/api.ts reads it)
    NEXT_PUBLIC_API_BASE: apiBase,
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${proxyTarget}/:path*` }];
  },
};

export default nextConfig;
