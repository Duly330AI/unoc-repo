# Always-On L3 Auto-Provisioning von Router-Uplinks

Stand: 2025-09-24

## Ziel

Nach dem Provisionieren eines Edge- oder Core-Routers soll unmittelbar eine minimale, deterministische L3-Erreichbarkeit zur nächst-höheren Anker-Ebene (Core ↔ Backbone, Edge ↔ Core) bestehen, so dass strikte Status-Logik (`Status.UP` nur bei echter L3-Reachability) nicht manuell geblockt wird. Dadurch entfallen fragile Zwischenzustände (DOWN obwohl physisch/ logisch verbunden) und Tests bleiben deterministisch ohne Feature-Flags.

## Geltungsbereich

Automatisch aktiv für Device-Typen:

- `CORE_ROUTER`
- `EDGE_ROUTER`

Andere Gerätetypen (POP, BACKBONE_GATEWAY, OLT/ONT, AON Switch, etc.) werden nicht direkt konfiguriert; POP/BACKBONE gelten ohnehin als Anker oder containerhaft, OLT/ONT folgen eigener (optischer) Logik.

## Auslöser

Die Routine wird immer am Ende des Provisionierungsvorgangs (`provision_device`) aufgerufen – kein Feature-Flag, kein Opt-In.

## Ablauf (High Level)

1. Sicherstellen, dass die Management-VRF (`mgmt`) existiert – ggf. via `ensure_ipam_defaults` anlegen.
2. Falls das Device noch keine `vrf_id` hat, wird es der `mgmt`-VRF zugewiesen.
3. Alle Interfaces des Geräts erfassen; relevante Links (Edge↔Core oder Core↔Backbone) sammeln.
4. Für jeden beteiligten Link deterministische /31 Punkt-zu-Punkt IP-Adressen ableiten (Hash des Link-IDs → stabiler 172.18.X.Y/31 Block):
   - Link-spezifische Paarung `(base, peer)`; `base` wird dem lexikographisch „niedrigeren“ Device-Ende zugewiesen, `peer` dem anderen Ende – dadurch deterministische Symmetrie.
5. Auf beiden Endpunkten je eine `InterfaceAddress` (falls nicht vorhanden) anlegen.
6. Default-Route hinzufügen:
   - Edge: Default via Core-IP, falls noch kein Default auf Device-Ebene existiert.
   - Core: Default via Backbone-IP, falls noch kein Default existiert.
7. `Neighbor`-Einträge (ARP/Nachbarschaft) erzeugen, sofern noch nicht vorhanden.
8. Idempotenz: Alle Objekte werden nur ergänzt, wenn eindeutig fehlend (Lookup per Interface/Route/Neighbor-Schlüssel).

## Determinismus

- Hash→/31 Ableitung garantiert stabile Wiederholbarkeit bei gleichen Link-IDs (SHA-1 → erste zwei Bytes → 172.18.X.Y, Y wird auf gerade Adresse gemaskt; Peer = Y+1).
- Keine Zufallszahlen, keine Zeitabhängigkeiten.
- Reihenfolge der Verarbeitung ohne Seiteneffekt (INSERT nur bei Nicht-Existenz).

## Sicherheitsgeländer

- Exceptions innerhalb des Auto-Konfigurationsschritts werden abgefangen (Provisioning darf nie fehlschlagen). Fehlerhafte Links können später manuell behoben werden.
- Wenn keine geeignete VRF erzeugt werden kann, wird der Schritt übersprungen (Device bleibt DOWN nach strikter L3-Regel – bewusste, seltene Degradationspfad).

## Status-Integration

Die Statusberechnung (`evaluate_device_status`) für Router verlangt echte L3-Reachability zu einem Backbone / POP Anker. Durch das automatische Setzen von InterfaceAddress, Neighbor und Default-Route erfüllt ein frisch provisionierter Router diese Bedingung (sofern physischer Link existiert) und springt deterministisch auf `UP`. Fällt der Upstream (Override oder physisch) aus, wird Status erneut strikt berechnet (→ `DOWN`).

## Beispiel

Core ↔ Backbone Link-ID: `bbA-coreA`

- Hash generiert 172.18.34.120/31 → Adressen: 172.18.34.120 (Ende A), 172.18.34.121 (Ende B)
- Core erhält (je nach lexikographischer Sortierung der Device-IDs) eine der beiden Adressen.
- Core bekommt Default-Route `0.0.0.0/0` via Backbone-IP.
- Neighbor (MAC generisch / placeholder) wird für die Peer-IP erstellt.

Edge ↔ Core (weiterer Link) analog; Edge erhält Default via Core.

## Idempotenzprüfung

Mehrfaches Provisionieren / Re-Calls (z.B. bei Replays) verändern keine existierenden Einträge. Bereits gesetzte VRF, InterfaceAddresses, Routes oder Neighbors bleiben unverändert.

## Abgrenzungen & Nicht-Ziele

- Kein dynamisches Routing-Protokoll (OSPF/BGP) – rein statische Default + Punkt-zu-Punkt.
- Kein IPv6 (future work).
- Keine automatische Entfernung veralteter Einträge (Garbage Collection) – separate Maintenance-Aufgabe.
- Keine Erzeugung von /30 statt /31 – bewusst kompaktes /31 Schema.

## Auswirkungen auf Tests

- Tests, die früher einen DOWN-Zustand direkt nach Provisionierung erwarteten, wurden angepasst: Router sind jetzt unmittelbar `UP` (sofern Link vorhanden). Downstream Degradation wird über tatsächliche Upstream-Ausfälle verifiziert.

## Mögliche Erweiterungen (Future Work)

- Dynamische Erkennung mehrerer paralleler Uplinks (ECMP Vorbereitung).
- /31 Pool Zentralisierung im IPAM statt Hash-Derivation.
- Validierung gegen Adressüberlappungen (obwohl Hash-Raum groß genug ist).
- Erweiterung für OLT Management-Uplink wenn Multi-Hop-Berechnung nötig wird.

## Troubleshooting

| Symptom                                          | Ursache                                      | Aktion                                                        |
| ------------------------------------------------ | -------------------------------------------- | ------------------------------------------------------------- |
| Router bleibt DOWN                               | Kein passender Link oder VRF fehlt           | Prüfen ob Link existiert und `ensure_ipam_defaults` greift    |
| Edge hat keine Default-Route                     | Link Hash abgeleitet aber Insert schlug fehl | Logs prüfen (Exception abgefangen), manuelle Route hinzufügen |
| Doppeltes /31 Subnet auf zwei unabhängigen Links | Hash-Kollision extrem unwahrscheinlich       | Link-ID anpassen (Rename)                                     |

## Zusammenfassung

Immer aktive, deterministische, idempotente L3-Uplink-Autokonfiguration eliminiert fragile Race-Zustände, beschleunigt Status-Stabilisierung und vereinfacht Tests sowie Betriebsabläufe – ohne Feature-Flags.
