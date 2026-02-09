#!/usr/bin/env node
import fs from "fs";
import path from "path";

const targets = process.argv.slice(2);
if (targets.length === 0) {
  console.error("Usage: node scripts/rm.mjs <path> [path...]");
  process.exit(1);
}

for (const target of targets) {
  const resolved = path.resolve(process.cwd(), target);
  try {
    fs.rmSync(resolved, { recursive: true, force: true });
    // eslint-disable-next-line no-console
    console.log(`Removed ${resolved}`);
  } catch (err) {
    console.error(`Failed to remove ${resolved}:`, err);
    process.exitCode = 1;
  }
}
