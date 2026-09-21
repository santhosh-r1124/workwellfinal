from fastapi import APIRouter, Response

from apps.backend.core.observability import render_prometheus

router = APIRouter(tags=["observability"])


@router.get("/metrics")
def metrics() -> Response:
    """Prometheus scrape endpoint. Exposes only operational aggregates -
    request counts/latency, LLM call volume, and counts of pattern states,
    interventions and safety events by category. No employee identifiers and
    no feature values, so scraping this never becomes a way around consent."""
    return Response(content=render_prometheus(), media_type="text/plain; version=0.0.4")
