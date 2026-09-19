// Package respond writes every API response, so success and error bodies
// have one consistent shape:
//
//	{"error": {"code": "queue_full", "message": "...", "retry_after_ms": 2000}}
package respond

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"strconv"
)

// Error codes the frontend can rely on.
const (
	CodeBadRequest       = "bad_request"
	CodeInvalidText      = "invalid_text"
	CodeInvalidNickname  = "invalid_nickname"
	CodeUnknownSession   = "unknown_session"
	CodeBodyTooLarge     = "body_too_large"
	CodeNotFound         = "not_found"
	CodeMethodNotAllowed = "method_not_allowed"
	CodeRateLimited      = "rate_limited"
	CodeQueueFull        = "queue_full"
	CodeModelLoading     = "model_loading"
	CodeModelUnavailable = "model_unavailable"
	CodeModelError       = "model_error"
	CodeTimeout          = "timeout"
	CodeShuttingDown     = "shutting_down"
	CodeDatabase         = "database_unavailable"
	CodeInternal         = "internal_error"
)

type ErrorBody struct {
	Error ErrorDetail `json:"error"`
}

type ErrorDetail struct {
	Code         string `json:"code"`
	Message      string `json:"message"`
	RetryAfterMS int    `json:"retry_after_ms,omitempty"`
}

func JSON(w http.ResponseWriter, status int, v any) {
	body, err := json.Marshal(v)
	if err != nil {
		slog.Error("encode response", "error", err)
		status = http.StatusInternalServerError
		body = []byte(`{"error":{"code":"internal_error","message":"response could not be encoded"}}`)
	}
	h := w.Header()
	h.Set("Content-Type", "application/json; charset=utf-8")
	h.Set("Cache-Control", "no-store")
	h.Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	_, _ = w.Write(body)
}

// Error writes the error shape. retryAfterMS > 0 also sets Retry-After.
func Error(w http.ResponseWriter, status int, code, message string, retryAfterMS int) {
	if retryAfterMS > 0 {
		seconds := (retryAfterMS + 999) / 1000
		w.Header().Set("Retry-After", strconv.Itoa(seconds))
	}
	JSON(w, status, ErrorBody{Error: ErrorDetail{Code: code, Message: message, RetryAfterMS: retryAfterMS}})
}
