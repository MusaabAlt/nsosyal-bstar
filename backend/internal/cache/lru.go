// Package cache keeps recent analysis results so a repeated text never
// reaches the model twice.
//
// The key is sha256(exact text) plus the model's artifact_hash. The text is
// never normalized for the key: this project exists to tell "s4l4k" from
// "salak", and a normalized key would hand one the other's answer. Including
// artifact_hash means a new model or threshold file never serves old results.
package cache

import (
	"container/list"
	"crypto/sha256"
	"encoding/hex"
	"sync"
	"time"
)

// Key builds the cache key for a text under a model version.
func Key(text, artifactHash string) string {
	sum := sha256.Sum256([]byte(text))
	return artifactHash + ":" + hex.EncodeToString(sum[:])
}

type entry[V any] struct {
	key     string
	value   V
	expires time.Time
}

// LRU is a size-bounded, TTL-bounded, concurrency-safe cache. Memory never
// grows past `size` entries.
type LRU[V any] struct {
	size int
	ttl  time.Duration
	now  func() time.Time

	mu    sync.Mutex
	order *list.List // front = most recently used
	items map[string]*list.Element

	hits, misses uint64
}

func New[V any](size int, ttl time.Duration) *LRU[V] {
	if size < 1 {
		size = 1
	}
	return &LRU[V]{size: size, ttl: ttl, now: time.Now, order: list.New(), items: make(map[string]*list.Element, size)}
}

func (c *LRU[V]) Get(key string) (V, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	var zero V
	el, ok := c.items[key]
	if !ok {
		c.misses++
		return zero, false
	}
	e := el.Value.(*entry[V])
	if c.now().After(e.expires) {
		c.order.Remove(el)
		delete(c.items, key)
		c.misses++
		return zero, false
	}
	c.order.MoveToFront(el)
	c.hits++
	return e.value, true
}

func (c *LRU[V]) Put(key string, value V) {
	c.mu.Lock()
	defer c.mu.Unlock()
	expires := c.now().Add(c.ttl)
	if el, ok := c.items[key]; ok {
		e := el.Value.(*entry[V])
		e.value, e.expires = value, expires
		c.order.MoveToFront(el)
		return
	}
	c.items[key] = c.order.PushFront(&entry[V]{key: key, value: value, expires: expires})
	for c.order.Len() > c.size {
		oldest := c.order.Back()
		c.order.Remove(oldest)
		delete(c.items, oldest.Value.(*entry[V]).key)
	}
}

type Stats struct {
	Entries  int    `json:"entries"`
	Capacity int    `json:"capacity"`
	Hits     uint64 `json:"hits"`
	Misses   uint64 `json:"misses"`
}

func (c *LRU[V]) Stats() Stats {
	c.mu.Lock()
	defer c.mu.Unlock()
	return Stats{Entries: c.order.Len(), Capacity: c.size, Hits: c.hits, Misses: c.misses}
}
