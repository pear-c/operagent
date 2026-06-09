# operagent Phase 0 — CHECKLIST (공정표)

> 단계별 진행 상태. 2026-06-09 상세 스펙 기준 flat 레이아웃으로 스캐폴딩 완료.
> 상태: ⬜ 미착수 / 🔵 진행 중 / ✅ 완료 / 🧪 코드·설정 완료, 런타임 검증은 사용자 `docker compose up` 필요

레이아웃은 PLAN 초안의 `go/`+`deploy/` 래퍼 대신 **flat**(`demo-service/`·`webhook-sink/`·`prometheus/`·`alertmanager/`·`loki/`·`alloy/`·`grafana/`·`load-gen/`)으로 확정 (CONTEXT §2).

---

## 작성 완료 (코드·설정)

- [x] **레포 골격** — `.gitignore` / `.gitattributes`(LF 강제) / `docker-compose.yml`(8 컨테이너)
- [x] **demo-service (Go)** — main / handlers / metrics(client_golang 3종 + go_*/process_*) / chaos(mutex State + 미들웨어 주입 + reset/state) / Dockerfile(multi-stage distroless)
- [x] **webhook-sink (Go)** — `POST /alert` payload 정렬 로깅 + Dockerfile. Phase 1 교체 자리 주석 명시
- [x] **load-gen** — curl 루프(healthz 대기 후 GET/POST 혼합 ~10-20rps)
- [x] **prometheus** — prometheus.yml(5s scrape) + rules.yml(HighErrorRate/HighLatencyP95/HighHeapMemory, for:30s)
- [x] **loki + alloy** — 단일바이너리 filesystem loki + config.alloy(docker discovery → service 라벨 → loki.write)
- [x] **grafana** — datasource(uid prometheus/loki) + dashboard provider + ops-overview.json(5패널)
- [x] **alertmanager** — webhook-sink 라우팅(send_resolved)
- [x] **Makefile + README** — up/down/chaos-*/reset/state + 완료기준 6항목 체크리스트
- [x] YAML 7종 + JSON 2종 유효성 검증 통과

## 런타임 검증 — 2026-06-09 E2E 통과 ✅
- [x] `git init` + remote(pear-c) + 첫 커밋 (82df0a8, push됨)
- [x] `docker compose up --build -d` → 8 컨테이너 전부 Up (loki config 수정 69dca7b 후)
- [x] Prometheus 타깃 demo-service `health=up` + `http_requests_total` ~14 req/s (load-gen)
- [x] Loki `service=demo-service` 라벨 유입 확인 (Alloy 동작)
- [x] `chaos/errors` → 50초에 HighErrorRate firing → **webhook-sink가 payload 수신** (5xx 40.82%)
- [x] `chaos/reset` → 60초에 alert 해제 → **webhook-sink가 resolved payload 수신**
- [x] `chaos/latency`(800ms) → HighLatencyP95 firing(70초) → webhook 수신 ✅
- [x] `chaos/memory`(200MB) → heap 210.9MB → HighHeapMemory firing(30초) → webhook 수신 ✅ → reset 후 heap 5.1MB 복귀

---

## VERIFY 게이트 (Phase 0) — 코드/설정 레벨
- [x] 게이트 1 Lint: YAML 7 + JSON 2 유효 / gofmt 두 모듈 통과(내 코드, vendor 제외)
- [x] 게이트 2 Type: `go vet` + `go build` 로컬 PASS (webhook-sink, demo-service `-mod=vendor`)
- [x] 게이트 3 Policy: 메트릭 3종·alert 3종 계약 준수 / chaos reset+state 존재 / promtail 부재(Alloy) 확인
- [x] 게이트 4 Build: `docker compose up --build` 성공, 8/8 Up (2026-06-09)
- [x] 게이트 5 Scope: `agent/` 로직 0줄, LLM·write 0줄 (Phase 경계 준수)

---

## 다음
- Phase 0 런타임 E2E 통과 후 → CONTEXT §6 미해결(메모리 임계값 실측 등) 마감 → Phase 1 (`agent/` Python webhook 에이전트)
