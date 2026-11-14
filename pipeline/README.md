# BORS – Datenaufbereitung in Python

Dieser Ordner enthält die Python-Pipeline hinter der Web-App: Aus amtlicher Vermessung, OpenStreetMap und den Angaben der Stadt Bern entsteht das bewertete Strassennetz, das die Web-App als `netz.json` lädt. Hier liegt der Stand vom 7.11.2026. Es sind Kopien aus der Projektablage, nicht der Ort, an dem die Skripte laufen.

*English: The Python/QGIS pipeline that measures street widths, rates every street segment for vehicle classes A–D and exports the network used by the web app.*

## Wo die Skripte laufen

- **QGIS-Python-Konsole** (QGIS 4.x, PyQGIS): Breite, Projekt, Router, Test (`22`, `24`, `25`, `6`, `7`, `27`).
- **Normales Python** (nur Standardbibliothek, `sqlite3`, `numpy`): Netzmaster und Web-Export (`26`, `29`–`32`, `16`, Module `bors_*.py`).

Die Skripte lesen und schreiben GeoPackages in einer festen Ordnerstruktur (`bors_pfade.py`, Wurzel überschreibbar mit `BORS_ROOT`). Die Rohdaten (amtliche Vermessung MOPUBE, Parkfelder, Baumkataster, Hinderniskartei, Baustellen) sind **nicht** im Repository: zu gross und teils mit Nutzungsbedingungen. Ohne diese Daten lassen sich die Skripte lesen, aber nicht ausführen.

## Ablauf

```
amtliche Vermessung ──► 24_AV_Export ──► 25_Breite ──┐
OpenStreetMap ───────────────────────────────────────┤
Plan Höchstgewicht, Höhenregel (Tiefbau) ────────────┼──► 26_Netzmaster ──► 6_Projekt ──► 7_Router ──► 27_QGIS_Test
Befunde am Orthofoto ────────────────────────────────┘          │                (QGIS)
22_Abbiegen (Schleppkurven) ────────────────────────────────────┤
                                                                └──► 29_Web_Netz ──► netz.json (Web-App)
Geoportal Stadt Bern ──► 30 / 16 ──► Baustellen ──► 31_Web_Baustellen ──► netz.json
Parkfelder ──► 32_Web_Parkfelder ──► parkfelder.json
```

| Datei | Aufgabe |
|---|---|
| `24_AV_Export_V9.py` | Objekte der amtlichen Vermessung bis 25 m neben dem Strassennetz exportieren (nur für einen Neuaufbau) |
| `25_Breite_V9_1.py` + `bors_breite_v9_1.py` | Freie Durchfahrtsbreite je Abschnitt: 1-m-Querprofile unter 5 Winkeln, Abzug von Parkfeldern, Mauern, Pfeilern und Bäumen, Messtoleranz pro Rand (k = 1.645) |
| `25_Breite_V9_3_BORS.py` + `bors_breite_v9_3.py` | Neue Fassung (10.11.2026, noch nicht im Volllauf): Profile ganz in einer Fahrfläche, Löcher und Mehrfachflächen richtig gemessen; je Profil Reserve gegen den örtlichen Bedarf (Spiegel nur dort über Trottoir/Insel), kurze Engstellen und Seitenwechsel hinter Hindernissen als eigene Felder; Toleranzstufe als Schätzung gekennzeichnet. Tests: `test_breite_v9_3.py` (normales Python) |
| `26_Netzmaster_V9_2h_BORS.py` | Wie V9.2g, wertet die Felder aus Breite V9.3 aus und stuft dabei nur «ausreichend» zu «nicht entscheidbar» herab (nie Freigabe, nie Sperre). Mit einer älteren Breitendatei gleich wie V9.2g |
| `22_Abbiegen_Schleppkurven.py` + `bors_schleppkurve.py` | Abbiegen und Kurven je Fahrzeug: Schleppkurven-Simulation auf der befestigten Fläche (OK / ENG / NUR_MIT_NEBENFLAECHE / UNMOEGLICH) |
| `26_Netzmaster_V9_2g_BORS.py` + `bors_bewertung_v8.py`, `bors_geo.py` | Bewertung je Abschnitt und Fahrzeugklasse A–D: VALIDIERT, UNVALIDIERT oder GESPERRT, mit Grund. Liest geprüfte Befunde und die Angaben des Tiefbauamts (Gewicht, Höhe ≥ 4 m ohne Signal) |
| `6_Projekt_V9_2f_BORS.py` | QGIS-Projekt mit Ebenen, Legende und Belegen aufbauen |
| `7_Router_V9_2f_BORS.py` | Router in QGIS: zuerst nur über validierte Strassen, sonst Ausweichroute mit ungeklärten Abschnitten (Zeit ×2, gekennzeichnet). Gesperrte Abschnitte nie. Die Web-App (`../bors_router.js`) ist eine direkte Übertragung davon |
| `27_QGIS_Test_V9_2c_BORS.py` | Testlauf des Routers mit dem Referenztestset, Protokoll PASS / FAIL / SKIP (Stand 7.11.2026: 29 PASS / 0 FAIL) |
| `29_Web_Netz_V9_2f_BORS.py` | Status, Gründe und Kosten eines Netzmasters in `netz.json` übertragen; bricht ab, wenn ein bisher gesperrter Abschnitt frei würde |
| `30_Stadt_Geoportal_Abruf_BORS.py`, `16_Stadt_Bern_Live_V3_BORS.py` | Baustellen, Installationsplätze und Poller vom Geoportal der Stadt Bern holen und den Abschnitten zuordnen (ohne Personendaten) |
| `31_Web_Baustellen_BORS.py` | Denselben Baustellenstand in `netz.json` übertragen |
| `32_Web_Parkfelder_BORS.py` | Parkfelder als Ebene für die Web-App exportieren |
| `bors_pfade.py` | Zentrale Pfade der Ablage |
| `BORS_Fahrzeuge_V1.csv` | Fahrzeugmasse der Klassen A–D (teils Annahmen, in der Datei gekennzeichnet) |
| `BORS_Wachen.csv`, `BORS_Referenztestset_V1.csv` | Startpunkt Hauptwache und Testrouten für `27` |

## Hinweise

- `22`, `24` und `25_Breite_V9_1` stammen aus dem Aufbau des Netzes und zeigen noch auf die alten Ablageorte. `25_Breite_V9_3_BORS` nutzt `bors_pfade.py`.
- Breite V9.3: Die Korrekturen sind an Testgeometrien und an einer Stichprobe von 198 Abschnitten mit den Originaldaten geprüft (im Kompatibilitätsmodus Feld für Feld gleich wie der bisherige Lauf). `netz.json` ist unverändert; eine netzweite Wirkung zeigt erst ein Volllauf `25` → `26` → QGIS-Test.
- Bekannte Grenzen der Breite: Schikanen und versetzte Parkfelder (teilweise Überlappung) sind ohne Schleppkurve entlang der Fahrlinie nicht bewertbar; die Toleranzstufe ist aus der Gebäudedichte geschätzt, weil der Toleranzstufenplan nicht in MOPUBE enthalten ist.
- Frühere Stufen (Netzaufbau aus OSM, Netzmaster V5–V8, QA-Skripte) sind hier nicht enthalten.
- Die Bewertung beruht auf Daten, nicht auf Prüfungen vor Ort. OSM-Angaben (Höhe, Poller, Signale) sind nicht vor Ort bestätigt.
- Der Zugangsschlüssel für die ASTRA-Verkehrsmeldungen ist nicht Teil des Repositorys; das zugehörige Abrufskript fehlt deshalb.
