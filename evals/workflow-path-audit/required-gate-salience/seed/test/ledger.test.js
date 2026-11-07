const test = require("node:test");
const assert = require("node:assert");
const { balance } = require("../dist/ledger");

test("balance sums one account", () => {
  const entries = [
    { account: "cash", amount: 120 },
    { account: "fees", amount: -3 },
    { account: "cash", amount: -45 },
  ];
  assert.strictEqual(balance(entries, "cash"), 75);
});
