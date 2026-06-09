// demo-service — Phase 0의 유일한 "감시 대상".
// 세 표면으로 구성된다: 비즈니스(handlers.go) / 계측(metrics.go) / 고장 주입(chaos.go).
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	// 구조화 로그(JSON) → stdout → Alloy → Loki
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo})))

	m := NewMetrics()
	chaos := NewChaos()
	store := NewOrderStore()

	mux := http.NewServeMux()

	// /metrics: 계측·고장 미적용 — 고장 중에도 스크레이프되어야 alert이 뜬다.
	mux.Handle("GET /metrics", m.Handler())

	// 비즈니스 표면: 계측 미들웨어 → 고장 미들웨어 → 핸들러
	mux.Handle("GET /healthz", m.instrument("/healthz", http.HandlerFunc(healthz)))
	mux.Handle("GET /api/orders", m.instrument("/api/orders", chaos.middleware(http.HandlerFunc(store.list))))
	mux.Handle("POST /api/orders", m.instrument("/api/orders", chaos.middleware(http.HandlerFunc(store.create))))

	// 고장 제어 표면: 주입 미적용 — reset/state는 고장 중에도 항상 동작해야 복구된다.
	mux.Handle("POST /chaos/latency", http.HandlerFunc(chaos.setLatency))
	mux.Handle("POST /chaos/errors", http.HandlerFunc(chaos.setErrors))
	mux.Handle("POST /chaos/memory", http.HandlerFunc(chaos.setMemory))
	mux.Handle("POST /chaos/cpu", http.HandlerFunc(chaos.setCPU))
	mux.Handle("GET /chaos/state", http.HandlerFunc(chaos.getState))
	mux.Handle("POST /chaos/reset", http.HandlerFunc(chaos.reset))

	srv := &http.Server{
		Addr:              ":8080",
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}

	go func() {
		slog.Info("demo-service 시작", "addr", srv.Addr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			slog.Error("서버 비정상 종료", "err", err)
			os.Exit(1)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = srv.Shutdown(ctx)
	slog.Info("demo-service 정상 종료")
}
