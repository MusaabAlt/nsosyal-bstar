package config

import (
	"bufio"
	"bytes"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"strings"
)

// EnvFileName is read from the same folder as config.yaml. It holds local
// secrets such as NSOSYAL_DATABASE_URL and is never committed.
const EnvFileName = ".env"

// readDotEnv parses a .env file. A missing file is not an error and returns
// an empty map. Supported syntax, one entry per line:
//
//	# comment
//	KEY=value
//	export KEY=value
//	KEY="value with spaces"   or   KEY='value'
//
// Values are taken literally: no variable expansion, no escape sequences, so
// a password containing $ or \ is read exactly as written.
func readDotEnv(path string) (map[string]string, error) {
	data, err := os.ReadFile(path)
	if errors.Is(err, fs.ErrNotExist) {
		return map[string]string{}, nil
	}
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}
	return parseDotEnv(data, path)
}

func parseDotEnv(data []byte, name string) (map[string]string, error) {
	values := map[string]string{}
	data = bytes.TrimPrefix(data, []byte("\xef\xbb\xbf")) // BOM written by some Windows editors

	sc := bufio.NewScanner(bytes.NewReader(data))
	for lineNo := 1; sc.Scan(); lineNo++ {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		line = strings.TrimPrefix(line, "export ")

		key, value, ok := strings.Cut(line, "=")
		key = strings.TrimSpace(key)
		// Errors name the line and key but never the value: it may be a password.
		if !ok || key == "" || strings.ContainsAny(key, " \t") {
			return nil, fmt.Errorf("%s line %d: expected KEY=value", name, lineNo)
		}
		value = strings.TrimSpace(value)
		if n := len(value); n >= 2 && (value[0] == '"' || value[0] == '\'') {
			if value[n-1] != value[0] {
				return nil, fmt.Errorf("%s line %d: %s has an unclosed quote", name, lineNo, key)
			}
			value = value[1 : n-1]
		}
		values[key] = value
	}
	if err := sc.Err(); err != nil {
		return nil, fmt.Errorf("read %s: %w", name, err)
	}
	return values, nil
}
