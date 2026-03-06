📘 TASK‑800: Feature – Implement Hierarchical Container Nodes with Snap Logic
Priority: High Milestone: M9 – Foundational Network Emulation

🎯 Goal
Ersetzen der primitiven gestrichelten Linien zur Darstellung von Parent‑Child‑Beziehungen durch ein skalierbares, intuitives Container‑Nesting‑Modell. Geräte werden innerhalb visuell unterscheidbarer Container Nodes (z. B. POP, CORE_SITE) gruppiert, die ihre logische und physische Hierarchie widerspiegeln. Die neue Version integriert eine Snap‑Logik für Drag‑and‑Drop‑Platzierung in freie Slots.

Blueprint‑Prinzipien:

Zentraler Container (z. B. POP) als große, klar abgegrenzte Fläche

Geräte (OLT, AON_SWITCH, Edge Router etc.) werden innerhalb dieser Fläche angeordnet

Keine externen gestrichelten Linien mehr – stattdessen echte visuelle Verschachtelung

Snap‑Mechanismus für präzises Einrasten in definierte Slots

🧭 Scope

1. Backend – Models & Validation
   Neuer Container‑Typ:

CORE_SITE in DeviceType Enum aufnehmen

Als passive_container markieren (analog zu POP)

Strikte Containment‑Regeln (validate_parent_child):

OLT, AON_SWITCH, Edge Router → müssen in einem POP liegen

Backbone Gateway, Core Router → müssen in einem CORE_SITE liegen

❌ Ungültige Kombinationen (z. B. OLT in CORE_SITE) → 400 Bad Request

Port‑ und Interface‑Bezug:

Container‑Slots sind logische Aufnahmepunkte für Geräte, nicht Ersatz für Ports

Ports, Interfaces, VLAN, IPAM bleiben am Gerät selbst verankert

2. Frontend – Visual Refactoring
   Container Cockpits:

POPCockpit.vue refactoren

CoreSiteCockpit.vue neu erstellen

Darstellung: große, umrandete Rechtecke mit klar unterscheidbaren Styles (Farbe/Icon je Typ)

Nested Rendering (draw.ts):

Geräte mit parent_container_id innerhalb der Container‑Geometrie rendern

Positionierung anhand Container‑Koordinaten + definierter Slot‑Positionen

Remove Dashed Lines:

Alle gestrichelten Linien für Parent‑Child‑Beziehungen entfernen

3. Frontend – Physics & Interaction
   Bounding Force (forceSimulation):

Custom Force, die Child‑Nodes innerhalb der Container‑Bounds hält

Padding berücksichtigen, um Überlappung mit Container‑Rändern zu vermeiden

Smart Drag & Drop mit Snap‑Logik:

Slots im Container mit Koordinaten + erlaubten Gerätetypen definieren

Beim Drag:

Slot‑Highlight bei gültigem Ziel

Ungültige Ziele rot markieren

Beim Drop:

✅ Gültig → Gerät auf Slot‑Koordinaten setzen, parent_container_id setzen, PATCH /api/devices/{id} ausführen

❌ Ungültig → Drop verhindern, Gerät zurücksetzen

⛔ Herausziehen → parent_container_id = null

4. Frontend – Aggregated Metrics
   Device Summary:

Anzahl enthaltener Geräte pro Typ (z. B. „2 OLTs, 1 Edge Router“)

Traffic Summary:

Summe aller total_bps der enthaltenen Geräte (live‑aktualisiert)

5. Device Creation Viewer (Erweiterung)
   Gerätetyp‑Dropdown (nur passende Modelle je Typ)

Pflichtfelder:

Model Name

Port Count

Port Max Speed

Port Type (PON, Ethernet, 10G, …)

Max Subscribers per Port (nur PON)

Default Split Ratio (nur PON)

Interface Template (optional)

Passive/Active Flag

Optionale direkte Slot‑Zuordnung bei Erstellung

6. Verification
   Backend‑Tests:

Containment‑Regeln

Fehlerbehandlung

Schema‑Integrität

Frontend‑Tests:

Drag‑and‑Drop (gültig/ungültig)

Snap‑Verhalten

Container‑Rendering & Metrik‑Anzeige

Manuelle Prüfung:

Geräte sind korrekt im Container verschachtelt

Container‑Grenzen werden eingehalten

Keine gestrichelten Linien mehr

Aggregierte Daten korrekt

📎 Notes
Atomic Diff Principle (max. 3 Files pro Commit)

parent_container_id bleibt Single Source of Truth

Container‑Slots sind organisatorisch, Ports bleiben technisch am Gerät

Snap‑Logik wiederverwendbar für alle Container‑Typen

Ich habe hier bewusst die Snap‑Mechanik und die Slot‑Definition direkt in den Scope integriert, damit Backend‑ und Frontend‑Team eine gemeinsame Sprache haben.
