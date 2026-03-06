"""Compute p95 from Prometheus histogram buckets exposed by the API.

Usage examples:
  # Graph building phase (status recompute)
  .venv/Scripts/python.exe scripts/metrics_p95.py \
    --url http://localhost:5001/api/metrics/prometheus \
    --metric status_recompute_phase_seconds \
    --labels phase=graph_building

  # Data fetching phase (status recompute)
  .venv/Scripts/python.exe scripts/metrics_p95.py \
    --url http://localhost:5001/api/metrics/prometheus \
    --metric status_recompute_phase_seconds \
    --labels phase=data_fetching

  # Generate phase (traffic engine)
  .venv/Scripts/python.exe scripts/metrics_p95.py \
    --url http://localhost:5001/api/metrics/prometheus \
    --metric traffic_tick_phase_seconds \
    --labels phase=generate
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request

Line = tuple[str, dict[str, str], float]


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read().decode("utf-8", errors="replace")


_METRIC_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)\{(?P<labels>[^}]*)\}\s+(?P<value>[0-9.eE+-]+)"
)


def parse_prom_text(text: str) -> list[Line]:
    out: list[Line] = []
    for raw in text.splitlines():
        if not raw or raw.startswith("#"):
            continue
        m = _METRIC_RE.match(raw)
        if not m:
            continue
        name = m.group("name")
        labels_raw = m.group("labels").strip()
        value = float(m.group("value"))
        labels: dict[str, str] = {}
        if labels_raw:
            # split on commas not inside quotes
            for part in re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", labels_raw):
                if not part:
                    continue
                k, _, v = part.partition("=")
                if not _:
                    continue
                labels[k.strip()] = v.strip().strip('"')
        out.append((name, labels, value))
    return out


def labels_match(have: dict[str, str], want: dict[str, str]) -> bool:
    for k, v in want.items():
        if have.get(k) != v:
            return False
    return True


def compute_p95_from_histogram(
    lines: list[Line], metric: str, want_labels: dict[str, str]
) -> float | None:
    # Collect buckets: metric_bucket{... le="x"} count
    buckets: list[tuple[float, float]] = []
    count_total = None
    for name, labels, value in lines:
        if name == f"{metric}_bucket" and labels_match(labels, want_labels) and "le" in labels:
            try:
                le = float(labels["le"]) if labels["le"] != "+Inf" else float("inf")
            except ValueError:
                continue
            buckets.append((le, value))
        elif name == f"{metric}_count" and labels_match(labels, want_labels):
            count_total = value
    if not buckets or count_total is None or count_total <= 0:
        return None
    buckets.sort(key=lambda x: x[0])
    target = 0.95 * count_total
    for le, cnt in buckets:
        if cnt >= target:
            return le
    return buckets[-1][0]


def parse_labels_arg(arg: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    if not arg:
        return labels
    for item in arg.split(","):
        k, _, v = item.partition("=")
        if _:
            labels[k.strip()] = v.strip()
    return labels


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:5001/api/metrics/prometheus")
    ap.add_argument(
        "--metric", required=True, help="base metric name (without _bucket/_count suffix)"
    )
    ap.add_argument(
        "--labels", default="", help="comma separated labels filter, e.g., phase=generate"
    )
    args = ap.parse_args()

    text = fetch_text(args.url)
    lines = parse_prom_text(text)
    want = parse_labels_arg(args.labels)
    p95 = compute_p95_from_histogram(lines, args.metric, want)
    if p95 is None:
        print("p95=NA (no data)")
        sys.exit(2)
    print(f"p95={p95}")


if __name__ == "__main__":
    main()
