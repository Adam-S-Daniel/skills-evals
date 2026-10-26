package stock

import "testing"

func TestRemoveRefusesNegativeStock(t *testing.T) {
	l := NewLedger()
	l.Add("widget", 1)
	if err := l.Remove("widget", 2); err == nil {
		t.Fatal("expected an error removing more than is on hand")
	}
	if got := l.Count("widget"); got != 1 {
		t.Fatalf("Count = %d, want 1", got)
	}
}
