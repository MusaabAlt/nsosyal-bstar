# syntax=docker/dockerfile:1
# Stage 1 — Vue SPA. Emits into backend/web/dist for go:embed.
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci
COPY frontend/ ./frontend/
COPY backend/ ./backend/
# build:backend also runs check-offline.mjs, asserting no external hosts.
RUN cd frontend && npm run build:backend

# Stage 2 — Go binary with the SPA embedded. go.mod requires 1.27.0.
FROM golang:1.27-alpine AS builder
WORKDIR /src
COPY backend/go.mod backend/go.sum ./backend/
RUN cd backend && go mod download
COPY backend/ ./backend/
COPY --from=frontend /src/backend/web/dist ./backend/web/dist
RUN cd backend && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/server ./cmd/server

# Stage 3 — runtime
FROM alpine:3.20
RUN apk add --no-cache ca-certificates tzdata curl && adduser -D -u 10001 app
COPY --from=builder /out/server /usr/local/bin/server
COPY backend/config.yaml /etc/nsosyal/config.yaml
USER app
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/server", "-config", "/etc/nsosyal/config.yaml"]
