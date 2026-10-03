/** @type {import('next').NextConfig} */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

function loadRootEnv() {
  const here = dirname(fileURLToPath(import.meta.url));
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
      if (!(key in process.env)) process.env[key] = value;
    }
  } catch {
    // No repo-root .env is valid for reproducible image builds. Runtime-only
    // service addresses are read by server code and route handlers instead.
  }
}

loadRootEnv();

const nextConfig = {};

export default nextConfig;
