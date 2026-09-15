package cache

import (
	"fmt"
	"sync"
	"testing"
	"time"
)

func TestKeyNeverMergesSpellings(t *testing.T) {
	// The obfuscated and the plain spelling must never share an answer.
	if Key("s4l4k", "h") == Key("salak", "h") {
		t.Fatal("different spellings share a key")
	}
	if Key("Salak", "h") == Key("salak", "h") {
		t.Fatal("case variants share a key")
	}
	if Key("salak ", "h") == Key("salak", "h") {
		t.Fatal("trailing space ignored")
	}
	if Key("salak", "model-1") == Key("salak", "model-2") {
		t.Fatal("a new model version must not reuse old answers")
	}
}

func TestGetPut(t *testing.T) {
	c := New[string](2, time.Minute)
	c.Put("a", "1")
	if v, ok := c.Get("a"); !ok || v != "1" {
		t.Fatalf("get a = %q %v", v, ok)
	}
	if _, ok := c.Get("missing"); ok {
		t.Fatal("hit on missing key")
	}
	c.Put("a", "2")
	if v, _ := c.Get("a"); v != "2" {
		t.Fatalf("update lost: %q", v)
	}
	if s := c.Stats(); s.Hits != 2 || s.Misses != 1 || s.Entries != 1 {
		t.Fatalf("stats = %+v", s)
	}
}

func TestEvictsLeastRecentlyUsed(t *testing.T) {
	c := New[int](2, time.Minute)
	c.Put("a", 1)
	c.Put("b", 2)
	c.Get("a") // a is now more recent than b
	c.Put("c", 3)
	if _, ok := c.Get("b"); ok {
		t.Fatal("b should have been evicted")
	}
	for _, k := range []string{"a", "c"} {
		if _, ok := c.Get(k); !ok {
			t.Fatalf("%s evicted", k)
		}
	}
}

func TestExpires(t *testing.T) {
	now := time.Unix(0, 0)
	c := New[int](10, time.Second)
	c.now = func() time.Time { return now }
	c.Put("a", 1)
	now = now.Add(999 * time.Millisecond)
	if _, ok := c.Get("a"); !ok {
		t.Fatal("expired too early")
	}
	now = now.Add(2 * time.Millisecond)
	if _, ok := c.Get("a"); ok {
		t.Fatal("served after TTL")
	}
	if c.Stats().Entries != 0 {
		t.Fatal("expired entry not removed")
	}
}

func TestMemoryIsBoundedUnderConcurrency(t *testing.T) {
	c := New[int](100, time.Minute)
	var wg sync.WaitGroup
	for g := range 16 {
		wg.Go(func() {
			for i := range 1000 {
				key := fmt.Sprintf("%d-%d", g, i)
				c.Put(key, i)
				c.Get(key)
			}
		})
	}
	wg.Wait()
	if n := c.Stats().Entries; n > 100 {
		t.Fatalf("%d entries, capacity 100", n)
	}
}
