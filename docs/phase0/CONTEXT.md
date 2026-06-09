# operagent Phase 0 — CONTEXT (시방서)

> 결정 이력·제약·정책 변경 기록. 세션 재개 시 PLAN·CHECKLIST와 함께 먼저 읽는다.

---

## 1. 프로젝트 한 줄

operagent = alert을 받아 사람 대신 진단하는 webhook 리시버형 LLM 운영 에이전트. **Phase 0은 그 무대(장애 재현 환경)를 까는 단계, LLM 0줄.**

---

## 2. 결정 이력

| 일자 | 결정 | 근거 |
|------|------|------|
| 2026-06-09 | 신규 별개 레포. origin `github.com/pear-c/operagent.git`, pear-c 계정 | OPSWATCH·feed-it과 무관한 독립 프로젝트 |
| 2026-06-09 | **flat 레이아웃 채택** (`demo-service/`·`webhook-sink/`·`prometheus/`·`alertmanager/`·`loki/`·`alloy/`·`grafana/`·`load-gen/`). 초안의 `go/`+`deploy/` 래퍼 폐기 | 사용자 상세 스펙(2026-06-09) 명시 트리. overview/conventions의 go//deploy/ 경로 표기와 다름 — policy-keywords file_globs는 flat로 동기 갱신 완료 |
| 2026-06-09 | Go 서비스 2개 **모듈 분리** + demo-service는 **단일 package main**(internal/ 안 씀) | 의도적으로 작게(가드레일). client_golang만 의존 |
| 2026-06-09 | webhook-sink = Go 서비스(표준 라이브러리만), Phase 1에 Python 에이전트로 교체 | 스펙대로 |
| 2026-06-09 | MVP = docker-compose 로컬 시뮬 | 비용 0·재현성·장애 임의 재현. 실 클라우드는 Phase 3 |
| 2026-06-09 | 언어 분할: Go(demo-service·계측·고장) / Python(에이전트) | 인프라 생태계 = Go, LLM 생태계 = Python |
| 2026-06-09 | 로그 수집기 = Grafana Alloy | promtail 2026-03-02 EOL |
| 2026-06-09 | Phase 1 오케스트레이션 = 단순 도구 루프, LangGraph는 Phase 3~4 | 멀티에이전트 나중 원칙 (tama Week 3 전례) |
| 2026-06-09 | noti 1순위 = Slack | Block Kit·승인 버튼 생태계 성숙 |

---

## 3. 제약 (불변)

- **LLM에게 탐지 금지** — 탐지는 Prometheus rule + Alertmanager
- **write 액션 Phase 3 전까지 0개** — Phase 0엔 chaos만 (이건 데모 장치지 에이전트 도구 아님)
- **Phase 경계 침범 금지** — Phase 0에서 `agent/` 로직 작성 금지
- **메트릭 3종·alert 3종은 계약** — 변경 시 demo-service/rule/(Phase1)에이전트도구/grafana 동기

## 4. 정책 변경

(없음 — Phase 0 시작 시점)

---

## 5. 환경

- Windows 11 + Docker Desktop
- Go (demo-service), 기성품 컨테이너(prometheus/loki/alloy/grafana/alertmanager)
- 메트릭 이름·alert 임계값은 policy-keywords "메트릭·alert 계약" 카테고리로 보호

---

## 6. 미해결·확인 필요

해결됨:
- [x] Go 모듈 경로 → `github.com/pear-c/operagent/demo-service` · `.../webhook-sink` (2개 분리)
- [x] 더미 webhook 리시버 → Go 서비스 `webhook-sink` (`POST /alert` payload 정렬 로깅)
- [x] Alloy config → `discovery.docker` + `discovery.relabel`(service 라벨) + `loki.source.docker` + `loki.write`

런타임에서 확인 필요:
- [ ] **메모리 임계값 실측** — 현재 `HighHeapMemory > 157286400`(150MB), `/chaos/memory` 기본 200MB 주입. demo-service baseline heap이 임계 근처면 조정 (README 트러블슈팅)
- [ ] Alloy docker.sock 마운트가 Windows Docker Desktop에서 동작하는지 (conventions §7.7 / README 트러블슈팅) — 안 되면 file source fallback
- [ ] `sleep 0.1`(load-gen)이 curlimages/curl busybox에서 분수초 지원하는지 (alpine busybox는 지원)

## 6.1 빌드 막힘 디버깅 (2026-06-09) — 교훈

증상: `go mod tidy`가 `client_golang found but does not contain package promhttp`로 실패. 동시에 초기엔 `proxy.golang.org` i/o timeout도 발생.

**두 가지가 겹쳐 진단을 흐림**:
1. **방화벽** — 사내 방화벽이 `proxy.golang.org`를 막아 초기 timeout (사용자가 해제).
2. **진짜 근본 원인 = import 경로 오타** — `metrics.go`에서 `github.com/prometheus/client_golang/promhttp`로 적음. 실제 경로는 `.../client_golang/prometheus/promhttp`. go가 잘못된 경로의 패키지를 못 찾아 다른 버전(v1.23.2)을 계속 뒤지며 "does not contain package" 출력. **이건 네트워크/캐시 문제처럼 보이지만 코드 버그였음.**

해결 (커밋 0821794):
- import 경로 수정 → 방화벽 해제 후 **기본 프록시로 정상 빌드** (`tidy/vendor/vet/build` 전부 0)
- 사용자 선택대로 **vendoring**: `go mod vendor`(735 files) + go.sum 커밋, Dockerfile `-mod=vendor`로 전환 → 빌드 시 네트워크 0 (폐쇄망 친화, operagent IDC 지향과 정합)
- 로컬 검증 완료: 내 코드 4파일 gofmt clean(vendor/ 서드파티 제외), `go vet`·`go build -mod=vendor` PASS

교훈: **"does not contain package X" = 대개 import 경로 오타** (네트워크 아님). 모듈 캐시·프록시 의심 전에 import 경로부터 확인.

## 7. 이미지 태그 (재현성)
prom/prometheus v2.55.1 · prom/alertmanager v0.27.0 · grafana/loki 3.2.1 · grafana/alloy v1.5.1 · grafana/grafana 11.3.1 · curlimages/curl 8.11.0 · golang 1.23-alpine · distroless/static-debian12:nonroot. 변경 시 호환성 확인.
