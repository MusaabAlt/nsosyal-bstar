// Package web serves the built Vue frontend from inside the Go binary, so the
// demo laptop runs one executable on one port with no files beside it.
//
// The frontend is built straight into web/dist (npm run build:backend in
// frontend/, or make frontend). go:embed cannot reach ../frontend/dist,
// which is why the build writes here.
package web

import (
	"embed"
	"io/fs"
	"net/http"
	"path"
	"strings"
)

//go:embed all:dist
var dist embed.FS

// Handler serves static files and falls back to index.html for client-side
// routes (/kategoriler). Paths under /api/ never reach it.
func Handler() http.Handler {
	files, err := fs.Sub(dist, "dist")
	if err != nil {
		panic(err) // the embed pattern guarantees the directory exists
	}
	index, indexErr := fs.ReadFile(files, "index.html")
	fileServer := http.FileServer(http.FS(files))

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet && r.Method != http.MethodHead {
			w.Header().Set("Allow", "GET, HEAD")
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		h := w.Header()
		h.Set("X-Content-Type-Options", "nosniff")

		name := strings.TrimPrefix(path.Clean(r.URL.Path), "/")
		if name != "" && name != "index.html" {
			if info, err := fs.Stat(files, name); err == nil && !info.IsDir() {
				if strings.HasPrefix(name, "assets/") {
					// Vite puts a content hash in every asset name: safe to cache forever.
					h.Set("Cache-Control", "public, max-age=31536000, immutable")
				}
				fileServer.ServeHTTP(w, r)
				return
			}
			if path.Ext(name) != "" {
				// A missing file (not a client route): answer 404, not the app.
				http.NotFound(w, r)
				return
			}
		}

		if indexErr != nil {
			h.Set("Content-Type", "text/plain; charset=utf-8")
			w.WriteHeader(http.StatusServiceUnavailable)
			_, _ = w.Write([]byte("Frontend not built. Run: make frontend (or npm run build:backend in frontend/), then rebuild the server.\n"))
			return
		}
		// index.html must never be cached, so a rebuilt UI is picked up at once.
		h.Set("Cache-Control", "no-cache")
		h.Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write(index)
	})
}
