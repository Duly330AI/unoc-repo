import os


def _cfg_bool(env: str, default: bool) -> bool:
    v = os.getenv(env)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _cfg_float(env: str, default: float) -> float:
    try:
        return float(os.getenv(env, str(default)))
    except Exception:
        return default


def _cfg_int(env: str, default: int) -> int:
    try:
        return int(os.getenv(env, str(default)))
    except Exception:
        return default
