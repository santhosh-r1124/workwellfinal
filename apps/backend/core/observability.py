"""Structured logging and Prometheus metrics (Phase 19).

Metrics are implemented directly rather than via prometheus_client so the
MVP keeps its dependency surface small; the exposition format is simple
enough that a hand-rolled registry is honest here. Swap in prometheus_client
if/when histograms with exemplars or multiprocess mode are needed.

Nothing here records employee identifiers or feature values - operational
telemetry about the app must not become a side channel around the consent
system.
"""

import json
import logging
import sys
import threading
from collections import defaultdict

LATENCY_BUCKETS_SECONDS = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]


class _Registry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple], float] = defaultdict(float)
        self._histograms: dict[tuple[str, tuple], list[float]] = defaultdict(list)

    def increment(self, name: str, labels: dict | None = None, value: float = 1.0) -> None:
        key = (name, tuple(sorted((labels or {}).items())))
        with self._lock:
            self._counters[key] += value

    def observe(self, name: str, seconds: float, labels: dict | None = None) -> None:
        key = (name, tuple(sorted((labels or {}).items())))
        with self._lock:
            self._histograms[key].append(seconds)

    def snapshot(self) -> tuple[dict, dict]:
        with self._lock:
            return dict(self._counters), {k: list(v) for k, v in self._histograms.items()}

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()


REGISTRY = _Registry()


def _format_labels(labels: tuple) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{key}="{value}"' for key, value in labels)
    return "{" + inner + "}"


def render_prometheus() -> str:
    counters, histograms = REGISTRY.snapshot()
    lines: list[str] = []

    for (name, labels), value in sorted(counters.items()):
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name}{_format_labels(labels)} {value}")

    for (name, labels), observations in sorted(histograms.items()):
        lines.append(f"# TYPE {name} histogram")
        label_pairs = list(labels)
        cumulative = 0
        for bucket in LATENCY_BUCKETS_SECONDS:
            cumulative = sum(1 for o in observations if o <= bucket)
            bucket_labels = tuple(label_pairs + [("le", str(bucket))])
            lines.append(f"{name}_bucket{_format_labels(bucket_labels)} {cumulative}")
        inf_labels = tuple(label_pairs + [("le", "+Inf")])
        lines.append(f"{name}_bucket{_format_labels(inf_labels)} {len(observations)}")
        lines.append(f"{name}_sum{_format_labels(labels)} {round(sum(observations), 6)}")
        lines.append(f"{name}_count{_format_labels(labels)} {len(observations)}")

    return "\n".join(lines) + "\n"


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def record_llm_call(provider: str, duration_seconds: float, failed: bool = False) -> None:
    REGISTRY.increment("workwell_llm_calls_total", {"provider": provider})
    REGISTRY.observe("workwell_llm_call_duration_seconds", duration_seconds, {"provider": provider})
    if failed:
        REGISTRY.increment("workwell_llm_call_failures_total", {"provider": provider})


def record_pattern_state(state: str) -> None:
    REGISTRY.increment("workwell_pattern_states_total", {"state": state})


def record_intervention(intervention_type: str) -> None:
    REGISTRY.increment("workwell_interventions_total", {"type": intervention_type})


def record_safety_event(severity: str) -> None:
    REGISTRY.increment("workwell_safety_events_total", {"severity": severity})
