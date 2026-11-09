import { loadOverrides } from "./settings.js";

const overrides = await loadOverrides(process.argv[2] ?? "overrides.json");
console.log(overrides);
