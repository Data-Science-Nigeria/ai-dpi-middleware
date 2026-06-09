"""Prometheus metrics registry and request instrumentation."""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, REGISTRY, CollectorRegistry
import prometheus_client

# ── Counters ──────────────────────────────────────────────────────────────────
requests_total = Counter(
    "dpi_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

llm_requests_total = Counter(
    "dpi_llm_requests_total",
    "LLM API calls",
    ["provider", "model"],
)

llm_errors_total = Counter(
    "dpi_llm_errors_total",
    "LLM API errors",
    ["provider"],
)

# ── Histograms ─────────────────────────────────────────────────────────────────
request_latency = Histogram(
    "dpi_request_latency_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

llm_latency = Histogram(
    "dpi_llm_latency_seconds",
    "LLM call latency",
    ["provider"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

# ── Gauges ────────────────────────────────────────────────────────────────────
active_requests = Gauge(
    "dpi_active_requests",
    "In-flight HTTP requests",
)
