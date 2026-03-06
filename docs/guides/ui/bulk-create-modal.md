# Bulk device creation modal (Frontend)

## Overview

- Trigger: Right-click a device type in the palette opens a modal to create many devices at once.
- Inputs: count (>=1, max limit), optional POP parent for OLT/AON_SWITCH when POPs exist.
- Placement: Automatic positions via generator to minimize overlap; persisted via /api/layout/positions.
- UX: Progress toast, error aggregation, Undo removes all created items in this batch.

## Accessibility and Keyboard

- Focus trap within the modal; Tab cycles within dialog controls.
- ESC closes the modal without changes.
- Enter activates the primary action (Create) from anywhere inside the modal.
- Count input receives autofocus on open.

## Contract notes

- Aligns with Architecture §9 (UI Modality & Creation Flows): bulk creation is a modal action with validation and reversible outcome (Undo).
- WebSocket updates: subsequent deviceCreated events may arrive if the backend emits; UI is resilient to out-of-order.

## Developer tips

- Primary button is marked with data-primary for accessibility binding.
- Adjust max limit from the component state if larger test topologies are needed.
