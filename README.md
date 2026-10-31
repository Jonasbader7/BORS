# BORS Bern – Web-App (Prototyp)

Fahrzeugabhängiges Einsatzrouting für Bern und zehn Nachbargemeinden. BFH, Modul BCS HS26, Gruppe 5.

**Forschungsprototyp – keine Einsatzfreigabe.** Schilder und Poller stammen aus OpenStreetMap und sind nicht vor Ort bestätigt.

- `index.html` – Web-App (Karte, Routing für die Fahrzeugklassen A–D, Routenvergleich, Einsatzansicht, Strassenbefund, Ebenen)
- `bors_router.js` – Routing-Kern, direkte Übertragung des QGIS-Routers V9.2c (Abgleich: 325/325 Testrouten identisch), unverändert
- `netz.json` – Strassennetz V9.2b mit Bewertung je Fahrzeugklasse
- `basis.json` – Ersatz-Grundkarte aus der amtlichen Vermessung (Gebäude, Wald, Gewässer)

## Neu in Version 5 (1.11.2026)

- **Routenvergleich (je Klasse A–D):** beste Route nur über validierte Strassen (grün, geringste Routingkosten) gegen die Vergleichsroute (blau) mit Zeitunterschied, Distanz und nummerierten ungeklärten Stellen (gelb, mit Grund aus dem Netzmaster). Die Vergleichsroute ist die Route des bestehenden Modus «experimentell» (ungeklärte Abschnitte bei der Wahl mit Zeit ×2 gewichtet, wie in QGIS); angezeigt wird die Modellzeit ohne Zuschlag. Gesperrte Abschnitte und feste Poller sind in beiden Routen ausgeschlossen. Gibt es keine validierte Route, steht das so da.
- **Einsatzansicht:** Knopf oben rechts oder `?ansicht=einsatz`. Eine Klasse, grosse Schrift und Tippflächen, nur die zwei Routen auf der Karte. Die volle GIS-Ansicht bleibt unverändert erreichbar (`?ansicht=gis`). Die Wahl merkt sich der Browser.
- **Direktlink:** `?start=E,N&ziel=E,N` (LV95) öffnet eine Route direkt.
- Technisch: Der Worker rechnet pro Anfrage beide Modi (`berechne(…, 'VALIDIERT')` und `berechne(…, 'EXPERIMENTELL')`); der Vergleich ist reine Darstellung. Am Routing selbst ist nichts geändert.

Geprüft am 31.10.2026: gesperrte Abschnitte in beiden Modi ausgeschlossen (Code), 32 Testrouten Segment für Segment ohne Fehler, Abgleich mit swissTLM3D und KSVB ohne Konflikt. Nicht geprüft: Befahrbarkeit vor Ort.

Lokal starten: `python -m http.server 8771` in diesem Ordner, dann http://localhost:8771 öffnen.

Grundkarte: © swisstopo. Strassennetz: © OpenStreetMap-Mitwirkende. Fahrbahnbreiten: amtliche Vermessung Kanton Bern.
