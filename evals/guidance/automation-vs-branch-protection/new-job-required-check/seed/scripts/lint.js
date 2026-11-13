// Fails when a source file has a trailing space.
const fs = require("node:fs");
const bad = fs.readdirSync("test").filter((f) => /[ \t]$/m.test(fs.readFileSync(`test/${f}`, "utf8")));
if (bad.length) { console.error(`trailing whitespace: ${bad.join(", ")}`); process.exit(1); }
