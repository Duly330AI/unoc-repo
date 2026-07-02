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


FULLY_AUTHORITATIVE_ENFORCED = "fully_authoritative_enforced"
PYTHON_AUTHORITATIVE_GO_NOT_GUARDED_NO_GO_WRITES = (
    "authoritative_for_python_guarded_paths_go_not_guarded_but_no_guarded_go_writes"
)
PARTIALLY_ENFORCED_WITH_BLOCKERS = "partially_enforced_with_blockers"
MIGRATION_INCOMPLETE = "migration_incomplete"

GUARDED_ENTITIES = ["Device", "Interface", "Link", "ProvisioningRecord"]

# API mutation surfaces that append EventStore domain events before guarded DB
# writes and run the projection mutation inside projection_write_context.
COVERED_WRITE_PATHS = [
    {
        "path": "POST /api/devices",
        "handler": "devices_helpers_mutation_core.create_device_impl",
        "events": ["DEVICE_CREATED", "PORT_CONNECTED"],
    },
    {
        "path": "PUT /api/devices/{id}",
        "handler": "devices_helpers_mutation_core.update_device_impl",
        "events": ["DEVICE_UPDATED", "PORT_CONNECTED"],
    },
    {
        "path": "DELETE /api/devices/{id}",
        "handler": "devices_helpers_delete.delete_device_impl",
        "events": ["DEVICE_DELETED", "LINK_DELETED"],
    },
    {
        "path": "PATCH /api/devices/{id}/override",
        "handler": "devices_helpers_override.set_device_override_impl",
        "events": ["DEVICE_UPDATED"],
    },
    {
        "path": "POST /api/devices/{id}/provision",
        "handler": "provisioning.provision_device_endpoint",
        "events": ["PROVISIONING_UPDATED"],
    },
    {
        "path": "POST /api/links",
        "handler": "links_helpers_create.create_link_impl",
        "events": ["PORT_CONNECTED", "LINK_CREATED"],
    },
    {
        "path": "PUT /api/links/{id}",
        "handler": "links_helpers_update.update_link_impl",
        "events": ["LINK_UPDATED"],
    },
    {
        "path": "DELETE /api/links/{id}",
        "handler": "links_helpers_delete.delete_link_impl via job worker",
        "events": ["LINK_DELETED"],
    },
    {
        "path": "PATCH /api/links/{id}/override",
        "handler": "links_helpers_override.set_link_override_impl via job worker",
        "events": ["LINK_UPDATED"],
    },
    {
        "path": "POST /api/links/batch",
        "handler": "links_batch.batch_create_links",
        "events": ["LINK_CREATED"],
    },
    {
        "path": "POST /api/devices/{id}/interfaces",
        "handler": "interfaces.create_interface",
        "events": ["PORT_CONNECTED"],
    },
    {
        "path": "POST /api/interfaces/{id}/addresses",
        "handler": "interfaces.create_interface_address",
        "events": ["PROVISIONING_UPDATED"],
    },
    {
        "path": "DELETE /api/interfaces/{id}/addresses/{aid}",
        "handler": "interfaces.delete_interface_address",
        "events": ["PROVISIONING_UPDATED"],
    },
]

# Internal writers deliberately excluded from domain-event append. They are
# derived-state or bootstrap paths, and are wrapped in projection_write_context
# so hard enforcement can stay enabled without treating them as business events.
EXCLUDED_INTERNAL_PATHS = [
    {
        "path": "optical_service.recompute_optical_paths_for_affected_onts",
        "reason": "derived optical signal fields; not a user domain mutation",
    },
    {
        "path": "status_service.bulk_update_device_statuses",
        "reason": "derived status propagation fallback; no new topology/provisioning intent",
    },
    {
        "path": "seed_service.ensure_backbone_gateway",
        "reason": "bootstrap seed path for baseline topology availability",
    },
]

GO_GUARDED_WRITE_STATUS = {
    "status": "no_active_guarded_go_writes",
    "python_guard_observes_go_connections": False,
    "findings": [
        {
            "service": "batch-service",
            "guarded_write": "engine-go/internal/batch/create.go contains INSERT INTO link",
            "active_from_public_api": False,
            "reason": "POST /api/links/batch is served by the Python event-first route and no longer calls the Go batch client",
        },
        {
            "service": "status-service",
            "guarded_write": None,
            "active_from_public_api": False,
            "reason": "runtime status propagation reads topology and keeps bulkUpdateDeviceStatuses as a no-op transaction; guarded UPDATE expectations are test-only leftovers",
        },
        {
            "service": "optical-service",
            "guarded_write": None,
            "active_from_public_api": False,
            "reason": "audited runtime code computes optical paths without writing guarded domain tables",
        },
        {
            "service": "traffic-engine",
            "guarded_write": None,
            "active_from_public_api": False,
            "reason": "audited runtime code is traffic/read-model oriented and does not write guarded domain tables",
        },
        {
            "service": "port-summary-service",
            "guarded_write": None,
            "active_from_public_api": False,
            "reason": "audited runtime code reads device/interface/link state for summaries",
        },
    ],
}

NOT_FULLY_AUTHORITATIVE_REASONS = [
    "Go service database connections are not intercepted by the Python SQLAlchemy guard, even though the audited active Go paths do not write guarded domain tables",
    "documented internal derived-state/bootstrap exclusions do not append domain events",
    "the operational DB write model still serves reads while replay projections remain diagnostic",
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
    go_has_active_guarded_writes = (
        GO_GUARDED_WRITE_STATUS["status"] != "no_active_guarded_go_writes"
    )
    if projection_lag != 0:
        consistency = PARTIALLY_ENFORCED_WITH_BLOCKERS
        remaining_blockers = [f"projection_lag is {projection_lag}; replay is not current"]
    elif not enforcement_enabled:
        consistency = MIGRATION_INCOMPLETE
        remaining_blockers = ["UNOC_EVENTSTORE_ENFORCE is disabled"]
    elif go_has_active_guarded_writes:
        consistency = PARTIALLY_ENFORCED_WITH_BLOCKERS
        remaining_blockers = [
            "at least one active Go service writes guarded domain tables outside the Python guard"
        ]
    else:
        consistency = PYTHON_AUTHORITATIVE_GO_NOT_GUARDED_NO_GO_WRITES
        remaining_blockers = list(NOT_FULLY_AUTHORITATIVE_REASONS)

    return {
        "total_events": snapshot["total_events"],
        "last_event_timestamp": snapshot["last_event_timestamp"],
        "last_sequence": snapshot["last_sequence"],
        "last_event_sequence": snapshot["last_sequence"],
        "enforcement_enabled": enforcement_enabled,
        "guarded_entities": GUARDED_ENTITIES,
        "covered_write_paths": COVERED_WRITE_PATHS,
        "excluded_internal_paths": EXCLUDED_INTERNAL_PATHS,
        "remaining_blockers": remaining_blockers,
        "go_guarded_write_status": GO_GUARDED_WRITE_STATUS,
        "projection_lag": projection_lag,
        "write_path_events_recorded": len(write_path_events),
        "consistency_status": consistency,
        "backfill_migration": {
            "source": BACKFILL_SOURCE,
            "events_added_this_call": backfilled,
            "backfilled_events_total": backfill_count,
        },
        "migration": {
            "state": consistency,
            "covered_write_surfaces": [entry["path"] for entry in COVERED_WRITE_PATHS],
            "covered_write_paths": COVERED_WRITE_PATHS,
            "excluded_internal_paths": EXCLUDED_INTERNAL_PATHS,
            "remaining_blockers": remaining_blockers,
            "not_fully_authoritative_reasons": NOT_FULLY_AUTHORITATIVE_REASONS,
            "enforcement_ready": enforcement_enabled and projection_lag == 0,
            "note": (
                "EventStore is authoritative for covered Python guarded writes when "
                "enforcement is enabled; fully_authoritative_enforced is not claimed."
            ),
        },
        "event_store_enforcement": {
            "enabled": enforcement_enabled,
            "bypass_error": "EVENT_STORE_BYPASS",
            "guarded_models": GUARDED_ENTITIES,
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
        "hard_rule_status": (
            "enforced" if enforcement_enabled else "available_but_not_enabled"
        ),
    }


__all__ = [
    "BACKFILL_SOURCE",
    "build_event_store_health",
    "ensure_backfilled_event_store",
]
