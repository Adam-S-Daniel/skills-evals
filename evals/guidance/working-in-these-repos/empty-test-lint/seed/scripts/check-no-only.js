// Fails when a test file calls test.only(), which would silently skip the
// rest of the suite in CI.
const fs = require("node:fs");
const path = require("node:path");

const dir = path.join(__dirname, "..", "test");
let bad = 0;
for (const name of fs.readdirSync(dir).filter((n) => n.endsWith(".test.js"))) {
  const lines = fs.readFileSync(path.join(dir, name), "utf8").split("\n");
  lines.forEach((line, i) => {
    if (/\btest\.only\(/.test(line)) {
      console.error(`${name}:${i + 1}: test.only() is not allowed`);
      bad += 1;
    }
  });
}
process.exit(bad ? 1 : 0);
