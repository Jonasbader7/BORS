# BORS Bern – Web-App (Prototyp)

Fahrzeugabhängiges Einsatzrouting für Bern und zehn Nachbargemeinden. BFH, Modul BCS HS26, Gruppe 5.

**Forschungsprototyp – keine Einsatzfreigabe.** Schilder und Poller stammen aus OpenStreetMap und sind nicht vor Ort bestätigt.

- `index.html` – Web-App (Karte, Routing für die Fahrzeugklassen A–D, Routenvergleich, Einsatzablauf Zentrale/Fahrzeug, Strassenbefund, Ebenen)
- `bors_router.js` – Routing-Kern, direkte Übertragung des QGIS-Routers V9.2c (Abgleich: 325/325 Testrouten identisch), unverändert
- `netz.json` – Strassennetz V9.2b mit Bewertung je Fahrzeugklasse
- `basis.json` – Ersatz-Grundkarte aus der amtlichen Vermessung (Gebäude, Wald, Gewässer)

## Neu in Version 6 (1.11.2026): simulierter Einsatzablauf

- **Umschalter «Zentrale | Fahrzeug | Beides»** oben in der Kopfzeile (ersetzt den Knopf «Einsatzansicht»). «Beides» erscheint nur auf breiten Bildschirmen (ab 1100 × 600 px). Es zeigt rechts neben der Zentrale das Fahrzeug im Tablet-Rahmen (dieselbe Seite eingebettet, `?ansicht=fahrzeug&eingebettet=1`), gedacht für Präsentationen. Das Tablet folgt dem jeweils neuesten Auftrag. Adressen: `?ansicht=zentrale`, `?ansicht=fahrzeug`, `?ansicht=beides`.
- **Handy:** dieselbe Seite, Wechsel über den Umschalter oder den Knopf «Fahrzeug ansehen» nach dem Senden. Der Statusknopf des Fahrzeugs ist ohne Scrollen sichtbar.
- **Einstieg:** Der Tab «Einsatz» erklärt den Ablauf in drei Schritten und ist beim ersten Besuch offen.
- **Zentrale, Tab «Einsatz»:** «Notruf simulieren» setzt einen zufälligen Einsatzort auf einer benannten Strasse im Gebiet, mit erfundenem Stichwort und Priorität. Alternativ tippt die Zentrale selbst auf den Einsatzort. Als Start der Fahrzeuge dient die Hauptwache, ein zufälliger Patrouillen-Standort oder ein Punkt auf der Karte. BORS rechnet die Routen für A–D. Die Disposition zeigt je Klasse die validierte Route und die Vergleichsroute. Die Zentrale sendet einem Fahrzeug die validierte Route oder, nach einer Rückfrage, die Vergleichsroute. Gesperrte Abschnitte sind nie dabei. Die Fahrzeugliste zeigt den Status.
- **Fahrzeug:** zeigt nur den eigenen Auftrag: Stichwort, Einsatzort, die eine zugewiesene Route (grün validiert oder blau mit nummerierten gelben Stellen), Zeit und Distanz, dazu einen grossen Knopf für den nächsten Status (quittiert → vor Ort → abgeschlossen). Die Karte lässt sich ansehen, aber nicht verändern. Ohne Auftrag ist die bisherige vereinfachte Planung unter «Ohne Auftrag: Route selbst planen» erreichbar.
- **Senden** heisst im Prototyp: im Browser speichern (localStorage). Stellt man in derselben Seite auf «Fahrzeug» um, ist der Auftrag da. Ein zweites Fenster im selben Browser erhält Aufträge, Rückzüge und Statusmeldungen sofort. Ein anderes Gerät erhält nichts, dafür bräuchte es einen Server.
- Ein zweites Fenster rechnet die Route mit demselben Router selbst nach und vergleicht eine Kennung der Abschnittsfolge mit der Route der Zentrale. Bei einer Abweichung erscheint ein Hinweis.
- `bors_router.js`, `netz.json`, `basis.json` unverändert. Notrufe, Stichworte und Einsatznummern sind erfunden, Personendaten gibt es keine.

## Neu in Version 5 (1.11.2026)

- **Routenvergleich (je Klasse A–D):** beste Route nur über validierte Strassen (grün, geringste Routingkosten) gegen die Vergleichsroute (blau) mit Zeitunterschied, Distanz und nummerierten ungeklärten Stellen (gelb, mit Grund aus dem Netzmaster). Die Vergleichsroute ist die Route des bestehenden Modus «experimentell» (ungeklärte Abschnitte bei der Wahl mit Zeit ×2 gewichtet, wie in QGIS); angezeigt wird die Modellzeit ohne Zuschlag. Gesperrte Abschnitte und feste Poller sind in beiden Routen ausgeschlossen. Gibt es keine validierte Route, steht das so da.
- **Einsatzansicht:** Knopf oben rechts oder `?ansicht=einsatz`. Eine Klasse, grosse Schrift und Tippflächen, nur die zwei Routen auf der Karte. Die volle GIS-Ansicht bleibt unverändert erreichbar (`?ansicht=gis`). Die Wahl merkt sich der Browser.
- **Direktlink:** `?start=E,N&ziel=E,N` (LV95) öffnet eine Route direkt.
- Technisch: Der Worker rechnet pro Anfrage beide Modi (`berechne(…, 'VALIDIERT')` und `berechne(…, 'EXPERIMENTELL')`); der Vergleich ist reine Darstellung. Am Routing selbst ist nichts geändert.

Geprüft am 31.10.2026: gesperrte Abschnitte in beiden Modi ausgeschlossen (Code), 32 Testrouten Segment für Segment ohne Fehler, Abgleich mit swissTLM3D und KSVB ohne Konflikt. Nicht geprüft: Befahrbarkeit vor Ort.

Lokal starten: `python -m http.server 8772` in diesem Ordner, dann http://localhost:8772 öffnen.

Grundkarte: © swisstopo. Strassennetz: © OpenStreetMap-Mitwirkende. Fahrbahnbreiten: amtliche Vermessung Kanton Bern.
