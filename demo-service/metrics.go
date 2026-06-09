package main

import (
	"net/http"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// Metrics는 HTTP 계측 컬렉터를 보유한다.
// 기본 레지스트리에 등록해 go_*/process_* 컬렉터(메모리·goroutine 등)도
// 함께 노출되게 한다 — 메모리 고장은 go_memstats_heap_inuse_bytes에,
// goroutine 폭증은 go_goroutines에 자동으로 드러난다.
type Metrics struct {
	requests *prometheus.CounterVec
	duration *prometheus.HistogramVec
	inflight prometheus.Gauge
}

func NewMetrics() *Metrics {
	m := &Metrics{
		requests: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "총 HTTP 요청 수",
		}, []string{"method", "route", "status"}),
		duration: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "HTTP 요청 처리 시간(초)",
			Buckets: []float64{.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5},
		}, []string{"route"}),
		inflight: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "http_inflight_requests",
			Help: "처리 중인(in-flight) 요청 수",
		}),
	}
	prometheus.MustRegister(m.requests, m.duration, m.inflight)
	return m
}

// Handler는 기본 레지스트리(우리 메트릭 + go_*/process_*)를 노출한다.
func (m *Metrics) Handler() http.Handler { return promhttp.Handler() }

// instrument는 요청을 감싸 카운터/히스토그램/게이지를 갱신한다.
func (m *Metrics) instrument(route string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		m.inflight.Inc()
		defer m.inflight.Dec()

		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		start := time.Now()
		next.ServeHTTP(rec, r)

		m.duration.WithLabelValues(route).Observe(time.Since(start).Seconds())
		m.requests.WithLabelValues(r.Method, route, strconv.Itoa(rec.status)).Inc()
	})
}

// statusRecorder는 상태 코드를 캡처해 메트릭 라벨에 쓴다(고장 주입된 500 포함).
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}
