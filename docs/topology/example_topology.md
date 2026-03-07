Simuliere ein realistisches Lastszenario basierend auf folgender FTTH-Topologie:

Backbone:

- backbone_gateway
  → core_router
  → edge_router

Zweig 1:

- edge_router
  → aon_switch
  → aon_cpe

Zweig 2:

- edge_router
  → olt
  → odf
  → ont

Anforderungen:

- Alle Geräte sind exakt wie durch "→" verbunden.
- Provisioniere die Geräte nacheinander: core_router → edge_router → Zweige.
- Stelle sicher, dass aon_cpe und ont Traffic generieren:
  - Gerät erfolgreich provisioniert
  - Tarif vorhanden
  - Status = online
    → dann beginnt Traffic Engine zu arbeiten.

Testziel:

- Führe die Provisionierung und Link-Erstellung per API durch (z. B. via `scripts/load_test_scenario.py`).
- Beobachte währenddessen die Grafana-Dashboards.
- Messe:
  - Gesamtdauer des Szenarios
  - Latenz der API-Endpunkte
  - Teuerste Phasen im `status_recompute` und `traffic_engine.tick`

Ziel:

- Generiere realistische Messdaten unter aktiver Systemlast.
- Ermittle Engpässe und Optimierungspotenzial unter realen Bedingungen.
