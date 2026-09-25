import logging

from fastapi import APIRouter, Response

from apps.backend.core.observability import record_queue_depth, render_prometheus

logger = logging.getLogger("workwell.metrics")

router = APIRouter(tags=["observability"])


def _refresh_queue_gauges() -> None:
    """Queue depth lives in Redis, so any process can read it. Publishing it
    from here means an operator sees a backed-up queue on the scrape target
    they already have, including in the case that matters most - the worker
    being down and therefore not exporting anything itself."""
    from apps.worker.queue import get_queue

    try:
        queue = get_queue()
        record_queue_depth(queue.depth(), queue.in_flight())
    except Exception as exc:
        logger.warning("could not read queue depth: %s", type(exc).__name__)


@router.get("/metrics")
def metrics() -> Response:
    """Prometheus scrape endpoint. Exposes only operational aggregates -
    request counts/latency, LLM call volume, queue depth, and counts of
    pattern states, interventions and safety events by category. No employee
    identifiers and no feature values, so scraping this never becomes a way
    around consent."""
    _refresh_queue_gauges()
    return Response(content=render_prometheus(), media_type="text/plain; version=0.0.4")
