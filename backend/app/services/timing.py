from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from collections.abc import Iterator


logger = logging.getLogger(__name__)


@contextmanager
def timed(stage_name: str, timings: dict[str, float] | None = None) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - started
        if timings is not None:
            timings[stage_name] = timings.get(stage_name, 0.0) + elapsed
        logger.info("[POST-ANALYSIS] stage=%s seconds=%.3f", stage_name, elapsed)
