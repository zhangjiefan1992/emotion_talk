import { cpSync, existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";

const publicDir = resolve("public");
const h5Dir = resolve("dist/build/h5");

if (existsSync(publicDir)) {
  mkdirSync(h5Dir, { recursive: true });
  cpSync(publicDir, h5Dir, { recursive: true });
}
