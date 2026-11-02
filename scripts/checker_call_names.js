// The names a real-work fixture's JavaScript checker calls or supplies as a
// function (skills-evals#595).
//
// Reads {"sources": {relative path: source text}} as JSON on stdin and prints
// {"calls": [name, ...]}: the callee of every CallExpression and NewExpression
// (an identifier's name or a non-computed member's property name), and the key
// of every object property whose value is a function, or a `||`, `??` or `?:`
// with a function operand (a test injecting a dependency the code under test
// calls, as `newestPathCommit: overrides.newestPathCommit || (() => null)`). The source
// is parsed with Acorn as data and never imported or run. Any file that does
// not parse, as a module or as a script, makes the whole run exit 1, so the
// caller fails closed.
//
// Acorn and acorn-walk come from the trusted default branch's exact-pinned
// lockfile in evals/browser-testing/seed (npm ci --ignore-scripts there),
// never from the scaffold under review.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const seed = path.join(__dirname, "../evals/browser-testing/seed/node_modules");
const acorn = require(path.join(seed, "acorn"));
const walk = require(path.join(seed, "acorn-walk"));

function parse(source) {
  const options = { ecmaVersion: "latest", allowHashBang: true };
  try {
    return acorn.parse(source, { ...options, sourceType: "module" });
  } catch {
    return acorn.parse(source, { ...options, sourceType: "script" });
  }
}

function calleeName(node) {
  if (node.type === "Identifier") return node.name;
  if (node.type === "MemberExpression" && !node.computed && node.property.type === "Identifier") {
    return node.property.name;
  }
  if (node.type === "ChainExpression") return calleeName(node.expression);
  return null;
}

const FUNCTIONS = new Set(["FunctionExpression", "ArrowFunctionExpression"]);

function suppliesFunction(value) {
  if (!value) return false;
  if (FUNCTIONS.has(value.type)) return true;
  if (value.type === "LogicalExpression") return FUNCTIONS.has(value.left.type) || FUNCTIONS.has(value.right.type);
  if (value.type === "ConditionalExpression") {
    return FUNCTIONS.has(value.consequent.type) || FUNCTIONS.has(value.alternate.type);
  }
  return false;
}

try {
  const { sources } = JSON.parse(fs.readFileSync(0, "utf8"));
  const calls = new Set();
  for (const file of Object.keys(sources).sort()) {
    const tree = parse(sources[file]);
    const visit = (node) => {
      const found = calleeName(node.callee);
      if (found) calls.add(found);
    };
    walk.full(tree, (node) => {
      if (node.type === "CallExpression" || node.type === "NewExpression") visit(node);
      if (node.type === "Property" && !node.computed && suppliesFunction(node.value)) {
        const key = node.key.type === "Identifier" ? node.key.name
          : typeof node.key.value === "string" ? node.key.value : null;
        if (key) calls.add(key);
      }
    });
  }
  process.stdout.write(JSON.stringify({ calls: [...calls].sort() }));
} catch {
  // Fixed text only: the gate reads an untrusted branch.
  process.stderr.write("checker_call_names: a checker file could not be parsed\n");
  process.exit(1);
}
