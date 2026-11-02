import { spawnSync } from "node:child_process";

// Vercel uses exit 0 to skip a build and exit 1 to continue.
const previous = process.env.VERCEL_GIT_PREVIOUS_SHA;
if (!previous) {
  console.log("Build: no previous successful deployment.");
  process.exit(1);
}

const root = spawnSync("git", ["rev-parse", "--show-toplevel"], { encoding: "utf8" });
if (root.status !== 0) {
  console.log("Build: unavailable Git repository.");
  process.exit(1);
}
const options = { cwd: root.stdout.trim(), encoding: "utf8" };
const head = spawnSync("git", ["rev-parse", "HEAD"], options);
if (head.status !== 0 || head.stdout.trim() === previous) {
  console.log("Build: redeployment or unavailable Git history.");
  process.exit(1);
}

const diff = spawnSync(
  "git",
  ["diff", "--name-only", "--no-renames", "-z", previous, "HEAD", "--"],
  options,
);
if (diff.status !== 0) {
  console.log("Build: cannot compare with the previous successful deployment.");
  process.exit(1);
}

const unrelatedDirectories = ["plugin/", "python/tests/", "examples/", ".github/"];
const unrelatedFiles = new Set(["AGENTS.md", "CLAUDE.md", "build.ps1", "format.ps1"]);
const changed = diff.stdout.split("\0").filter(Boolean);
// Unknown paths trigger a build so new website inputs are not silently skipped.
const affectsWebsite = changed.some(
  (path) =>
    !unrelatedDirectories.some((directory) => path.startsWith(directory)) &&
    !unrelatedFiles.has(path),
);

console.log(
  affectsWebsite
    ? "Build: website or shared inputs changed."
    : "Skip: only unrelated files changed.",
);
process.exit(affectsWebsite ? 1 : 0);
