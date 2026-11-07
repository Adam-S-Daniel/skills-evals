import { balance } from "./ledger";

const entries = [
  { account: "cash", amount: 120 },
  { account: "cash", amount: -45 },
];
console.log(`cash: ${balance(entries, "cash")}`);
