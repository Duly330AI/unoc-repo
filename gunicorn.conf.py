# Gunicorn configuration for UNOC
# Run with: gunicorn -c gunicorn.conf.py backend.main:app
# On Windows, use Docker or WSL; gunicorn is recommended for Linux/macOS.

import multiprocessing
import os

# Worker configuration
# Use uvicorn workers for ASGI
worker_class = "uvicorn.workers.UvicornWorker"

# Default workers: (2 * CPU) + 1, overridable via UNOC_WORKERS
_workers_env = os.getenv("UNOC_WORKERS")
if _workers_env and _workers_env.isdigit():
    workers = int(_workers_env)
else:
    workers = (multiprocessing.cpu_count() * 2) + 1

# Bind address
bind = os.getenv("UNOC_BIND", f"0.0.0.0:{os.getenv('UNOC_PORT', '5001')}")

# Timeouts
timeout = int(os.getenv("UNOC_GUNICORN_TIMEOUT", "120"))
keepalive = int(os.getenv("UNOC_GUNICORN_KEEPALIVE", "5"))

# Logging
accesslog = os.getenv("UNOC_GUNICORN_ACCESSLOG", "-")  # '-' -> stdout
errorlog = os.getenv("UNOC_GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("UNOC_GUNICORN_LOGLEVEL", "info")

# Graceful reload in dev (SIGHUP) – do not enable auto-reload here; use uvicorn --reload for dev
reload = False

# Max requests per worker to mitigate leaks (optional)
max_requests = int(os.getenv("UNOC_GUNICORN_MAX_REQUESTS", "0")) or 0
max_requests_jitter = int(os.getenv("UNOC_GUNICORN_MAX_REQUESTS_JITTER", "0")) or 0
