package handlers

import "crypto/sha256"

func sha256Sum(text string) []byte {
	sum := sha256.Sum256([]byte(text))
	return sum[:]
}
