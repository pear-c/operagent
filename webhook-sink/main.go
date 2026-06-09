// webhook-sink — Alertmanager webhook을 받아 보기 좋게 stdout에 로깅하는 임시 리시버.
//
// ★ Phase 1에서 이 자리가 Python 에이전트(진단 두뇌)로 교체된다.
//   여기엔 어떤 진단·대응 로직도 없다. 받은 payload를 그대로 찍는 "로거"일 뿐이다.
//   외부 라이브러리 의존 없음(표준 라이브러리만).
package main

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"os"
	"time"
)

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})
	mux.HandleFunc("POST /alert", handleAlert)

	srv := &http.Server{Addr: ":9000", Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	slog.Info("webhook-sink 시작 (Phase 1에서 Python 에이전트로 교체될 자리)", "addr", ":9000")
	if err := srv.ListenAndServe(); err != nil {
		slog.Error("webhook-sink 종료", "err", err)
		os.Exit(1)
	}
}

func handleAlert(w http.ResponseWriter, r *http.Request) {
	raw, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "read error", http.StatusBadRequest)
		return
	}

	// Alertmanager payload를 들여쓰기해 사람이 읽기 좋게 출력한다.
	var pretty any
	if json.Unmarshal(raw, &pretty) == nil {
		out, _ := json.MarshalIndent(pretty, "", "  ")
		slog.Info("=== ALERT 수신 ===")
		_, _ = os.Stdout.Write(out)
		_, _ = os.Stdout.Write([]byte("\n"))
	} else {
		slog.Info("ALERT 수신(비 JSON)", "body", string(raw))
	}

	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"received"}`))
}
