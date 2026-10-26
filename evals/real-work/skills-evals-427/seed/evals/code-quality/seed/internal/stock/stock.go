// Package stock keeps per-item quantities for the inventory report.
package stock

import "fmt"

// Ledger maps an item name to the quantity on hand.
type Ledger struct {
	items map[string]int
}

// NewLedger returns an empty ledger.
func NewLedger() *Ledger {
	return &Ledger{items: map[string]int{}}
}

// Add records n more of item.
func (l *Ledger) Add(item string, n int) {
	l.items[item] += n
}

// Remove takes n of item off the ledger, refusing to go below zero.
func (l *Ledger) Remove(item string, n int) error {
	if l.items[item] < n {
		return fmt.Errorf("stock: only %d %s on hand, cannot remove %d", l.items[item], item, n)
	}
	l.items[item] -= n
	return nil
}

// Count reports the quantity of item on hand.
func (l *Ledger) Count(item string) int {
	return l.items[item]
}
