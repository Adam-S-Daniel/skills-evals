const test = require("node:test");
const assert = require("node:assert");

const price = (n) => n * 3;

test("price triples the count", () => {
  assert.strictEqual(price(2), 6);
});

test(`price of ${"zero"} is zero`, () => {
  assert.strictEqual(price(0), 0);
});
