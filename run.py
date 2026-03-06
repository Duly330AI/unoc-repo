"""UNOC backend dev runner (Phase B skeleton).

Launch with: python run.py
Env vars (prefixed UNOC_): see backend.core.config.Settings
"""

from __future__ import annotations

import os

import uvicorn

from backend.core.config import get_settings
from backend.main import app

if __name__ == "__main__":
    settings = get_settings()
    disable_reload = os.getenv("UNOC_DISABLE_RELOAD") or os.getenv("UNOC_FORCE_NO_RELOAD")

    # In dev mode: reduce log noise
    is_dev = os.getenv("UNOC_DEV_FEATURES") == "1"
    log_level = "warning" if is_dev else "info"
    access_log = not is_dev  # Disable access logs in dev mode

    if settings.debug and not disable_reload:
        # When reload=True uvicorn expects an import string not the app object
        uvicorn.run(
            "backend.main:app",
            host="0.0.0.0",
            port=settings.port,
            reload=True,
            log_level=log_level,
            access_log=access_log,
        )
    else:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=settings.port,
            reload=False,
            log_level=log_level,
            access_log=access_log,
        )
