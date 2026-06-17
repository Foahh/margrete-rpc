import { execSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcPath = resolve(__dirname, "../../src");

execSync("pip install ./node_modules/fumadocs-python", { stdio: "inherit" });
execSync("fumapy-generate margrete_rpc", {
  stdio: "inherit",
  env: { ...process.env, PYTHONPATH: srcPath },
});
