"""EventStore migration/backfill health diagnostics."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from backend.models import EventStoreRecord
from backend.services.event_store import append_event, event_store_snapshot
from backend.services.event_store_runtime import event_store_enforcement_enabled
from backend.services.simulation_event_engine import (
    SIMULATION_EVENT_TYPES,
    SimulationEvent,
    build_simulation_event_log,
    replay_simulation_events,
)

BACKFILL_SOURCE = "BACKFILL_DB_SNAPSHOT"


def ensure_backfilled_event_store(session: Session) -> int:
    existing = session.exec(
        select(EventStoreRecord.id).where(EventStoreRecord.source == BACKFILL_SOURCE)
    ).first()
    if existing is not None:
        return 0
    count = 0
    for event in build_simulation_event_log(session):
        append_event(session, event.type, event.payload, source=BACKFILL_SOURCE)
        count += 1
    return count


def _records_to_simulation_events(records: list[EventStoreRecord]) -> list[SimulationEvent]:
    events: list[SimulationEvent] = []
    sequence = 0
    for record in records:
        if record.source != BACKFILL_SOURCE:
            continue
        if record.event_type not in SIMULATION_EVENT_TYPES:
            continue
        events.append(
            SimulationEvent(
                sequence=sequence,
                type=record.event_type,
                payload=dict(record.payload or {}),
                source=record.source,
            )
        )
        sequence += 1
    return events


# API mutation surfaces that append write-path events and run inside
# projection_write_context (enforcement-ready).
COVERED_WRITE_SURFACES = [
    "POST /api/devices (create_device_impl)",
    "PUT /api/devices/{id} (update_device_impl)",
    "DELETE /api/devices/{id} (delete_device_impl)",
    "PATCH /api/devices/{id}/override (set_device_override_impl)",
    "POST /api/devices/{id}/provision (provision_device_endpoint)",
    "POST /api/links (create_link_impl)",
    "PUT /api/links/{id} (update_link_impl)",
    "DELETE /api/links/{id} (delete_link_impl, via job worker)",
    "PATCH /api/links/{id}/override (set_link_override_impl, via job worker)",
    "POST /api/links/batch (batch_create_links)",
    "POST /api/devices/{id}/interfaces (create_interface)",
    "POST /api/interfaces/{id}/addresses (create_interface_address)",
    "DELETE /api/interfaces/{id}/addresses/{aid} (delete_interface_address)",
]

# Internal writers deliberately allowed to bypass event append (derived state /
# bootstrap), wrapped in projection_write_context so hard enforcement can be
# enabled without breaking them.
INTERNAL_WRITE_EXCLUSIONS = [
    "optical_service.recompute_optical_paths_for_affected_onts (derived signal fields)",
    "status_service.bulk_update_device_statuses (derived status propagation fallback)",
    "seed_service.ensure_backbone_gateway (bootstrap seed)",
]

# Reasons full ("fully_enforced") event sourcing cannot be claimed yet.
FULL_ENFORCEMENT_BLOCKERS = [
    "Go services (batch-service, status-service, traffic-engine) write the database "
    "directly over their own connections; the Python session guard cannot observe or "
    "block those writes",
    "DB writes remain the operational source of truth (dual-write); projections are "
    "rebuilt from the event log for diagnostics, not serving reads",
    "internal derived-state/bootstrap writers listed in internal_write_exclusions do "
    "not append domain events",
]


def build_event_store_health(session: Session) -> dict[str, Any]:
    backfilled = ensure_backfilled_event_store(session)
    snapshot = event_store_snapshot(session)
    records = session.exec(select(EventStoreRecord).order_by(EventStoreRecord.sequence)).all()
    replayable_events = _records_to_simulation_events(records)
    projections = replay_simulation_events(replayable_events)
    backfill_count = sum(1 for record in records if record.source == BACKFILL_SOURCE)
    projection_lag = len(replayable_events) - int(projections.get("event_count") or 0)
    legacy_runtime_events = [record for record in records if record.source == "RUNTIME_EVENT_BUS"]
    write_path_events = [record for record in records if record.source == "WRITE_PATH"]

    enforcement_enabled = event_store_enforcement_enabled()
    # Honest migration state:
    # - projection_lag: replay is behind, investigate first
    # - partially_enforced: hard bypass guard active for Python write paths; Go
    #   direct DB writes and documented internal writers remain outside it
    # - instrumented_dual_write: all audited API mutation surfaces append events
    #   and are enforcement-ready, but DB dual-write stays operational and the
    #   guard is not enabled
    if projection_lag != 0:
        consistency = "projection_lag"
    elif enforcement_enabled:
        consistency = "partially_enforced"
    else:
        consistency = "instrumented_dual_write"

    return {
        "total_events": snapshot["total_events"],
        "last_event_timestamp": snapshot["last_event_timestamp"],
        "last_sequence": snapshot["last_sequence"],
        "backfill_migration": {
            "source": BACKFILL_SOURCE,
            "events_added_this_call": backfilled,
            "backfilled_events_total": backfill_count,
        },
        "projection_lag": projection_lag,
        "consistency_status": consistency,
        "migration": {
            "state": consistency,
            "covered_write_surfaces": COVERED_WRITE_SURFACES,
            "internal_write_exclusions": INTERNAL_WRITE_EXCLUSIONS,
            "full_enforcement_blockers": FULL_ENFORCEMENT_BLOCKERS,
            "enforcement_ready": True,
            "note": (
                "Set UNOC_EVENTSTORE_ENFORCE=1 to activate the hard bypass guard for "
                "the covered Python write paths; state then reports partially_enforced. "
                "fully_enforced is not claimable until the listed blockers are resolved."
            ),
        },
        "event_store_enforcement": {
            "enabled": enforcement_enabled,
            "bypass_error": "EVENT_STORE_BYPASS",
            "guarded_models": ["Device", "Interface", "Link", "ProvisioningRecord"],
        },
        "projection_summary": {
            "event_count": projections.get("event_count"),
            "effective_subscriber_count": projections.get("analytics_projection", {}).get(
                "effective_subscriber_count"
            ),
            "olt_subscribers": projections.get("analytics_projection", {}).get("olt_subscribers", {}),
            "aon_subscribers": projections.get("analytics_projection", {}).get("aon_subscribers", {}),
        },
        "legacy_runtime_events_recorded": len(legacy_runtime_events),
        "write_path_events_recorded": len(write_path_events),
        "hard_rule_status": (
            "enforced" if enforcement_enabled else "available_but_not_enabled"
        ),
    }


__all__ = ["BACKFILL_SOURCE", "build_event_store_health", "ensure_backfilled_event_store"]