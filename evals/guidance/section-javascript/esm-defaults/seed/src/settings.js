import { readFile } from "node:fs/promises";

export async function loadOverrides(file) {
  const text = await readFile(file, "utf8");
  return JSON.parse(text);
}
