# NSosyal backend. Run from backend/.
#
# Everyday flow:
#   make frontend    build the Vue UI into web/dist (embedded in the binary)
#   make mock        start the mock Python service on :8001 (second terminal)
#   make run         start the server on :8080 (UI + /api)
#
# Demo laptop:
#   make build       one executable: bin/nsosyal-server(.exe)

TEST_DATABASE_URL ?= postgres://nsosyal:nsosyal_dev@127.0.0.1:5432/nsosyal_test?sslmode=disable
BIN := bin/nsosyal-server$(if $(filter Windows_NT,$(OS)),.exe,)

.PHONY: run build frontend mock ai ai-setup test test-integration vet fmt \
        migrate-up migrate-down migrate-reset migrate-status db-up db-down \
        run-loadtest loadtest

## run: start the server (reads config.yaml and .env)
run:
	go run ./cmd/server

## build: frontend + a single server binary in bin/
build: frontend
	go build -trimpath -o $(BIN) ./cmd/server

## frontend: build the UI into web/dist and check it references no external host
frontend:
	npm --prefix ../frontend run build:backend

## mock: the stand-in Python service (30ms per batch + 5ms per text)
mock:
	go run ./cmd/mockinfer

## ai-setup: install the real inference service into the project venv (../.venv)
ai-setup:
	cd ../AI && ../.venv/Scripts/python.exe -m pip install -r serving/requirements.txt -r modules/m1_lexicon/requirements.txt -r modules/m3_encoder/requirements.txt

## ai: run the real inference service by hand (the server also starts it itself)
ai:
	cd ../AI && ../.venv/Scripts/python.exe -m uvicorn serving.app:create_app --factory --host 127.0.0.1 --port 8001 --no-access-log

## test: unit tests (no database needed; Postgres tests are skipped)
test:
	go test ./...
	npm --prefix ../frontend test

## test-integration: all tests, including Postgres (drops tables in the TEST database)
test-integration: export NSOSYAL_TEST_DATABASE_URL = $(TEST_DATABASE_URL)
test-integration:
	go test -count=1 ./...

vet:
	go vet ./...

fmt:
	gofmt -l -w cmd internal web

## migrate-*: schema changes on the database in config.yaml / .env
migrate-up:
	go run ./cmd/migrate up

migrate-down:
	go run ./cmd/migrate down

migrate-reset:
	go run ./cmd/migrate reset

migrate-status:
	go run ./cmd/migrate status

## db-up / db-down: optional Postgres in Docker on port 5433 (a local install on 5432 works too)
db-up:
	docker compose up -d postgres

db-down:
	docker compose down

## run-loadtest: the server with rate limits raised, because k6 sends every
## virtual user from ONE IP (on the LAN each phone has its own)
run-loadtest: export NSOSYAL_RATE_LIMIT_ANALYZE_PER_SECOND = 100000
run-loadtest: export NSOSYAL_RATE_LIMIT_ANALYZE_BURST = 100000
run-loadtest: export NSOSYAL_RATE_LIMIT_READ_PER_SECOND = 100000
run-loadtest: export NSOSYAL_RATE_LIMIT_READ_BURST = 100000
run-loadtest: export NSOSYAL_LOG_LEVEL = warn
run-loadtest:
	go run ./cmd/server

## loadtest: 150 concurrent users (double the real audience) against :8080
loadtest:
	k6 run loadtest/k6-150users.js
