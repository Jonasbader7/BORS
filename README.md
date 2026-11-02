# BORS Bern – Web-App (Prototyp)

Fahrzeugabhängiges Einsatzrouting für Bern und zehn Nachbargemeinden. BFH, Modul BCS HS26, Gruppe 5.

**Forschungsprototyp – keine Einsatzfreigabe.** Schilder und Poller stammen aus OpenStreetMap und sind nicht vor Ort bestätigt.

- `index.html` – Web-App (Karte, Routing für die Fahrzeugklassen A–D, Routenvergleich, Einsatzablauf Zentrale/Fahrzeug, Strassenbefund, Ebenen)
- `bors_router.js` – Routing-Kern, direkte Übertragung des QGIS-Routers V9.2e (Ersatzanschluss nach Gesamtkosten)
- `netz.json` – Strassennetz V9.2f mit Bewertung je Fahrzeugklasse (Netzmaster `BORS_Netzmaster_V9_20261101_2206`)
- `netz_aenderungen.csv` – die 52 Statuswechsel gegenüber V7 (Abschnitt × Klasse)
- `basis.json` – Ersatz-Grundkarte aus der amtlichen Vermessung (Gebäude, Wald, Gewässer)

## Neu in Version 8 (1.11.2026): Netz V9.2f und Router V9.2e

Oberfläche wie V7 (nur zwei Texte im Tab «Methode» angepasst). Neu sind die Daten und der Router:
- **Gesperrt nach Hinderniskartei Kanton Bern** (signalisiertes Gewicht an Brücken): Nydeggbrücke, Brunngasshalde, Fährstrasse, Postgasshalde für D, Reichenbachstrasse für C und D. V7 bot sie noch als validiert an.
- **Unvalidiert** (Höhe unbekannt, OSM `maxheight=below_default`): 2 Abschnitte für B–D.
- **Validiert nach geprüften Befunden** (Orthofoto, nicht vor Ort): 10 Engstellen für A–D, u. a. Viktoriarain und Nordring vor der Hauptwache, Bolligenstrasse, Papiermühlestrasse, Freiburgstrasse.
- **Router V9.2e:** Ist Start oder Ziel nicht anfahrbar, wählt er den Ersatzanschluss nach Gesamtkosten statt nach Abstand (in QGIS am 1.11.2026 geprüft, 29 PASS / 0 FAIL).
- `netz.json` erzeugt mit `01_Skripte/Aktuell/29_Web_Netz_V9_2f_BORS.py` aus der V7-Datei und dem Netzmaster; Graph, Hindernisse, Abbiegen, Baustellen und Autoreferenz unverändert.
- **Baustellen:** weiterhin Stand 28.10.2026 (keine Live-Daten, keine Aktualisierung).

Geprüft am 1.11.2026 (Browser, Handy 375 × 812 und Beamer 1440 × 900): Notruf → Senden → Quittieren → vor Ort → abgeschlossen, Fahrerwahl mit Alternative, Route über die Nydeggbrücke (A–C darüber, D umfährt). Abgleich Web gegen QGIS auf diesem Stand: ausstehend.

## Neu in Version 7 (1.11.2026): Fahrer wählt die Route

- **Zentrale:** pro Fahrzeugklasse ein Knopf. Gibt es neben der validierten Route eine Alternative mit ungeklärten Stellen, heisst er «Senden: beide Routen, Fahrer wählt». Gibt es nur die validierte Route, wird nur sie gesendet. Gibt es keine validierte Route, fragt die Zentrale nach, bevor sie nur die Vergleichsroute sendet.
- **Fahrzeug:** Vor dem Quittieren zeigt es zwei grosse Karten nebeneinander («Validiert» und «Alternative»: Zeit, Distanz, gesichert oder Anzahl ungeklärter Stellen). Auf der Karte sind beide Routen zu sehen, die gewählte breiter. Die validierte Route ist vorgewählt. Der Knopf heisst «Mit validierter Route quittieren» bzw. «Mit Alternative quittieren». Danach zeigt das Fahrzeug nur noch die gewählte Route; bei der Alternative mit der Liste der ungeklärten Stellen.
- **Rückmeldung:** Die Zentrale sieht «vorgewählt: …» und nach dem Quittieren «gewählt: …» und erhält eine Meldung, wenn der Fahrer umwählt.
- Aufträge, die V6 im Browser gespeichert hat, werden weiter gelesen (eine Route, keine Wahl).
- Grundlage ist Anjas Vorschlag (beide Routen je Klasse vergleichen), hier mit der Entscheidung beim Fahrer. Router, Netz und Grundkarte unverändert.

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

Lokal starten: `python -m http.server 8774` in diesem Ordner, dann http://localhost:8774 öffnen.

Grundkarte: © swisstopo. Strassennetz: © OpenStreetMap-Mitwirkende. Fahrbahnbreiten: amtliche Vermessung Kanton Bern.
