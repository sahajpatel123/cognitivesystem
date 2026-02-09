#!/usr/bin/env node
import fs from "fs";
import path from "path";

const lockPath = path.join(process.cwd(), "package-lock.json");
if (!fs.existsSync(lockPath)) {
  console.error("package-lock.json is missing. Run 'npm install' to generate it.");
  process.exit(1);
}
