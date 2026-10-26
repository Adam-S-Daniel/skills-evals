package main

import (
	"fmt"
	"os"

	"example.com/inventory/internal/stock"
)

func main() {
	ledger := stock.NewLedger()
	ledger.Add("widget", 3)
	ledger.Add("gadget", 1)
	if err := ledger.Remove("gadget", 1); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(ledger.Count("widget"))
}
