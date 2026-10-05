#!/usr/bin/env node
// Fixed, seed-provided objective verifier. It parses source; it never loads a spec.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const MODES = new Set([
  "new-spec", "admin-read", "single-entry-after-publish", "base-collection-guard",
  "config-origin", "consumer-spec", "preview-link-assertion",
]);
const EXAMPLES = new Set([
  "cms-posts-list-runtime.spec.js", "cms-preview-url.spec.js", "cms-smoke.spec.js",
]);
const SPEC_AST_SHA256 = "46a013d25c90bc26be9f3176b782bc1fb81ab88f66fd5419cd723edc8f5016d8";
const astPath = path.join(__dirname, "e2e", "spec-ast.js");
const PARSER_FILES = {
  "node_modules/acorn/package.json": "5c1ed7259579a7899b303f514b0194adcb9fe474fc7d136a84c6a45f10eefc84",
  "node_modules/acorn/dist/acorn.js": "fc3ed7b81e58464715d0291402892f22c3d86ea75302645a330390f85d8015c9",
  "node_modules/acorn-walk/package.json": "73c77feaf1224859bc6995cefe976d51cfd2abcd1edc0362df3149d8bd3633e3",
  "node_modules/acorn-walk/dist/walk.js": "1aa9615d8ea06e2126a21a4c21eb7b8b97a69e5eda256f06d2c48834a57cbf0e",
};

function source(name) {
  return fs.readFileSync(path.join(__dirname, name), "utf8");
}
function equalsHash(file, expected) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex") === expected;
}
function key(node) {
  return node && (node.name || node.value);
}
function hasBaseFixtureImport(ast, calleeName, stringValue) {
  return ast.body.some((statement) => statement.type === "VariableDeclaration" &&
    statement.declarations.some(({ id, init }) => id.type === "ObjectPattern" &&
      new Set(id.properties.map((prop) => key(prop.key))).has("test") &&
      new Set(id.properties.map((prop) => key(prop.key))).has("expect") &&
      init?.type === "CallExpression" && calleeName(init.callee) === "require" &&
      stringValue(init.arguments[0]) === "./base"));
}
function functionArg(call) {
  return call.arguments.find((arg) => arg && ["ArrowFunctionExpression", "FunctionExpression"].includes(arg.type));
}
function tagOf(call, stringValue) {
  for (const arg of call.arguments) {
    if (arg.type !== "ObjectExpression") continue;
    for (const prop of arg.properties) {
      if (key(prop.key) !== "tag") continue;
      const values = prop.value.type === "ArrayExpression" ? prop.value.elements : [prop.value];
      return values.map(stringValue).filter(Boolean);
    }
  }
  return [];
}
function testScopes(facts, walk, calleeName, stringValue) {
  const scopes = [];
  walk.ancestor(facts.ast, {
    CallExpression(node, ancestors) {
      const name = calleeName(node.callee);
      if (name !== "test") return;
      const callback = functionArg(node);
      if (!callback || !stringValue(node.arguments[0])) return;
      const describes = ancestors.filter((a) => a.type === "CallExpression" && calleeName(a.callee) === "test.describe");
      const tags = [...tagOf(node, stringValue), ...describes.flatMap((a) => tagOf(a, stringValue))];
      scopes.push({ callback, describes, tags });
    },
  });
  return scopes;
}
function scopeNodes(callback, walk, visit) {
  // Walk the test body, not callbacks or helpers it merely declares or passes.
  const visitors = {
    FunctionDeclaration() {},
    FunctionExpression() {},
    ArrowFunctionExpression() {},
  };
  for (const type of ["CallExpression", "VariableDeclarator", "AssignmentExpression"]) {
    visitors[type] = (node, state, descend) => {
      visit(node);
      walk.base[type](node, state, descend);
    };
  }
  walk.recursive(callback.body, null, visitors);
}
function callsIn(callback, walk, calleeName) {
  const calls = [];
  scopeNodes(callback, walk, (node) => {
    if (node.type !== "CallExpression") return;
    const name = calleeName(node.callee);
    calls.push({ name, tail: name?.split(".").pop(), args: node.arguments, node });
  });
  return calls.sort((a, b) => a.node.start - b.node.start);
}
function bindingsIn(ast, callback, walk) {
  const bindings = new Map();
  const changed = new Set();
  function add(statement) {
    if (statement.type !== "VariableDeclaration") return;
    for (const node of statement.declarations) {
      if (node.id.type !== "Identifier") continue;
      if (bindings.has(node.id.name)) changed.add(node.id.name);
      bindings.set(node.id.name, node.init);
    }
  }
  ast.body.forEach(add);
  if (callback.body.type === "BlockStatement") callback.body.body.forEach(add);
  scopeNodes(callback, walk, (node) => {
    if (node.type === "AssignmentExpression" && node.left.type === "Identifier") changed.add(node.left.name);
  });
  for (const name of changed) bindings.delete(name);
  return bindings;
}
function routeText(node, bindings, stringValue, seen = new Set()) {
  const direct = stringValue(node);
  if (direct !== null) return direct;
  if (node?.type === "NewExpression" && node.callee.type === "Identifier" && node.callee.name === "URL") {
    return stringValue(node.arguments[0]);
  }
  if (node?.type === "Identifier" && bindings.has(node.name) && !seen.has(node.name)) {
    seen.add(node.name);
    return routeText(bindings.get(node.name), bindings, stringValue, seen);
  }
  return null;
}
function isEntryRoute(value) {
  return value !== null && /#\/collections\/[^/]+\/entries\//.test(value);
}
function isPublish(call, analyzeNode, stringValue) {
  if (call.tail === "publishViaUi") return true;
  if (call.tail !== "click") return false;
  const target = call.node.callee.object;
  const facts = analyzeNode(target);
  return facts.strings.some((s) => /#cms-publish-button|\bpublish\b/i.test(s)) ||
    facts.getByRoleNames.some(({ name }) => /publish/i.test(name));
}
function previewAssertion(callback, walk, calleeName, stringValue) {
  const links = new Set();
  scopeNodes(callback, walk, (node) => {
    if (node.type !== "VariableDeclarator" || node.id.type !== "Identifier" ||
        node.init?.type !== "CallExpression" || calleeName(node.init.callee)?.split(".").pop() !== "getByRole") return;
    const [role, options] = node.init.arguments;
    if (stringValue(role) !== "link" || options?.type !== "ObjectExpression") return;
    const name = options.properties.find((entry) => key(entry.key) === "name")?.value;
    if (name?.regex && /preview/i.test(name.regex.pattern)) links.add(node.id.name);
    if (name && /preview/i.test(stringValue(name) || "")) links.add(node.id.name);
  });
  let found = false;
  scopeNodes(callback, walk, (node) => {
    if (node.type !== "CallExpression" || calleeName(node.callee)?.split(".").pop() !== "toHaveAttribute") return;
    const expectation = node.callee.object;
    if (expectation?.type !== "CallExpression" || calleeName(expectation.callee) !== "expect") return;
    const target = expectation.arguments[0];
    if (target?.type === "Identifier" && links.has(target.name) &&
        stringValue(node.arguments[0]) === "href" && node.arguments[1]) found = true;
  });
  return found;
}
function isPostsGuard(call, calleeName, stringValue) {
  if (!call || call.type !== "CallExpression" || calleeName(call.callee) !== "test.skip") return false;
  const negated = call.arguments[0];
  const predicate = negated && negated.type === "UnaryExpression" && negated.operator === "!" && negated.argument;
  return predicate && predicate.type === "CallExpression" &&
    calleeName(predicate.callee) === "cap.keepsBaseCollection" &&
    predicate.arguments[0]?.type === "Identifier" && predicate.arguments[0].name === "SITE_ROOT" &&
    stringValue(predicate.arguments[1]) === "posts";
}
function hasDirectGuard(describe, calleeName, stringValue) {
  const fn = functionArg(describe);
  if (!fn || fn.body.type !== "BlockStatement") return false;
  return fn.body.body.some((statement) =>
    statement.type === "ExpressionStatement" &&
    isPostsGuard(statement.expression, calleeName, stringValue));
}
function postsUse(call, analyzeNode, bindings, stringValue) {
  if (call.tail === "goto" && /#\/collections\/posts(?:\/|$)/.test(routeText(call.args[0], bindings, stringValue) || "")) return true;
  if (call.tail === "getByRole") {
    return analyzeNode(call.node).getByRoleNames.some(({ role, name }) => role === "link" && /posts/i.test(name));
  }
  return false;
}
function safeRoute(node, bindings, allowedBaseURLs, stringValue, calleeName, seen = new Set()) {
  const value = stringValue(node);
  if (value !== null && value.startsWith("/") && !value.startsWith("//") && !/^\/\\/.test(value)) return true;
  if (node?.type === "TemplateLiteral" && node.quasis[0].value.cooked === "" &&
      node.expressions.length && safeBaseURL(node.expressions[0], bindings, allowedBaseURLs, calleeName)) {
    const suffix = node.quasis[1]?.value.cooked || "";
    return suffix.startsWith("/") && !suffix.startsWith("//") && !/^\/\\/.test(suffix);
  }
  if (node?.type === "BinaryExpression" && node.operator === "+" &&
      safeBaseURL(node.left, bindings, allowedBaseURLs, calleeName)) {
    const suffix = stringValue(node.right);
    return suffix !== null && suffix.startsWith("/") && !suffix.startsWith("//");
  }
  if (node?.type === "Identifier" && bindings.has(node.name) && !seen.has(node.name)) {
    seen.add(node.name);
    return safeRoute(bindings.get(node.name), bindings, allowedBaseURLs, stringValue, calleeName, seen);
  }
  if (node?.type === "NewExpression" && calleeName(node.callee) === "URL") {
    return safeRoute(node.arguments[0], bindings, allowedBaseURLs, stringValue, calleeName) &&
      safeBaseURL(node.arguments[1], bindings, allowedBaseURLs, calleeName);
  }
  return false;
}
function safeBaseURL(node, bindings, allowedBaseURLs, calleeName, seen = new Set()) {
  if (node?.type !== "Identifier") return false;
  if (allowedBaseURLs.has(node.name)) return true;
  if (!bindings.has(node.name) || seen.has(node.name)) return false;
  seen.add(node.name);
  return safeBaseURL(bindings.get(node.name), bindings, allowedBaseURLs, calleeName, seen);
}
function baseURLParameters(callback, walk) {
  const names = new Set();
  for (const param of callback.params) {
    if (param.type === "ObjectPattern") {
      for (const prop of param.properties) {
        if (key(prop.key) === "baseURL" && prop.value.type === "Identifier") names.add(prop.value.name);
      }
    }
  }
  scopeNodes(callback, walk, (node) => {
    if (node.type === "AssignmentExpression" && node.left.type === "Identifier") names.delete(node.left.name);
  });
  return names;
}
function metaSpecs(config, parse, stringValue) {
  const names = new Set();
  for (const statement of parse(config).body) {
    if (statement.type !== "VariableDeclaration") continue;
    for (const entry of statement.declarations) {
      if (entry.id.name !== "PLATFORM_META_SPECS" || entry.init?.type !== "ArrayExpression") continue;
      for (const element of entry.init.elements) {
        const name = stringValue(element);
        if (name) names.add(name);
      }
    }
  }
  return names;
}

function verify(mode) {
  if (!MODES.has(mode) || !equalsHash(astPath, SPEC_AST_SHA256)) return false;
  if (!Object.entries(PARSER_FILES).every(([file, digest]) =>
    equalsHash(path.join(__dirname, file), digest))) return false;
  const { analyzeSpec, analyzeNode, parse, stringValue, calleeName } = require("./e2e/spec-ast");
  const walk = require("acorn-walk");
  const files = fs.readdirSync(path.join(__dirname, "e2e"))
    .filter((name) => name.endsWith(".spec.js") && !EXAMPLES.has(name)).sort();
  if (!files.length) return false;
  const specs = files.map((name) => {
    const facts = analyzeSpec(source(path.join("e2e", name)));
    const scopes = testScopes(facts, walk, calleeName, stringValue).map((scope) => ({
      ...scope, bindings: bindingsIn(facts.ast, scope.callback, walk),
    }));
    return { name, facts, scopes };
  });
  if (specs.some(({ scopes }) => !scopes.length)) return false;

  if (mode === "new-spec") return specs.every(({ facts }) =>
    hasBaseFixtureImport(facts.ast, calleeName, stringValue));
  if (mode === "preview-link-assertion") return specs.every(({ scopes }) =>
    scopes.some(({ callback }) => previewAssertion(callback, walk, calleeName, stringValue)));
  if (mode === "admin-read") return specs.every(({ scopes }) =>
    scopes.every(({ tags, callback, bindings }) => tags.includes("@admin-read") && !tags.includes("@admin-write") &&
      callsIn(callback, walk, calleeName).some((call) => call.tail === "goto" &&
        (routeText(call.args[0], bindings, stringValue) || "").includes("/admin/"))));
  if (mode === "single-entry-after-publish") return specs.every(({ scopes }) => scopes.every(({ callback, bindings }) => {
    let published = false;
    let entryVisits = 0;
    return callsIn(callback, walk, calleeName).every((call) => {
      if (call.tail === "goto" && isEntryRoute(routeText(call.args[0], bindings, stringValue))) {
        entryVisits += 1;
        if (published) return false;
      }
      if (isPublish(call, analyzeNode, stringValue)) {
        published = true;
        if (entryVisits > 1) return false;
      }
      return true;
    });
  }));
  if (mode === "base-collection-guard") return specs.every(({ facts, scopes }) => {
    return facts.requires.has("./site-capabilities") && scopes.every(({ describes, callback, bindings }) => {
      const calls = callsIn(callback, walk, calleeName);
      const firstUse = calls.find((call) => postsUse(call, analyzeNode, bindings, stringValue));
      if (!firstUse) return false;
      const inline = calls.some((call) => call.node.start < firstUse.node.start &&
        isPostsGuard(call.node, calleeName, stringValue));
      return inline || describes.some((describe) => describe.start < callback.start &&
        hasDirectGuard(describe, calleeName, stringValue));
    });
  });
  if (mode === "config-origin") return specs.every(({ scopes }) => {
    return scopes.every(({ callback, bindings }) => {
      const gotos = callsIn(callback, walk, calleeName).filter((call) => call.tail === "goto");
      const allowed = baseURLParameters(callback, walk);
      return gotos.length > 0 && gotos.every(({ args }) =>
        safeRoute(args[0], bindings, allowed, stringValue, calleeName));
    });
  });
  if (mode === "consumer-spec") {
    const meta = metaSpecs(source("playwright.config.js"), parse, stringValue);
    return specs.every(({ name }) => !meta.has(name));
  }
  return false;
}

try {
  if (!verify(process.argv[2])) process.exitCode = 1;
} catch {
  process.exitCode = 1;
}
