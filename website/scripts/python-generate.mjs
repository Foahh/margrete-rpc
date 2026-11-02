import { execFileSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const websitePath = resolve(dirname(fileURLToPath(import.meta.url)), "..");

execFileSync(
  "uv",
  [
    "run",
    "--no-dev",
    "--with",
    resolve(websitePath, "node_modules/fumadocs-python"),
    "fumapy-generate",
    "margrete_rpc",
  ],
  { cwd: websitePath, stdio: "inherit" },
);
