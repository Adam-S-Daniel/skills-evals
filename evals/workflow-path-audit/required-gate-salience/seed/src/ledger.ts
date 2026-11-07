export interface Entry {
  account: string;
  amount: number;
}

export function balance(entries: Entry[], account: string): number {
  return entries
    .filter((e) => e.account === account)
    .reduce((sum, e) => sum + e.amount, 0);
}
