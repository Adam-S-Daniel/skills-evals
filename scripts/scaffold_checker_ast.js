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

const functions = new Set(["FunctionDeclaration", "FunctionExpression", "ArrowFunctionExpression"]);
const matchers = new Set(["toBe", "toEqual", "toStrictEqual", "toMatchObject", "toMatchSnapshot",
  "toBeGreaterThan", "toBeGreaterThanOrEqual", "toBeLessThan", "toBeLessThanOrEqual",
  "toBeCloseTo", "toHaveCSS", "toHaveScreenshot"]);

// Only model the explicit Playwright CLI form used by these fixtures. Unknown
// flags, dynamic file patterns and location selectors cannot grant admission.
function selection(argv) {
  if (argv[0] !== "node" || !argv[1]?.endsWith("/@playwright/test/cli.js") || argv[2] !== "test") return null;
  const result = { files: [], grep: null, invert: null };
  for (let i = 3; i < argv.length; i++) {
    const arg = argv[i];
    const [flag, inline] = arg.split(/=(.*)/s);
    if (["-g", "--grep", "--grep-invert", "--config", "-c", "--workers"].includes(flag)) {
      const value = inline === undefined ? argv[++i] : inline;
      if (!value) return null;
      if (flag === "-g" || flag === "--grep") result.grep = new RegExp(value);
      if (flag === "--grep-invert") result.invert = new RegExp(value);
    } else if (/^[\w./-]+\.(?:js|mjs|cjs)$/.test(arg) && !arg.startsWith("-")) {
      result.files.push(arg);
    } else return null;
  }
  return result.files.length ? result : null;
}

try {
  const { sources, selections } = JSON.parse(fs.readFileSync(0, "utf8"));
  const selected = selections.map(selection).filter(Boolean);
  const calls = new Set();
  let behavior = false;
  const modules = new Map();
  function moduleFor(file) {
    if (modules.has(file)) return modules.get(file);
    const tree = acorn.parse(sources[file], { ecmaVersion: "latest", sourceType: "module" });
    const mod = { file, tree, definitions: new Map(), imports: new Map(),
                  importDeclarations: new Set(), exports: new Map() };
    modules.set(file, mod);
    // Only module-scope declarations are available as helpers. A nested or
    // shadowed definition must not be mistaken for the callable being invoked.
    for (const original of tree.body) {
      const node = original.type === "ExportNamedDeclaration" ? original.declaration : original;
      if (node?.type === "FunctionDeclaration" && node.id) mod.definitions.set(node.id.name, node);
      if (node?.type === "VariableDeclaration") for (const item of node.declarations) {
        if (item.id.type === "Identifier" && functions.has(item.init?.type)) mod.definitions.set(item.id.name, item.init);
        if (item.init?.type === "CallExpression" && name(item.init.callee) === "require" &&
            typeof item.init.arguments[0]?.value === "string" && item.id.type === "ObjectPattern") {
          mod.importDeclarations.add(item);
          for (const property of item.id.properties) if (property.type === "Property" && property.value.type === "Identifier") {
            mod.imports.set(property.value.name, [item.init.arguments[0].value, property.key.name]);
          }
        }
      }
      if (original.type === "ImportDeclaration") for (const spec of original.specifiers) {
        if (spec.type === "ImportSpecifier") mod.imports.set(spec.local.name, [original.source.value, spec.imported.name]);
      }
      if (original.type === "ExportNamedDeclaration") {
        if (node?.id) mod.exports.set(node.id.name, node.id.name);
        if (node?.type === "VariableDeclaration") for (const item of node.declarations) {
          if (item.id.type === "Identifier") mod.exports.set(item.id.name, item.id.name);
        }
        for (const spec of original.specifiers) mod.exports.set(spec.exported.name, spec.local.name);
      }
      if (node?.type === "ExpressionStatement" && node.expression.type === "AssignmentExpression") {
        const assignment = node.expression;
        const target = name(assignment.left);
        if (target.startsWith("exports.") && assignment.right.type === "Identifier") {
          mod.exports.set(target.slice(8), assignment.right.name);
        }
        if (target === "module.exports" && assignment.right.type === "ObjectExpression") {
          for (const item of assignment.right.properties) if (item.type === "Property" && item.value.type === "Identifier") {
            mod.exports.set(item.key.name, item.value.name);
          }
        }
      }
    }
    return mod;
  }
  function helper(mod, called) {
    if (mod.definitions.has(called)) return [mod, mod.definitions.get(called)];
    const imported = mod.imports.get(called);
    if (!imported || !imported[0].startsWith(".")) return null;
    const relative = path.posix.normalize(path.posix.join(path.posix.dirname(mod.file), imported[0]));
    const file = [relative, relative + ".js", relative + "/index.js"].find(p => Object.hasOwn(sources, p));
    if (!file) return null;
    const target = moduleFor(file);
    const local = target.exports.get(imported[1]);
    return local && target.definitions.has(local) ? [target, target.definitions.get(local)] : null;
  }
  function assertion(node) {
    if (node.callee.type !== "MemberExpression" || node.callee.computed || !matchers.has(node.callee.property.name)) return false;
    let receiver = node.callee.object;
    while (receiver.type === "MemberExpression" && !receiver.computed &&
           ["not", "resolves", "rejects"].includes(receiver.property.name)) receiver = receiver.object;
    if (receiver.type !== "CallExpression" || name(receiver.callee) !== "expect") return false;
    if (["toHaveCSS", "toHaveScreenshot"].includes(node.callee.property.name)) {
      return receiver.arguments.some(arg => name(arg).startsWith("page.") || name(arg) === "page");
    }
    let observed = false;
    for (const arg of receiver.arguments) walk.recursive(arg, null, {
      FunctionDeclaration() {}, FunctionExpression() {}, ArrowFunctionExpression() {},
      CallExpression(call, state, recurse) {
        const called = name(call.callee);
        if (called.startsWith("page.") && ["boundingBox", "screenshot"].includes(called.split(".").pop())) observed = true;
        walk.base.CallExpression(call, state, recurse);
      }
    });
    return observed;
  }
  function analyze(node, mod, evidence, inherited = new Set(), hooks = false) {
    const shadowed = new Set(inherited);
    function bind(pattern) {
      if (!pattern) return;
      if (pattern.type === "Identifier") shadowed.add(pattern.name);
      else if (pattern.type === "ObjectPattern") for (const item of pattern.properties) bind(item.value || item.argument);
      else if (pattern.type === "ArrayPattern") for (const item of pattern.elements) bind(item);
      else if (pattern.type === "AssignmentPattern") bind(pattern.left);
      else if (pattern.type === "RestElement") bind(pattern.argument);
    }
    const body = functions.has(node.type) ? node.body : node;
    if (functions.has(node.type)) for (const parameter of node.params) bind(parameter);
    walk.recursive(body, null, {
      FunctionDeclaration(declaration) {
        if (mod.definitions.get(declaration.id?.name) !== declaration) bind(declaration.id);
      },
      FunctionExpression() {}, ArrowFunctionExpression() {},
      VariableDeclarator(declaration, state, recurse) {
        if (!mod.importDeclarations.has(declaration) &&
            mod.definitions.get(declaration.id.name) !== declaration.init) bind(declaration.id);
        if (declaration.init) recurse(declaration.init, state);
      }
    });
    const visitors = {
      FunctionDeclaration() {}, FunctionExpression() {}, ArrowFunctionExpression() {},
      CallExpression(call, state, recurse) {
        const called = name(call.callee);
        // A titled callback registers one skipped test. Runtime modifiers
        // suppress the whole candidate's evidence, even after an assertion.
        // Only a literal false condition proves that a modifier cannot skip.
        if (["test.skip", "test.fixme", "it.skip", "it.fixme"].includes(called) &&
            !(typeof call.arguments[0]?.value === "string" &&
              call.arguments.some(arg => functions.has(arg.type))) &&
            !(call.arguments[0]?.type === "Literal" && call.arguments[0].value === false)) {
          evidence.skipped = true;
        }
        evidence.calls.add(called);
        evidence.calls.add(called.split(".").pop());
        if (!shadowed.has("expect") && assertion(call)) evidence.behavior = true;
        walk.base.CallExpression(call, state, recurse);
        const definition = shadowed.has(called) ? null : helper(mod, called);
        if (definition && !evidence.visited.has(definition[1])) {
          evidence.visited.add(definition[1]);
          analyze(definition[1], definition[0], evidence);
        }
        if (["forEach", "map", "flatMap", "filter", "reduce", "some", "every", "find"].includes(called.split(".").pop()) ||
            hooks && ["test.beforeEach", "test.beforeAll"].includes(called)) {
          for (const argument of call.arguments) if (functions.has(argument.type)) analyze(argument, mod, evidence, shadowed);
        }
      }
    };
    walk.recursive(body, null, visitors);
  }
  function evidenceFor(node, mod, hooks = false) {
    const evidence = { calls: new Set(), behavior: false, skipped: false, visited: new Set() };
    analyze(node, mod, evidence, new Set(), hooks);
    return evidence;
  }
  for (const file of Object.keys(sources)) {
    const choices = selected.filter(s => s.files.some(f => file === f || file.endsWith("/" + f)));
    if (!choices.length) continue;
    const mod = moduleFor(file);
    // Focus changes the set of runnable tests throughout a project. Without
    // evaluating configuration and all files, the safe result is no evidence.
    let focused = false;
    walk.simple(mod.tree, { CallExpression(node) {
      if (["test.only", "it.only", "test.describe.only", "describe.only"].includes(name(node.callee))) focused = true;
    }});
    if (focused) continue;
    function collect(node, titles) {
      // Module/suite modifiers and setup hooks apply to every nested test.
      // Analyze their reachable helpers, excluding test registration callbacks.
      if (evidenceFor(node, mod, true).skipped) return;
      walk.recursive(node, titles, {
        FunctionDeclaration() {}, FunctionExpression() {}, ArrowFunctionExpression() {},
        CallExpression(call, parents, recurse) {
          const called = name(call.callee);
          if (["test", "it", "test.describe", "describe"].includes(called)) {
            const title = call.arguments[0];
            const callback = call.arguments.find(arg => functions.has(arg.type));
            if (typeof title?.value !== "string" || !callback) return;
            const full = [...parents, title.value];
            if (["test.describe", "describe"].includes(called)) collect(callback.body, full);
            else if (choices.some(s => (!s.grep || s.grep.test(full.join(" "))) &&
                                        (!s.invert || !s.invert.test(full.join(" "))))) {
              const evidence = evidenceFor(callback, mod);
              if (!evidence.skipped) {
                for (const called of evidence.calls) calls.add(called);
                behavior ||= evidence.behavior;
              }
            }
            return;
          }
          // Skipped tests/suites and arbitrary callback registrars have no roots.
          walk.base.CallExpression(call, parents, recurse);
        }
      });
    }
    collect(mod.tree, []);
  }
  process.stdout.write(JSON.stringify({ calls: [...calls], behavior }));
} catch {
  process.exitCode = 1;
}
