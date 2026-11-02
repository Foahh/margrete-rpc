import * as fs from "node:fs/promises";

import * as Python from "fumadocs-python";
import { rimraf } from "rimraf";

const out = "content/docs/reference";

async function generate() {
  await rimraf(out);

  const content = JSON.parse(await fs.readFile("./margrete_rpc.json", "utf-8"));

  const converted = Python.convert(content, {
    baseUrl: "/docs/reference",
    groupBy: "none",
  });

  await Python.write(converted, out);
}

void generate();
