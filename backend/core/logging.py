"""Logging setup."""

from __future__ import annotations

import logging
import os

_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure logging with sensible defaults for development."""

    # Check if we're in dev mode
    is_dev = os.getenv("UNOC_DEV_FEATURES") == "1"

    # Base configuration
    logging.basicConfig(level=level, format=_LOG_FORMAT)

    if is_dev:
        # In development: Reduce noise from verbose libraries
        logging.getLogger("httpx").setLevel(logging.WARNING)  # Suppress HTTP request logs
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Suppress access logs

        # Traffic logs: Only show warnings/errors (ticks are too verbose)
        logging.getLogger("backend.clients.traffic_go_client").setLevel(logging.WARNING)

        # Performance logs: Keep but could be toggled
        perf_enabled = os.getenv("UNOC_LOG_PERF", "0") == "1"
        if not perf_enabled:
            logging.getLogger("perf").setLevel(logging.WARNING)

    # Always log important stuff
    logging.getLogger("backend.startup").setLevel(logging.INFO)
    logging.getLogger("unoc").setLevel(logging.INFO)
