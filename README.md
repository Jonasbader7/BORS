# BORS Bern – Web-App (Prototyp)

Fahrzeugabhängiges Einsatzrouting für Bern und zehn Nachbargemeinden. BFH, Modul BCS HS26, Gruppe 5.

**Prototyp – keine Einsatzfreigabe.** Schilder und Poller stammen aus OpenStreetMap und sind nicht vor Ort bestätigt.

- `index.html` – Web-App (Karte, Routing für die Fahrzeugklassen A–D, Strassenbefund, Ebenen)
- `bors_router.js` – Routing-Kern, direkte Übertragung des QGIS-Routers V9.2c (Abgleich: 325/325 Testrouten identisch)
- `netz.json` – Strassennetz V9.2b mit Bewertung je Fahrzeugklasse
- `basis.json` – Ersatz-Grundkarte aus der amtlichen Vermessung (Gebäude, Wald, Gewässer)

Grundkarte: © swisstopo. Strassennetz: © OpenStreetMap-Mitwirkende. Fahrbahnbreiten: amtliche Vermessung Kanton Bern.
