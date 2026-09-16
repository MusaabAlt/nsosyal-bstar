// Package httpapi assembles the HTTP server: API routes, the embedded
// frontend, and the middleware chain.
package httpapi

import (
	"log/slog"
	"net/http"
	"time"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/http/handlers"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/http/middleware"
)

type RouterConfig struct {
	RequestTimeout time.Duration
	CORSOrigins    []string
	Analyze        *middleware.Limiter
	Read           *middleware.Limiter
	Log            *slog.Logger
	// OnRequest receives every finished /api request (request metrics).
	OnRequest func(middleware.RequestInfo)
}

// NewRouter serves /api/* from the API and everything else from static.
//
// Order, outermost first: recover (catches panics anywhere below, including
// logging), logging, CORS, rate limit, request deadline.
func NewRouter(api *handlers.API, static http.Handler, cfg RouterConfig) http.Handler {
	mux := http.NewServeMux()
	api.Register(mux)
	mux.Handle("/", static)

	return middleware.Chain(mux,
		middleware.Recover(cfg.Log),
		middleware.Logging(cfg.Log, cfg.OnRequest),
		middleware.CORS(cfg.CORSOrigins),
		middleware.RateLimit(cfg.Analyze, cfg.Read),
		middleware.Timeout(cfg.RequestTimeout),
	)
}
