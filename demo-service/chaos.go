package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"math/rand/v2"
	"net/http"
	"runtime"
	"sync"
	"time"
)

// Chaos는 주입된 고장 상태를 mutex로 보호해 보관한다.
// 고장 미들웨어가 요청마다 이 상태를 읽어 지연/에러를 주입한다.
// 설계 의도: reset + state 덕분에 데모를 스크립트로 반복 재현할 수 있다.
type Chaos struct {
	mu         sync.RWMutex
	latencyMs  int
	latencyPct int
	errorRate  float64
	memHold    [][]byte           // 잡아둔 메모리(set 방식, 누적 아님)
	cpuCancel  context.CancelFunc // CPU burn 중단용
	cpuWorkers int
}

func NewChaos() *Chaos { return &Chaos{} }

// middleware는 비즈니스 라우트에만 적용한다(/chaos/*·/metrics 제외 — 복구 가능성 보장).
func (c *Chaos) middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		c.mu.RLock()
		ms, pct, rate := c.latencyMs, c.latencyPct, c.errorRate
		c.mu.RUnlock()

		if rate > 0 && rand.Float64() < rate {
			slog.Error("고장 주입: 에러", "route", r.URL.Path, "status", 500, "reason", "chaos_errors")
			http.Error(w, `{"error":"chaos injected error"}`, http.StatusInternalServerError)
			return
		}
		if ms > 0 && pct > 0 && rand.IntN(100) < pct {
			time.Sleep(time.Duration(ms) * time.Millisecond)
		}
		next.ServeHTTP(w, r)
	})
}

func (c *Chaos) setLatency(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Ms  int `json:"ms"`
		Pct int `json:"pct"`
	}
	if !decode(w, r, &body) {
		return
	}
	c.mu.Lock()
	c.latencyMs, c.latencyPct = body.Ms, body.Pct
	c.mu.Unlock()
	slog.Warn("고장 설정: 지연", "ms", body.Ms, "pct", body.Pct)
	c.getState(w, r)
}

func (c *Chaos) setErrors(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Rate float64 `json:"rate"`
	}
	if !decode(w, r, &body) {
		return
	}
	c.mu.Lock()
	c.errorRate = body.Rate
	c.mu.Unlock()
	slog.Warn("고장 설정: 에러율", "rate", body.Rate)
	c.getState(w, r)
}

func (c *Chaos) setMemory(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Mb int `json:"mb"`
	}
	if !decode(w, r, &body) {
		return
	}
	// set 방식(누적 아님): 기존 보유분을 새 블록으로 교체한다.
	block := make([][]byte, body.Mb)
	for i := range block {
		b := make([]byte, 1<<20) // 1 MiB
		for j := 0; j < len(b); j += 4096 {
			b[j] = 1 // 페이지를 실제로 커밋시켜 heap_inuse_bytes를 키운다
		}
		block[i] = b
	}
	c.mu.Lock()
	c.memHold = block
	c.mu.Unlock()
	slog.Warn("고장 설정: 메모리", "mb", body.Mb)
	c.getState(w, r)
}

func (c *Chaos) setCPU(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Workers int `json:"workers"`
		Seconds int `json:"seconds"`
	}
	if !decode(w, r, &body) {
		return
	}
	c.startCPU(body.Workers, body.Seconds)
	slog.Warn("고장 설정: CPU", "workers", body.Workers, "seconds", body.Seconds)
	c.getState(w, r)
}

// startCPU는 workers개 goroutine으로 CPU를 태운다. seconds=0이면 reset 전까지 지속.
func (c *Chaos) startCPU(workers, seconds int) {
	c.mu.Lock()
	if c.cpuCancel != nil {
		c.cpuCancel() // 이전 burn 중단
	}
	ctx, cancel := context.WithCancel(context.Background())
	c.cpuCancel = cancel
	c.cpuWorkers = workers
	c.mu.Unlock()

	for i := 0; i < workers; i++ {
		go func() {
			for {
				select {
				case <-ctx.Done():
					return
				default:
				}
			}
		}()
	}
	if seconds > 0 {
		go func() {
			timer := time.NewTimer(time.Duration(seconds) * time.Second)
			defer timer.Stop()
			select {
			case <-ctx.Done():
			case <-timer.C:
				c.stopCPU()
			}
		}()
	}
}

func (c *Chaos) stopCPU() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.cpuCancel != nil {
		c.cpuCancel()
		c.cpuCancel = nil
	}
	c.cpuWorkers = 0
}

func (c *Chaos) reset(w http.ResponseWriter, r *http.Request) {
	c.stopCPU()
	c.mu.Lock()
	c.latencyMs, c.latencyPct, c.errorRate = 0, 0, 0
	c.memHold = nil
	c.mu.Unlock()
	runtime.GC() // 잡아둔 메모리를 즉시 반환시켜 heap_inuse_bytes를 떨어뜨린다
	slog.Warn("고장 전체 해제(reset)")
	c.getState(w, r)
}

func (c *Chaos) getState(w http.ResponseWriter, _ *http.Request) {
	c.mu.RLock()
	view := struct {
		LatencyMs  int     `json:"latency_ms"`
		LatencyPct int     `json:"latency_pct"`
		ErrorRate  float64 `json:"error_rate"`
		MemoryMB   int     `json:"memory_mb"`
		CPUWorkers int     `json:"cpu_workers"`
	}{c.latencyMs, c.latencyPct, c.errorRate, len(c.memHold), c.cpuWorkers}
	c.mu.RUnlock()

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(view)
}

// decode는 JSON body를 파싱하고 실패 시 400을 쓴다.
func decode(w http.ResponseWriter, r *http.Request, v any) bool {
	if err := json.NewDecoder(r.Body).Decode(v); err != nil {
		http.Error(w, `{"error":"invalid json body"}`, http.StatusBadRequest)
		return false
	}
	return true
}
