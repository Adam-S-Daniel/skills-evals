// Parse checker source as data. Never import or execute the fixture's code.
const fs = require("node:fs");
const path = require("node:path");
const acorn = require(path.join(__dirname, "../evals/browser-testing/seed/node_modules/acorn"));
const walk = require(path.join(__dirname, "../evals/browser-testing/seed/node_modules/acorn-walk"));

function name(node) {
  if (node.type === "Identifier") return node.name;
  if (node.type === "MemberExpression" && !node.computed) {
    const base = name(node.object);
    return base ? `${base}.${node.property.name}` : node.property.name;
  }
  if (node.type === "CallExpression") return name(node.callee);
  return "";
}

try {
  const sources = JSON.parse(fs.readFileSync(0, "utf8"));
  const calls = new Set();
  let behavior = false;
  for (const source of sources) {
    const tree = acorn.parse(source, { ecmaVersion: "latest", sourceType: "module" });
    const functions = new Map();
    walk.simple(tree, { FunctionDeclaration(node) {
      if (node.id) functions.set(node.id.name, node);
    }});
    const visited = new Set();
    const visitors = {
      FunctionDeclaration() {}, FunctionExpression() {}, ArrowFunctionExpression() {},
      CallExpression(node, state, recurse) {
        const called = name(node.callee);
        calls.add(called);
        calls.add(called.split(".").pop());
        // Browser observation must appear inside an assertion expression. A
        // parser's .parse() or a source string's .includes() is not behavior.
        if (/^(expect|assert)(\.|$)/.test(called)) {
          walk.recursive(node, null, {
            FunctionDeclaration() {}, FunctionExpression() {}, ArrowFunctionExpression() {},
            CallExpression(observed, ignored, next) {
              const observedName = name(observed.callee);
              const leaf = observedName.split(".").pop();
              const geometry = observedName.startsWith("page.") &&
                ["boundingBox", "screenshot"].includes(leaf);
              const matcher = /^(expect|assert)(\.|$)/.test(observedName) &&
                ["toHaveCSS", "toHaveScreenshot"].includes(leaf);
              if (geometry || matcher) behavior = true;
              walk.base.CallExpression(observed, ignored, next);
            }
          });
        }
        walk.base.CallExpression(node, state, recurse);
        const definition = functions.get(called);
        if (definition && !visited.has(definition)) {
          visited.add(definition);
          recurse(definition.body, state);
        }
        // Only known test/collection callbacks are treated as invoked. An
        // arbitrary function may retain or ignore its callback argument.
        const leaf = called.split(".").pop();
        const testCallback = ["test", "it", "describe", "beforeEach", "beforeAll",
          "afterEach", "afterAll"].includes(leaf);
        const collectionCallback = ["forEach", "map", "flatMap", "filter", "reduce",
          "some", "every", "find"].includes(leaf);
        if (testCallback || collectionCallback) {
          for (const argument of node.arguments) {
            if (["FunctionExpression", "ArrowFunctionExpression"].includes(argument.type)) {
              recurse(argument.body, state);
            }
          }
        }
      }
    };
    walk.recursive(tree, null, visitors);
  }
  process.stdout.write(JSON.stringify({ calls: [...calls], behavior }));
} catch {
  process.exitCode = 1;
}
