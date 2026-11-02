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
    // fumadocs-python uses Griffe 1; typingdoc 0.3 installs conflicting Griffe 2 files.
    "--with",
    "griffe-typingdoc<0.3",
    "fumapy-generate",
    "margrete_rpc",
  ],
  { cwd: websitePath, stdio: "inherit" },
);
