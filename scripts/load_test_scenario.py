"""Realistic load scenario to emulate user behavior and measure end-to-end.

Features:
- Optionally seeds topology from problems/debug.json via public HTTP API
  (devices, interfaces via hardware catalog auto-provision, links).
- Assigns tariffs to ONT and AON_CPE (by technology), provisions devices
  in a sensible order (core -> edge -> access).
- Runs a mixed read workload (ports summary, metrics snapshot, device/link lists,
  PON ont-list) for a given duration with concurrency.
- Parses Prometheus text metrics to estimate p95 for status_recompute and
  per-phase traffic_tick histograms using bucket interpolation.
- Prints a compact summary and optionally writes JSON to logs/scenario_summary.json.

Usage (PowerShell):
  # Backend should be running (see VS Code task: backend: run)
  ${env:PYTHONUTF8}=1; .\.venv\Scripts\python.exe scripts/load_test_scenario.py \
    --duration 45 --concurrency 8 --seed-from-debug

Notes:
- This script uses only the public API (http://localhost:5001/api/... by default).
- It does NOT drop/reset the DB by default to avoid clobbering a running server.
  Pass --reset-db to shell out to scripts/reset_dev_db.py before seeding (use with care).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass
class EndpointStat:
    count: int = 0
    durations_ms: list[float] | None = None

    def add(self, ms: float) -> None:
        if self.durations_ms is None:
            self.durations_ms = []
        self.durations_ms.append(ms)
        self.count += 1

    def pct(self, q: float) -> float | None:
        if not self.durations_ms:
            return None
        arr = sorted(self.durations_ms)
        if not arr:
            return None
        idx = max(0, min(len(arr) - 1, int(round(q * (len(arr) - 1)))))
        return arr[idx]


def _now_ms() -> float:
    return time.perf_counter() * 1000.0


def wait_healthy(base_url: str, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    url = f"{base_url}/api/health"
    last_err = None
    with httpx.Client(timeout=3.0) as client:
        while time.time() < deadline:
            try:
                r = client.get(url)
                if r.status_code == 200:
                    return
                last_err = f"HTTP {r.status_code}"
            except Exception as e:  # pragma: no cover - best-effort
                last_err = str(e)
            time.sleep(0.4)
    raise RuntimeError(f"health check failed: {last_err}")


def _call(client: httpx.Client, method: str, path: str, **kwargs: Any) -> httpx.Response:
    fn = getattr(client, method.lower())
    return fn(path, **kwargs)


def ensure_catalog_seeded(base_url: str) -> None:
    # Touch hardware catalog (it auto-seeds defaults if empty)
    with httpx.Client(base_url=base_url, timeout=10.0) as c:
        _ = _call(c, "get", "/api/catalog/hardware")
        # Ensure default tariffs exist; if none, create minimal set
        r = _call(c, "get", "/api/tariffs")
        if r.status_code == 200 and r.json():
            return
        defaults = [
            {"name": "Basic 100/20", "max_up_mbps": 20, "max_down_mbps": 100, "technology": "GPON"},
            {
                "name": "Pro 1000/300",
                "max_up_mbps": 300,
                "max_down_mbps": 1000,
                "technology": "GPON",
            },
            {"name": "AON 300/300", "max_up_mbps": 300, "max_down_mbps": 300, "technology": "AON"},
            {
                "name": "AON 1000/1000",
                "max_up_mbps": 1000,
                "max_down_mbps": 1000,
                "technology": "AON",
            },
        ]
        for d in defaults:
            _call(c, "post", "/api/tariffs", json=d)


def _load_debug_topology(debug_path: Path) -> dict:
    with debug_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _device_exists(c: httpx.Client, device_id: str) -> bool:
    r = _call(c, "get", f"/api/devices/{device_id}")
    return r.status_code == 200


def seed_from_debug(base_url: str, debug_path: Path) -> dict[str, Any]:
    data = _load_debug_topology(debug_path)
    with httpx.Client(base_url=base_url, timeout=15.0) as c:
        # Create devices (let backend auto-assign hardware and auto-provision interfaces)
        for d in data.get("devices", []):
            payload = {
                "id": d["id"],
                "name": d.get("name", d["id"]),
                "type": d["type"],
                "status": d.get("status", "UP"),
                "parent_container_id": d.get("parent_container_id"),
                # properties/hardware omitted -> AUTO_ASSIGN_DEFAULT_HARDWARE kicks in
            }
            if _device_exists(c, payload["id"]):
                continue
            r = _call(c, "post", "/api/devices", json=payload)
            if r.status_code not in (200, 201):
                raise RuntimeError(
                    f"create_device({payload['id']}) failed: {r.status_code} {r.text}"
                )

        # Create links (use interface ids from debug.json; most are *-if0/ponX/etc.)
        for link in data.get("links", []):
            link_id = link["id"]
            r = _call(c, "get", f"/api/links/{link_id}")
            if r.status_code == 200:
                continue
            payload = {
                "id": link_id,
                "a_interface_id": link["a_interface_id"],
                "b_interface_id": link["b_interface_id"],
                "kind": link.get("kind", "FIBER"),
                "status": link.get("status", "UP"),
            }
            # Optional optical params
            if link.get("length_km") is not None:
                payload["length_km"] = link["length_km"]
            if link.get("physical_medium_id") is not None:
                payload["physical_medium_id"] = link["physical_medium_id"]
            r = _call(c, "post", "/api/links", json=payload)
            if r.status_code not in (200, 201):
                # Try to recover if interfaces not yet present due to async seeding (rare)
                raise RuntimeError(f"create_link({link_id}) failed: {r.status_code} {r.text}")

        # Assign tariffs: GPON for ONT, AON for AON_CPE
        tariffs = {t["name"]: t for t in _call(c, "get", "/api/tariffs").json()}
        ont_tariff = tariffs.get("Pro 1000/300") or tariffs.get("Basic 100/20")
        aon_tariff = tariffs.get("AON 1000/1000") or tariffs.get("AON 300/300")
        for d in data.get("devices", []):
            if d["type"] in {"ONT", "AON_CPE"}:
                r_dev = _call(c, "get", f"/api/devices/{d['id']}")
                if r_dev.status_code != 200:
                    continue
                cur = r_dev.json()
                if cur.get("tariff_id"):
                    continue
                tid = None
                if d["type"] == "ONT" and ont_tariff:
                    tid = ont_tariff["id"]
                if d["type"] == "AON_CPE" and aon_tariff:
                    tid = aon_tariff["id"]
                if tid is not None:
                    _call(c, "put", f"/api/devices/{d['id']}", json={"tariff_id": tid})

        # Provision devices in a stable order
        def _prov(dev_id: str) -> None:
            _ = _call(c, "post", f"/api/devices/{dev_id}/provision", json={})

        order = [
            # backbone first, then core/edge, then OLT, AON switch, leaves
            "backbone_gateway",
            "core_router",
            "edge_router",
            "olt",
            "aon_switch",
            "ont",
            "aon_cpe",
        ]
        # Use what's actually present
        have = {d["id"] for d in data.get("devices", [])}
        for dev_id in [d for d in order if d in have]:
            _prov(dev_id)

    return {"created": True}


# ---- Load generation ----


def _workload_ops(
    base_url: str, olt_id: str
) -> list[tuple[str, Callable[[httpx.Client], httpx.Response]]]:
    # Each op returns an httpx.Response
    ops: list[tuple[str, Callable[[httpx.Client], httpx.Response]]] = []
    ops.append(("ports_summary", lambda c: _call(c, "get", f"/api/ports/summary/{olt_id}")))
    ops.append(("metrics_snapshot", lambda c: _call(c, "get", "/api/metrics/snapshot")))
    ops.append(("devices_list", lambda c: _call(c, "get", "/api/devices?include_interfaces=1")))
    ops.append(("links_list", lambda c: _call(c, "get", "/api/links")))
    ops.append(("ont_list", lambda c: _call(c, "get", f"/api/ports/ont-list/{olt_id}")))
    return ops


def run_load(base_url: str, duration_s: float, concurrency: int, olt_id: str) -> dict[str, Any]:
    ops = _workload_ops(base_url, olt_id)
    weights = {
        "ports_summary": 0.45,
        "metrics_snapshot": 0.2,
        "devices_list": 0.2,
        "links_list": 0.1,
        "ont_list": 0.05,
    }
    # Expand into a weighted list for simple choice without RNG (deterministic cycle)
    seq: list[tuple[str, Callable[[httpx.Client], httpx.Response]]] = []
    for name, fn in ops:
        repeat = int(round(weights.get(name, 0.1) * 20)) or 1
        seq.extend([(name, fn)] * repeat)
    # Deterministic rotation
    next_idx = 0
    stats: dict[str, EndpointStat] = defaultdict(EndpointStat)

    stop_at = time.time() + duration_s

    def worker() -> None:
        nonlocal next_idx
        with httpx.Client(base_url=base_url, timeout=10.0) as c:
            while time.time() < stop_at:
                name, fn = seq[next_idx % len(seq)]
                next_idx += 1
                t0 = _now_ms()
                try:
                    r = fn(c)
                    # Consume body to avoid connection reuse stalls
                    _ = r.text
                    dur = _now_ms() - t0
                    stats[name].add(dur)
                except Exception:
                    # Count as 0ms to keep stats aligned but highlight in output later if needed
                    stats[name].add(0.0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, int(concurrency))) as ex:
        futures = [ex.submit(worker) for _ in range(max(1, int(concurrency)))]
        for f in futures:
            try:
                f.result()
            except Exception:
                pass

    # Fetch Prometheus metrics at end
    prom: dict[str, Any] | None = None
    try:
        with httpx.Client(base_url=base_url, timeout=10.0) as c:
            r = _call(c, "get", "/api/metrics/prometheus")
            if r.status_code == 200:
                prom = parse_prom_text(r.text)
    except Exception:
        prom = None

    # Build summary
    summary: dict[str, Any] = {"http": {}}
    for name, st in stats.items():
        summary["http"][name] = {
            "count": st.count,
            "p50_ms": st.pct(0.50),
            "p90_ms": st.pct(0.90),
            "p95_ms": st.pct(0.95),
            "p99_ms": st.pct(0.99),
        }

    if prom:
        # status_recompute and traffic_tick per-phase p95s
        hist_sr = prom.get("status_recompute_phase_seconds", {})
        sr_p95 = histogram_p95(hist_sr)
        summary["status_recompute_p95_s"] = sr_p95
        hist_tick = prom.get("traffic_tick_phase_seconds", {})
        tick_p95 = histogram_p95(hist_tick)
        summary["traffic_tick_phases_p95_s"] = tick_p95

    return summary


# ---- Prometheus text parsing helpers ----


def parse_prom_text(text: str) -> dict[str, Any]:
    # Returns { metric_name: { label_key: { 'buckets': [(le, count), ...], 'count': N, 'sum': S } } }
    out: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Example: traffic_tick_phase_seconds_bucket{phase="generate",le="0.05"} 12
        try:
            name_and_labels, value_str = line.split(" ", 1)
        except ValueError:
            continue
        if not (name_and_labels.endswith("}") or "{" not in name_and_labels):
            # Simplify parsing: require {..}
            continue
        name, labels_str = name_and_labels.split("{", 1)
        labels_str = labels_str.rstrip("}")
        labels: dict[str, str] = {}
        if labels_str:
            for part in labels_str.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    labels[k.strip()] = v.strip().strip('"')
        try:
            value = float(value_str.strip())
        except Exception:
            continue
        # Group by metric name and a key from labels (phase or default)
        key = labels.get("phase") or labels.get("scope") or "_"
        m: dict[str, Any] = out.setdefault(name.replace("_bucket", ""), {})
        e = m.setdefault(key, {"buckets": [], "sum": 0.0, "count": 0.0})
        if name.endswith("_bucket"):
            le = labels.get("le")
            if le is not None:
                try:
                    e["buckets"].append((float(le), value))
                except Exception:
                    # '+Inf' bucket
                    if le == "+Inf":
                        e["buckets"].append((float("inf"), value))
        elif name.endswith("_sum"):
            e["sum"] = value
        elif name.endswith("_count"):
            e["count"] = value
    return out


def histogram_p95(hist_map: dict[str, Any]) -> dict[str, float]:
    res: dict[str, float] = {}
    for key, e in hist_map.items():
        buckets = sorted(e.get("buckets", []), key=lambda x: x[0])
        total = e.get("count", 0.0) or 0.0
        if not buckets or total <= 0:
            continue
        target = 0.95 * total
        p95 = None
        for le, cnt in buckets:
            if cnt >= target:
                p95 = le
                break
        if p95 is None:
            p95 = buckets[-1][0]
        res[key] = float(p95)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:5001", help="Backend base URL")
    ap.add_argument("--duration", type=int, default=45, help="Load duration in seconds")
    ap.add_argument("--concurrency", type=int, default=8, help="Concurrent worker threads")
    ap.add_argument("--seed-from-debug", action="store_true", help="Seed using problems/debug.json")
    ap.add_argument(
        "--reset-db", action="store_true", help="Reset DB before seeding (file DB only)"
    )
    ap.add_argument("--summary-json", default=str(Path("logs") / "scenario_summary.json"))
    args = ap.parse_args()

    base_url = args.base_url.rstrip("/")

    # Optional DB reset (shells out to avoid coupling to app state)
    if args.reset_db:
        script = Path(__file__).resolve().parents[0] / "reset_dev_db.py"
        # Use catalog-only first to ensure hardware/tariffs exist, then seed topology via API
        rc = os.system(f'"{sys.executable}" "{script}" --force --catalog-only')
        if rc != 0:
            print("Warning: reset_dev_db.py returned non-zero", file=sys.stderr)

    wait_healthy(base_url)
    ensure_catalog_seeded(base_url)

    olt_id = "olt"
    if args.seed_from_debug:
        dbg = Path(__file__).resolve().parents[1] / "problems" / "debug.json"
        if dbg.exists():
            seed_from_debug(base_url, dbg)
            # Heuristic: prefer the first OLT device from debug.json
            try:
                with dbg.open("r", encoding="utf-8") as f:
                    dd = json.load(f)
                for d in dd.get("devices", []):
                    if d.get("type") == "OLT":
                        olt_id = d.get("id", olt_id)
                        break
            except Exception:
                pass

    # Warm caches with an initial ports summary call (best-effort)
    try:
        with httpx.Client(base_url=base_url, timeout=10.0) as c:
            _ = _call(c, "get", f"/api/ports/summary/{olt_id}")
    except Exception:
        pass

    print(
        f"Running load: duration={args.duration}s, concurrency={args.concurrency}, olt_id={olt_id}"
    )
    started = time.time()
    summary = run_load(base_url, args.duration, args.concurrency, olt_id)
    elapsed = time.time() - started
    summary["total_duration_s"] = round(elapsed, 3)

    # Pretty-print summary
    def _fmt_ms(v: Any) -> Any:
        return None if v is None else round(float(v), 2)

    print("\nHTTP p95 latencies (ms):")
    for name, vals in summary.get("http", {}).items():
        print(
            f"- {name}: p50={_fmt_ms(vals['p50_ms'])} p90={_fmt_ms(vals['p90_ms'])} p95={_fmt_ms(vals['p95_ms'])} p99={_fmt_ms(vals['p99_ms'])} (n={vals['count']})"
        )

    if summary.get("status_recompute_p95_s"):
        print("\nstatus_recompute p95 (s):")
        for k, v in summary["status_recompute_p95_s"].items():
            print(f"- {k}: {round(v, 4)}")
    if summary.get("traffic_tick_phases_p95_s"):
        print("\ntraffic_tick phases p95 (s):")
        for k, v in summary["traffic_tick_phases_p95_s"].items():
            print(f"- {k}: {round(v, 4)}")

    # Write JSON
    out_path = Path(args.summary_json)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\nSummary written to {out_path}")
    except Exception as e:  # pragma: no cover - filesystem issues
        print(f"Failed to write summary JSON: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
