# operagent Phase 0 — 데모 편의 명령
# Windows에서는 git-bash/WSL에서 `make` 사용, 또는 각 타깃의 curl 명령을 직접 실행.

DEMO ?= http://localhost:8080

.PHONY: up down logs logs-sink chaos-latency chaos-errors chaos-memory chaos-cpu reset state

up: ## 전체 스택 빌드 + 기동
	docker compose up --build -d

down: ## 전체 종료 + 볼륨 정리
	docker compose down -v

logs: ## demo-service 로그
	docker compose logs -f demo-service

logs-sink: ## webhook-sink 로그 (alert payload 확인)
	docker compose logs -f webhook-sink

chaos-latency: ## 지연 장애 주입 (800ms, 100%)
	curl -s -XPOST $(DEMO)/chaos/latency -H 'Content-Type: application/json' -d '{"ms":800,"pct":100}'; echo

chaos-errors: ## 에러율 장애 주입 (50%)
	curl -s -XPOST $(DEMO)/chaos/errors -H 'Content-Type: application/json' -d '{"rate":0.5}'; echo

chaos-memory: ## 메모리 장애 주입 (200MB)
	curl -s -XPOST $(DEMO)/chaos/memory -H 'Content-Type: application/json' -d '{"mb":200}'; echo

chaos-cpu: ## CPU 장애 주입 (4 workers, reset까지 지속)
	curl -s -XPOST $(DEMO)/chaos/cpu -H 'Content-Type: application/json' -d '{"workers":4,"seconds":0}'; echo

reset: ## 모든 고장 해제
	curl -s -XPOST $(DEMO)/chaos/reset; echo

state: ## 현재 고장 상태 조회
	curl -s $(DEMO)/chaos/state; echo
