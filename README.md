# BORS Bern – Einsatzrouting für Blaulichtfahrzeuge

*English: Vehicle-specific emergency routing for Bern. For each street and each vehicle class, BORS decides whether width, height and weight allow passage, and routes only over streets the vehicle fits. Research prototype, not approved for operational use.*

**[Web-App öffnen](https://jonasbader7.github.io/BORS/)** · [Portfolio](https://jonasbader7.github.io/Portfoliopage/)

![BORS-Web-App: Karte von Bern, Strassen nach Befahrbarkeit eingefärbt](https://jonasbader7.github.io/Portfoliopage/img/bors-app.jpg)

| | |
|---|---|
| **Frage** | Welche Strasse ist für welches Einsatzfahrzeug physisch passierbar? |
| **Gebiet** | Stadt Bern und zehn Nachbargemeinden |
| **Fahrzeuge** | A Notarzt, B Rettungswagen, C Feuerwehr mittel, D Feuerwehr gross, dazu REF (normales Auto) |
| **Rahmen** | BFH, Modul BCS HS26, Teamprojekt mit 6 Personen |
| **Meine Rolle** | Product Owner und die gesamte technische Umsetzung |
| **Technik** | Python (QGIS/PyQGIS, SQLite, NumPy) für die Daten, JavaScript (MapLibre GL, Web Worker) für die Web-App |
| **Stand** | Forschungsprototyp – keine Einsatzfreigabe |

## Wie es funktioniert

1. **Breite messen:** Aus der amtlichen Vermessung wird die befahrbare Breite mit Querprofilen gemessen; Parkfelder, Mauern und Pfeiler werden abgezogen, pro Strassenrand gilt eine Messtoleranz.
2. **Pro Fahrzeug bewerten:** Jeder Abschnitt bekommt pro Fahrzeugklasse einen Zustand: **validiert** (passt nach Daten), **unvalidiert** (ungeklärt) oder **gesperrt**. Gewichtsgrenzen und die Regel «ohne Signal mindestens 4 m Höhe» stammen vom Tiefbauamt der Stadt Bern.
3. **Routen:** Der Router fährt zuerst nur über validierte Strassen. Gibt es so keinen Weg, zeigt er eine gekennzeichnete Ausweichroute; ungeklärte Abschnitte zählen dabei mit doppelter Zeit. Gesperrte Abschnitte bietet er nie an.
4. **Einsatzablauf:** Die Web-App simuliert Notruf, Disposition, Route senden und die Wahl der Route durch die Crew (Zentrale und Fahrzeug, auch auf dem Handy).

Beispiel: An der Felsenaubrücke fahren Notarzt und Rettungswagen direkt, die grosse Feuerwehr braucht 6,8 km Umweg (Stand 29.10.2026).

## Was geprüft ist und was nicht

- **Geprüft:** Die Web-App ist eine Übertragung des QGIS-Routers; beim Abgleich der Version V9.2c waren 325 von 325 Testrouten identisch. Der QGIS-Testlauf meldet 29 bestandene und 0 fehlgeschlagene Prüfungen (5.11.2026).
- **Nicht geprüft:** BORS wurde nicht im Einsatz und nicht systematisch vor Ort getestet. Höhenangaben und Poller aus OpenStreetMap sind nicht vor Ort bestätigt.

Dieses Repository enthält die Web-App. Die Datenaufbereitung in Python/QGIS liegt nicht öffentlich.

## Dateien

- `index.html` – Web-App (Karte, Routing für die Fahrzeugklassen A–D, Routenvergleich, Einsatzablauf Zentrale/Fahrzeug, Strassenbefund, Ebenen)
- `bors_router.js` – Routing-Kern, direkte Übertragung des QGIS-Routers V9.2e (Ersatzanschluss nach Gesamtkosten)
- `netz.json` – Strassennetz V9.2g mit Bewertung je Fahrzeugklasse (Netzmaster `BORS_Netzmaster_V9_20261105_1118`)
- `netz_aenderungen.csv` – die 129 Statuswechsel gegenüber V8 (Abschnitt × Klasse)
- `basis.json` – Ersatz-Grundkarte aus der amtlichen Vermessung (Gebäude, Wald, Gewässer)
- `parkfelder.json` – Parkfeld-Flächen für die Ebene «Parkfelder» (dieselben, die von der Fahrbahnbreite abgezogen werden)

## Versionsgeschichte

Was sich von Version zu Version geändert hat, neuste zuerst.

### Neu in Version 12 (6.11.2026): Texte und Demo-Sperrung nach dem Realitätstest

Router, Strassennetz, Baustellen und Parkfelder wie V11. Behoben sind die Probleme 2 und 7–11 aus `05_Berichte/Realitaetstest_WebApp_20261106/Testbericht_BORS_V11.md`, nur in `index.html`:
- **Kurve «UNMOEGLICH» (Problem 2):** Enthält eine validierte Route eine Kurve, die das Schleppkurven-Modell nur mit Rangieren schafft, heisst sie «validiert · Kurve prüfen». Der Hinweis «Kurve laut Schleppkurven-Modell nur mit Rangieren … BORS rechnet dafür nur einen Zeitzuschlag, keine Sperre – vor Ort prüfen» steht im Tab Route, im Routenvergleich, in der Disposition und im Fahrzeug. Die Codes ENG / NUR_MIT_NEBENFLAECHE erscheinen als «eng» / «nur über Trottoir/Insel». Die Routenwahl ist unverändert (beide Router rechnen weiter nur einen Zuschlag).
- **Disposition (Problem 7):** Halt vor dem Ziel, nicht nachgewiesene Zufahrt, Poller und Kurvenhinweis stehen jetzt auch in der Karte A–D der Zentrale (vorher nur im Fahrzeug).
- **Wording (Problem 8):** «gesichert» heisst bei der validierten Route jetzt «passt nach Daten», «alle Abschnitte nachgewiesen» heisst «alle Abschnitte passen nach Daten (nicht vor Ort geprüft)». Methode-Tab: «Nach den Daten passt das Fahrzeug (nicht vor Ort geprüft)». Die Alternative bleibt «nicht gesichert».
- **Meldungen ohne Route (Problem 9):** «Keine Fahrzeugklasse hat eine Route» mit Grund: ausserhalb des Strassennetzes / Untersuchungsgebiets oder «liegt 36 m neben der nächsten Strasse, BORS bindet höchstens 30 m an». Start = Ziel: «Start und Ziel liegen am selben Ort». «… fahren ungefähr die Route eines normalen Autos» nur noch für Klassen mit Route.
- **Modus Experimentell (Problem 10):** Eine Route ohne ungeklärte Meter bleibt «validiert» (sie ist dann dieselbe wie im Modus validiert).
- **Demo-Sperrung (Problem 11):** Der Tab «Strasse» wird nach jeder Änderung der Demo-Sperren neu gezeichnet. Während der Sperre steht «gesperrt (Demo)» mit dem Befund ohne Demo; «Alle aufheben» im Tab Route setzt den Tab Strasse zurück.

Geprüft am 6.11.2026 lokal im Browser (Port 8778): Thun → «ausserhalb des Strassennetzes»; Zollikofen → «36 m neben der nächsten Strasse»; Start = Ziel; Wache → Gümligen: D «validiert · Kurve prüfen», im Modus Experimentell A/B «validiert»; Postgasse: Disposition D «Halt 98 m»; S5 Aarstrasse sperren → im Tab Route aufheben → Tab Strasse «validiert», erneut sperren/aufheben ok; Beamer 1440 × 900 «Beides» Notruf → C (beide Routen) → quittiert → vor Ort → abgeschlossen; Handy 375 × 812 Notruf → B → abgeschlossen. Keine Konsolenfehler. Den Kurvenhinweis in der Fahrzeugansicht habe ich nicht mit einem echten Auftrag ausgelöst. Nicht veröffentlicht, nicht vor Ort geprüft.

### Neu in Version 11 (6.11.2026): Ebene Parkfelder, Badge nur «Prototyp»

Router, Strassennetz und Baustellen wie V10. Neu:
- **Ebene «Parkfelder (von der Breite abgezogen)»** im Tab «Ebenen»: 4631 Flächen aus `02_Daten/2_Aktuell_V9/Vorstufen/parkierung_v5_BORS_Netz_V2_20261027_1534.gpkg` (Stadt Bern 4245 Felder, OSM 381 Strassenränder), also genau die Daten, die `25_Breite_V9_1` von der Fahrbahnbreite abzieht und QGIS in der Gruppe *03 BELEGE* zeigt. Farbe nach Art: blaue Zone, weiss/gebührenpflichtig, Spezialfelder (Gehbehinderte, Taxi, Car, LKW …), OSM-Strassenrand; ungenau verortete Flächen (3885) heller. Wird erst beim Einschalten geladen, über dem Strassennetz gezeichnet. Export mit `01_Skripte/Aktuell/32_Web_Parkfelder_BORS.py` (normales Python). Nur Anzeige, Router und `netz.json` unverändert.
- **Badge oben rechts** zeigt nur noch «Prototyp» (ohne «keine Einsatzfreigabe»). Die Hinweise «Forschungsprototyp – keine Einsatznavigation» in der Fahrzeugansicht und im Tab «Einsatz» bleiben.

Geprüft am 6.11.2026 lokal im Browser (Port 8777): Ebene ein, Flächen entlang der Strassen sichtbar (Spitalacker, Altstadt), Legende mit Zahlen; «Beides» Notruf → A senden → quittiert → vor Ort → abgeschlossen; Handy 375 × 812 Badge und Ebene. Keine Konsolenfehler. Live seit 6.11.2026 (Commit d97f8df), nicht vor Ort geprüft.

### Neu in Version 10 (5.11.2026): Baustellen Stand 5.11., Vergleich mit dem normalen Navi, Demo-Sperrung

Router und Strassennetz wie V9 (Router V9.2e, Netz V9.2g). Neu:
- **Baustellen Stand 5.11.2026** statt 28.10.: Baustellen und Installationsplätze der Stadt Bern aus dem Geoportal (`01_Skripte/Aktuell/16_Stadt_Bern_Live_V3_BORS.py`, Datei `baustellen_20261105_1622_stadt.gpkg`), ASTRA-Meldungen vom 27.10. nach Datum gefiltert. 369 statt 404 Abschnitte (52 beendet, 17 neu), dazu die neue Zuordnung eines Westside-Pollers (Riedbachstrasse w1148969056 für REF wieder frei, wie in QGIS). `netz.json` mit `01_Skripte/Aktuell/31_Web_Baustellen_BORS.py` erzeugt; Liste `netz_baustellen_aenderungen.csv`. Geprüft: Mit dem alten Stand ergibt das Skript die bisherige `netz.json` (0 Kostenabweichungen). QGIS liest dieselbe Baustellendatei automatisch.
- **Normales Navi:** Unter dem Routenvergleich zeigt die App die Auto-Route (Profil REF, ohne Fahrzeugmasse) und die Abschnitte darauf, die für die gewählte Klasse gesperrt sind; auf Wunsch auf der Karte (grau, rote ✕). Nur Darstellung, Router unverändert.
- **Demo-Sperrung** (Tab «Strasse»): einen Abschnitt für alle Fahrzeuge und das Auto sperren, BORS rechnet sofort neu (⛔ auf der Karte). Nur Laufzeit in diesem Fenster, nicht in `netz.json`, nicht in QGIS, nicht an andere Fenster übertragen.
- **Datenstand** der Baustellen im Tab «Methode».

Geprüft am 5.11.2026 lokal im Browser (Port 8776): Beamer 1440 × 900 «Beides» Notruf → Senden an C (beide Routen) → Fahrerwahl → quittiert → vor Ort → abgeschlossen; Handy 375 × 812 Notruf → Senden an B → Fahrzeug → quittiert → vor Ort → abgeschlossen; Vergleich mit normalem Navi für C (Kornhausbrücke, Kornhausplatz gesperrt, 2 ✕ auf der Karte); Demo-Sperrung Lorrainebrücke: C 1.70 → 2.47 km, nach dem Aufheben wieder 1.70 km. Keine Konsolenfehler. Nicht veröffentlicht, nicht vor Ort geprüft.

### Neu in Version 9 (5.11.2026): Netz V9.2g mit den Angaben von Tiefbau Stadt Bern

Oberfläche und Router wie V8 (Router V9.2e). Neu sind die Daten aus der Antwort von Tiefbau Stadt Bern vom 4.11.2026:
- **Plan Höchstgewicht** (Stand 4.5.2026) georeferenziert und den Abschnitten zugeordnet (Rest im Median 0.8 m). Laut Tiefbau gelten die Grenzen für alle, auch für Einsatzfahrzeuge.
  - 28 t: ganze Altstadt, Aarstrasse, Schüttestrasse, Strassen bei der Universität (u. a. Sidlerstrasse, Wildhainweg): **D gesperrt** (Wasserwerfer 28.4 t). C (17 t) und leichter unverändert.
  - 16 t, Kleine Westtangente: **C und D gesperrt** (7 Abschnitte für C neu).
  - 10 t, Zufahrt Kornhausbrücke (Kornhausplatz), Grabenpromenade und Schänzlistrasse: **C und D gesperrt** (6 Abschnitte).
  - Zusammen für D 96 Abschnitte (6.8 km) neu gesperrt, für C 13 Abschnitte (0.6 km).
  - Folge: Ein Einsatzort mitten in der Altstadt (z. B. Kramgasse) ist für D nicht mehr erreichbar («keine Route»). A–C fahren unverändert.
- **Höhe ohne Signal mind. 4.00 m** (Verkehrsregelnverordnung, vom Tiefbau bestätigt) auf öffentlichen Strassen: 7 Abschnitte für B, 6 für C und D neu validiert (u. a. Wehrstrasse, Riedmoosstrasse, Freiburgstrasse). Auf Hof- und Garagenzufahrten (OSM `service`) bleibt die Höhe ungeklärt.
- **Lehnenviadukt / Kleine Westtangente 3.20 m:** B (2.95 m) validiert, C knapp, D gesperrt.
- **Kirchenfeldbrücke:** Hinweis auf die Nutzungsvereinbarung für Notfalldienste; die Sperre für C und D bleibt, bis SRB den Inhalt bestätigt.
- `netz.json` erzeugt mit `01_Skripte/Aktuell/29_Web_Netz_V9_2f_BORS.py` aus der V8-Datei und dem Netzmaster V9.2g. Bericht: `05_Berichte/Abgleich_Tiefbauamt_20261105`.

### Neu in Version 8 (1.11.2026): Netz V9.2f und Router V9.2e

Oberfläche wie V7 (nur zwei Texte im Tab «Methode» angepasst). Neu sind die Daten und der Router:
- **Gesperrt nach Hinderniskartei Kanton Bern** (signalisiertes Gewicht an Brücken): Nydeggbrücke, Brunngasshalde, Fährstrasse, Postgasshalde für D, Reichenbachstrasse für C und D. V7 bot sie noch als validiert an.
- **Unvalidiert** (Höhe unbekannt, OSM `maxheight=below_default`): 2 Abschnitte für B–D.
- **Validiert nach geprüften Befunden** (Orthofoto, nicht vor Ort): 10 Engstellen für A–D, u. a. Viktoriarain und Nordring vor der Hauptwache, Bolligenstrasse, Papiermühlestrasse, Freiburgstrasse.
- **Router V9.2e:** Ist Start oder Ziel nicht anfahrbar, wählt er den Ersatzanschluss nach Gesamtkosten statt nach Abstand (in QGIS am 1.11.2026 geprüft, 29 PASS / 0 FAIL).
- `netz.json` erzeugt mit `01_Skripte/Aktuell/29_Web_Netz_V9_2f_BORS.py` aus der V7-Datei und dem Netzmaster; Graph, Hindernisse, Abbiegen, Baustellen und Autoreferenz unverändert.
- **Baustellen:** weiterhin Stand 28.10.2026 (keine Live-Daten, keine Aktualisierung).

Geprüft am 1.11.2026 (Browser, Handy 375 × 812 und Beamer 1440 × 900): Notruf → Senden → Quittieren → vor Ort → abgeschlossen, Fahrerwahl mit Alternative, Route über die Nydeggbrücke (A–C darüber, D umfährt). Abgleich Web gegen QGIS auf diesem Stand: ausstehend.

### Neu in Version 7 (1.11.2026): Fahrer wählt die Route

- **Zentrale:** pro Fahrzeugklasse ein Knopf. Gibt es neben der validierten Route eine Alternative mit ungeklärten Stellen, heisst er «Senden: beide Routen, Fahrer wählt». Gibt es nur die validierte Route, wird nur sie gesendet. Gibt es keine validierte Route, fragt die Zentrale nach, bevor sie nur die Vergleichsroute sendet.
- **Fahrzeug:** Vor dem Quittieren zeigt es zwei grosse Karten nebeneinander («Validiert» und «Alternative»: Zeit, Distanz, gesichert oder Anzahl ungeklärter Stellen). Auf der Karte sind beide Routen zu sehen, die gewählte breiter. Die validierte Route ist vorgewählt. Der Knopf heisst «Mit validierter Route quittieren» bzw. «Mit Alternative quittieren». Danach zeigt das Fahrzeug nur noch die gewählte Route; bei der Alternative mit der Liste der ungeklärten Stellen.
- **Rückmeldung:** Die Zentrale sieht «vorgewählt: …» und nach dem Quittieren «gewählt: …» und erhält eine Meldung, wenn der Fahrer umwählt.
- Aufträge, die V6 im Browser gespeichert hat, werden weiter gelesen (eine Route, keine Wahl).
- Grundlage ist Anjas Vorschlag (beide Routen je Klasse vergleichen), hier mit der Entscheidung beim Fahrer. Router, Netz und Grundkarte unverändert.

### Neu in Version 6 (1.11.2026): simulierter Einsatzablauf

- **Umschalter «Zentrale | Fahrzeug | Beides»** oben in der Kopfzeile (ersetzt den Knopf «Einsatzansicht»). «Beides» erscheint nur auf breiten Bildschirmen (ab 1100 × 600 px). Es zeigt rechts neben der Zentrale das Fahrzeug im Tablet-Rahmen (dieselbe Seite eingebettet, `?ansicht=fahrzeug&eingebettet=1`), gedacht für Präsentationen. Das Tablet folgt dem jeweils neuesten Auftrag. Adressen: `?ansicht=zentrale`, `?ansicht=fahrzeug`, `?ansicht=beides`.
- **Handy:** dieselbe Seite, Wechsel über den Umschalter oder den Knopf «Fahrzeug ansehen» nach dem Senden. Der Statusknopf des Fahrzeugs ist ohne Scrollen sichtbar.
- **Einstieg:** Der Tab «Einsatz» erklärt den Ablauf in drei Schritten und ist beim ersten Besuch offen.
- **Zentrale, Tab «Einsatz»:** «Notruf simulieren» setzt einen zufälligen Einsatzort auf einer benannten Strasse im Gebiet, mit erfundenem Stichwort und Priorität. Alternativ tippt die Zentrale selbst auf den Einsatzort. Als Start der Fahrzeuge dient die Hauptwache, ein zufälliger Patrouillen-Standort oder ein Punkt auf der Karte. BORS rechnet die Routen für A–D. Die Disposition zeigt je Klasse die validierte Route und die Vergleichsroute. Die Zentrale sendet einem Fahrzeug die validierte Route oder, nach einer Rückfrage, die Vergleichsroute. Gesperrte Abschnitte sind nie dabei. Die Fahrzeugliste zeigt den Status.
- **Fahrzeug:** zeigt nur den eigenen Auftrag: Stichwort, Einsatzort, die eine zugewiesene Route (grün validiert oder blau mit nummerierten gelben Stellen), Zeit und Distanz, dazu einen grossen Knopf für den nächsten Status (quittiert → vor Ort → abgeschlossen). Die Karte lässt sich ansehen, aber nicht verändern. Ohne Auftrag ist die bisherige vereinfachte Planung unter «Ohne Auftrag: Route selbst planen» erreichbar.
- **Senden** heisst im Prototyp: im Browser speichern (localStorage). Stellt man in derselben Seite auf «Fahrzeug» um, ist der Auftrag da. Ein zweites Fenster im selben Browser erhält Aufträge, Rückzüge und Statusmeldungen sofort. Ein anderes Gerät erhält nichts, dafür bräuchte es einen Server.
- Ein zweites Fenster rechnet die Route mit demselben Router selbst nach und vergleicht eine Kennung der Abschnittsfolge mit der Route der Zentrale. Bei einer Abweichung erscheint ein Hinweis.
- `bors_router.js`, `netz.json`, `basis.json` unverändert. Notrufe, Stichworte und Einsatznummern sind erfunden, Personendaten gibt es keine.

### Neu in Version 5 (1.11.2026)

- **Routenvergleich (je Klasse A–D):** beste Route nur über validierte Strassen (grün, geringste Routingkosten) gegen die Vergleichsroute (blau) mit Zeitunterschied, Distanz und nummerierten ungeklärten Stellen (gelb, mit Grund aus dem Netzmaster). Die Vergleichsroute ist die Route des bestehenden Modus «experimentell» (ungeklärte Abschnitte bei der Wahl mit Zeit ×2 gewichtet, wie in QGIS); angezeigt wird die Modellzeit ohne Zuschlag. Gesperrte Abschnitte und feste Poller sind in beiden Routen ausgeschlossen. Gibt es keine validierte Route, steht das so da.
- **Einsatzansicht:** Knopf oben rechts oder `?ansicht=einsatz`. Eine Klasse, grosse Schrift und Tippflächen, nur die zwei Routen auf der Karte. Die volle GIS-Ansicht bleibt unverändert erreichbar (`?ansicht=gis`). Die Wahl merkt sich der Browser.
- **Direktlink:** `?start=E,N&ziel=E,N` (LV95) öffnet eine Route direkt.
- Technisch: Der Worker rechnet pro Anfrage beide Modi (`berechne(…, 'VALIDIERT')` und `berechne(…, 'EXPERIMENTELL')`); der Vergleich ist reine Darstellung. Am Routing selbst ist nichts geändert.

Geprüft am 31.10.2026: gesperrte Abschnitte in beiden Modi ausgeschlossen (Code), 32 Testrouten Segment für Segment ohne Fehler, Abgleich mit swissTLM3D und KSVB ohne Konflikt. Nicht geprüft: Befahrbarkeit vor Ort.

Lokal starten: `python -m http.server 8774` in diesem Ordner, dann http://localhost:8774 öffnen.

Grundkarte: © swisstopo. Strassennetz: © OpenStreetMap-Mitwirkende. Fahrbahnbreiten: amtliche Vermessung Kanton Bern.
