const test = require("node:test");
const assert = require("node:assert");
const { route } = require("../src/routes");

test("health answers ok", () => {
  assert.deepStrictEqual(route("/health"), { status: 200, body: "ok" });
});

test("unknown paths are 404", () => {
  assert.strictEqual(route("/nope").status, 404);
});
