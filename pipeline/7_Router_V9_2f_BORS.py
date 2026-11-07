# -*- coding: utf-8 -*-
r"""BORS ROUTER V9.2f_BORS (5.11.2026): wie 7_Router_V9_2e_BORS.py, nur eine Fehlerbehebung in der Ursachen-Diagnose:
  Fand ein Profil gar keine Route, brach die Diagnose mit KeyError '_row' ab (self.info[...]['_row'] gab es nie) und meldete
  TECHNISCHER_FEHLER statt der Ursache (EINBAHNRICHTUNG_VERHINDERT_VERBINDUNG / FAHRZEUGBESCHRAENKUNG_TRENNT /
  UNTERSCHIEDLICHE_NETZKOMPONENTEN / AUSSERHALB_UNTERSUCHUNGSGEBIET). Neu steht die Gemeinde im Abschnitt (info['gemeinde']),
  der Randtest liest sie dort - wie die Web-App (bors_router.js, Attribut 'ausserhalb' = gemeinde 'ausserhalb AOI').
  Gefundene Routen, Kosten und alle anderen Ergebnisse sind unveraendert. Seit mindestens 29.10.2026 bekannt
  (27_QGIS_Test Nr. 14, Abgleich Web 24 Faelle).
    p = Path.home() / 'OneDrive' / 'Desktop' / 'BORS' / '01_Skripte' / 'Aktuell' / '7_Router_V9_2f_BORS.py'
BORS ROUTER V9.2e_BORS (29.10.2026): wie 7_Router_V9_2c_BORS.py, neu nur die Wahl des Ersatzanschlusses (Arbeitspaket 2):
  Ist Start/Ziel fuer das Fahrzeug nicht anfahrbar oder der naechste zulaessige Abschnitt abgeschnitten (F4), wird der
  Anschluss nicht mehr nach Abstand (bzw. aus 6 Kandidaten) gewaehlt, sondern nach Gesamtkosten: eine Suche ueber alle
  zulaessigen Anschluesse bis F4_MAX_M, Restweg zu Fuss mit RESTWEG_SEK_PRO_M bewertet (RoutingKern.route_mehrfach).
  Weiter als F4_MAX_M gibt es keinen Ersatzanschluss mehr (vorher bis DIAG_SUCHE_M) -> wie jede fehlende validierte Route
  Rueckfall auf experimentell. Routen ohne Ersatzanschluss und REF rechnen unveraendert.
  Web-Gegenstueck: 04_WebApp/Entwicklung_V9_2e/bors_router.js.
  Fahrzeuge/Wachen aus 01_Skripte/Aktuell, Baustellen aus 02_Daten/1_Rohdaten/Baustellen_Verkehrsmeldungen,
  OSM-Hindernispunkte aus 02_Daten/2_Aktuell_V9/Vorstufen, Routen-Ausgaben nach 02_Daten/5_Routen_Ausgaben.
STARTEN (QGIS-Python-Konsole, Ablage BORS):
    from pathlib import Path
    p = Path.home() / 'OneDrive' / 'Desktop' / 'BORS' / '01_Skripte' / 'Aktuell' / '7_Router_V9_2e_BORS.py'
    exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'))
BORS ROUTER V9.2c - Profile A-D, Breite aus geometrischer Messung (25_Breite_V9 / 26_Netzmaster_V9).
Zwei Modi:
  VALIDIERT      nur Abschnitte, deren Breite geometrisch nachgewiesen (oder normativ abgeleitet) ist und fuer die keine
                 Hinweise auf Hoehe/Gewicht/Hindernis vorliegen. Gibt es keine solche Route, wird das ausdruecklich angezeigt
                 und zusaetzlich die experimentelle Route berechnet (deutlich als UNVALIDIERT markiert).
  EXPERIMENTELL  zusaetzlich Abschnitte "nicht entscheidbar" mit Risikozuschlag RISIKO_FAKTOR auf die Fahrzeit.
Nachweislich zu enge oder gesperrte Abschnitte sind in beiden Modi ausgeschlossen.
BORS Bern - Router V8 (QGIS 4.x, EPSG:2056) - Prototyp, KEINE Einsatzfreigabe.

NEU in V8 (28.10.2026):
- KONKRETE FAHRZEUGE: Auswahlliste aus BORS_Fahrzeuge_V1.csv (NEF, RTW, TLF 14, G-TLF 16, ADL, Wasserwerfer ...).
  Kategorien A-D bleiben als Huelle (groesstes Fahrzeug der Kategorie). Bewertung je Fahrzeug aus Netzmaster V8
  (Tabelle fahrzeug_kat_v8, Script 21): Breite getrennt nach Karosserie (gegen parkierte Autos/Baeume) und Spiegel
  (nur gegen feste Objekte ohne Trottoir), Hoehe/Gewicht als Zahl.
- ABBIEGEN/KURVEN: Schleppkurven-Simulation je Fahrzeug (Script 22, BORS_Abbiegen_V8_*.gpkg). Der Routing-Kern rechnet
  jetzt kantenbasiert (Abbiegen kostet je nach Ergebnis): UNMOEGLICH +240 s (Rangieren/Umkehren, Route weicht aus),
  nur mit Nebenflaeche +60 s, ENG +20 s, Spitzkehre > 120 Grad +240 s fuer Lastwagen / +60 s fuer PW.
- ZUFAHRT / LETZTE METER: liegt das Ziel an einer fuer das Fahrzeug kritischen Zufahrt (z. B. nur 18 t, zu eng),
  prueft der Router einen Haltepunkt an einer geeigneten Strasse bis 60 m vor dem Ziel. Gewaehlt wird, was insgesamt
  guenstiger ist (Restweg zu Fuss/Schlauch mit 2 s/m bewertet). Status ZIEL_ZU_FUSS.
- ADRESSSUCHE (amtliches Gebaeudeadressverzeichnis via api3.geo.admin.ch) fuer Start und Ziel, Wachen-Liste
  BORS_Wachen.csv. Das Ziel ist der Gebaeudeeingang; angefahren wird die naechste geeignete Strasse.

NEU in V7.6: DOMINANZ-REGEL - was fuer ein schwereres Fahrzeug zulaessig ist, ist fuer ein leichteres mindestens so gut.
Ist die Route eines schwereren Profils schneller, uebernimmt das leichtere sie (mit Hinweis). Damit faehrt C nie mehr
langsamer als D (vorher in 4.6 % der Profilpaare). Abschalten: BORS_DOMINANZ = False vor dem Start.
Zusaetzlich Erklaerung, wenn ein leichteres Fahrzeug eine LAENGERE Route hat als ein schwereres (z. B. C laenger als D):
das ist kein Fehler, sondern Folge der Risikobewertung - das leichtere Fahrzeug hat eine Ausweichmoeglichkeit mit
weniger Verdacht/ungeklaert, die fuer das schwerere selbst Verdacht ist. Der Router nennt jetzt die Meter, die dadurch
vermieden werden (Protokoll + Vergleichsansicht). Protokoll zeigt "Fahrzeit-min" statt "Modell-min".
Netzmaster V7.6 (19_Netzmaster_V7_6.py) wird automatisch genutzt, wenn er im Projekt geladen ist.

NEU in V7.5 (aus 1000 Zufallsrouten und gezielter Fehlersuche, 27.10.2026):
- Fahrzeit getrennt von Routing-Kosten: angezeigt wird die Fahrzeit (Laenge / Modellgeschwindigkeit + 30 s je zu
  oeffnendem Tor/Poller). Die Unsicherheits-Aufschlaege (Verdacht x4, ungeklaert x1.3, Baustelle x1.5) steuern nur
  die Routenwahl. Vorher erschien der NEF in 5 % der Faelle "langsamer als ein normales Auto".
- Feste Sperren (Poller fest, Betonblock ...) sperren nur noch den DURCHGANG an ihrem Punkt, nicht den ganzen
  Abschnitt. Vorher waren Haeuser vor dem Poller unerreichbar (z. B. Aarhaldenstrasse). Punkte aus osm_hindernispunkte
  (Documents\BORS_Netz_V2). Auch das Referenz-Auto faehrt nicht mehr durch feste Sperren.
- Tore/oeffenbare Poller (OSM und Stadt Bern): +30 s am Punkt statt x1.5 auf den ganzen Abschnitt.
- Zufahrten, Parkplatzgassen, Drive-through (service=driveway/parking_aisle/drive-through) als Abkuerzung: x3
  (11 % der Routen fuehrten durch eine Hauszufahrt, einige D-Routen durch einen Drive-through).
- OSM hgv=no/destination/delivery (LKW-Fahrverbot/Zubringer) wurde nie ausgewertet: fuer C und D jetzt wie
  eingeschraenkte Zufahrt (Sonderrecht x1.2, Hinweis).

NEU in V7.4: Absturz beim Zeichnen der Route behoben (Fatal Python error: Aborted in _karte). Ursache: eine
Linien-Symbolebene wurde aus einem temporaeren Symbol geklont, das Python schon wieder freigegeben hatte.
Jetzt wird die Symbolebene direkt erzeugt (QgsSimpleLineSymbolLayer). Ungueltige Routen-Layer werden uebersprungen.
Aus dem Zufallstest (100 Routen, 27.10.2026):
- Klick-Zuordnung: Ein Klick auf eine Strasse ueber einem Tunnel konnte in den Autobahntunnel darunter springen
  (Brünnen/A1 -> 7.8 km Umweg). Tunnel erhalten jetzt +25 m, Autobahn/Autostrasse +10 m "Klick-Malus" bei der Wahl
  der naechsten Strasse (die gemeldete Distanz bleibt die echte).
- Referenz (Auto ohne Sonderrecht): Zubringer-/Anliegerstrassen (destination, Zubringerdienst gestattet) waren ganz
  gesperrt -> 23 % der Referenzrouten scheiterten. Jetzt erlaubt mit Faktor x5 (wie ein normales Navi: nur am Anfang/Ende).

NEU in V7.3 (Stabilitaet): Die Berechnung startet NICHT mehr innerhalb des Maus-Klicks, sondern kurz danach
(QTimer). Vorher wurden Layer entfernt/neu geladen, waehrend QGIS den Klick noch verarbeitete -> moeglicher Absturz.
Zusaetzlich schreibt Python bei einem harten Absturz die Stelle in Documents\BORS_V7_QA\routen\absturz_protokoll.txt.

NEU in V7.2: liest aus der neuesten Baustellendatei auch die Daten der Stadt Bern (16_Stadt_Bern_Live.py):
Baustellen/Installationsplaetze (Aufschlag x1.5, Restbreite unbekannt) und gesteuerte Polleranlagen
(Tabelle stadt_poller): Poller = Oeffnen noetig (x1.5, nicht garantiert); 'Dauersperre' = Fahrverbot -> Referenz
gesperrt, Einsatzprofile nur mit Sonderrecht.

NEU in V7.1 (technisch, keine Oberflaechen-Neugestaltung):
- Nutzt den Netzmaster V7 (Layer "BORS Netz V7 (Routing)"), falls geladen: Kategorie <p>_kat_v7, Zugang zugang_v7
  (inkl. OSM vehicle=/motorcar=), Belegstufe. Sonst wie V7 mit "BORS Netz V5 (Routing)".
- Belege: fuer jedes befahrene Segment werden die Evidenzzeilen (Tabelle evidenz im Netzmaster) abgerufen und
  im Routen-GeoPackage als Tabelle route_belege gespeichert; das Protokoll nennt offene Kriterien je Route.
- Ziel/Start fuer das Fahrzeug gesperrt: Status ZIEL_NICHT_ANFAHRBAR + ueberpruefbarer Alternativ-Anfahrtspunkt
  (naechste zulaessige Strasse) mit Route dorthin. Die Restdistanz wird NICHT als befahren gezaehlt.
- Baustellen mit Zeitbezug: BORS_ZEITPUNKT (Standard: jetzt); aktiv nur von <= Zeitpunkt <= bis; Lagequelle
  (TMC = Abschnitt, Lage ungenau / Koordinaten); Fahrtrichtung in den Daten nicht vorhanden -> beide Richtungen.
- Routenlaenge = Summe der ungerundeten Kantenlaengen; Toleranz der gerundeten Zeilen: <= 0.005 m je Zeile.

STARTEN (QGIS-Python-Konsole, Projekt mit Layer "BORS Netz V5 (Routing)" offen):
    from pathlib import Path
    p = Path.home() / 'Downloads' / 'BORS_AKTUELL' / '7_Router_V8.py'
    exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'))

NEU in V7 (gegenueber 7_Router_V6.py, das unveraendert bleibt):
1. Eigener Routing-Kern (Dijkstra auf den Stuetzpunkten der Netz-Segmente) statt
   native:shortestpathpointtopoint. Jede Kante kennt ihre seg_id -> die befahrenen Segmente,
   Fahrtrichtung, Teilstuecke (Start/Ziel mitten im Segment), Laengen und Kosten sind EXAKT
   (keine raeumliche Nachzuordnung ueber einen Puffer mehr).
   Pro Lauf: GeoPackage mit Tabelle/Layer route_edges + diagnose in Documents\BORS_V7_QA\routen.
2. "Keine Route" wird begruendet: KEIN_NETZ_IN_ZIELNAEHE | NETZ_VORHANDEN_ABER_FUER_FAHRZEUG_AUSGESCHLOSSEN
   | EINBAHNRICHTUNG_VERHINDERT_VERBINDUNG | FAHRZEUGBESCHRAENKUNG_TRENNT | UNTERSCHIEDLICHE_NETZKOMPONENTEN
   | TECHNISCHER_FEHLER - jeweils mit Abstand + seg_id der naechsten Strasse und naechsten zulaessigen Strasse.
3. Aufgeraeumte Oberflaeche fuer Praesentationen; technisches Protokoll einklappbar.
4. Kategorie-Laengen = Routenlaenge (gleiche Kanten). Die alte Abweichung (z. B. 2061 statt 2055 m) kam
   daher, dass V6 die Kategorien ueber einen 1.5-m-Puffer um die Route aus GANZEN Segmenten summierte.

Modellannahmen (unveraendert, im Team festzulegen): Geschwindigkeiten je Strassentyp, Kostenfaktoren
KAT_FAKTOR, Sonderrecht x1.2, Oeffnen x1.5, Baustelle x1.5 / x4. Modellzeit = KEINE reale Einsatzzeit.
Aus der Konsole nutzbar (z. B. fuer 12_Regressionstest_V7.py):
    BORS_ROUTER.berechne((x1, y1), (x2, y2), ['REF', 'A', 'B', 'C', 'D'])  -> dict je Profil
"""
import csv
import re
import heapq
import math
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
# BORS-Ablage: zentrale Pfade aus 01_Skripte/Aktuell/bors_pfade.py (BORS_ROOT ueberschreibbar)
_BR = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
exec(compile((_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py').read_text(encoding='utf-8'), str(_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py'), 'exec'))

# ===================================================================== KERN START (reines Python)
ROAD_TYPES = {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary',
              'secondary_link', 'tertiary', 'tertiary_link', 'unclassified', 'residential', 'living_street',
              'service', 'road'}


class RoutingKern:
    """Gerichteter Graph auf den Stuetzpunkten aller Segmente. Knoten = Koordinate (auf 1 cm gerundet),
    Kante = zwei aufeinanderfolgende Stuetzpunkte EINES Segments (fid). Verbindungen zwischen Segmenten
    entstehen nur an gemeinsamen Stuetzpunkten (wie QGIS-Netzwerkanalyse mit Toleranz 0)."""

    def __init__(self):
        self.nodes = {}
        self.xy = []
        self.out = []
        self.und = []
        self.feat = {}

    def _node(self, x, y):
        k = (round(x, 2), round(y, 2))
        n = self.nodes.get(k)
        if n is None:
            n = len(self.xy)
            self.nodes[k] = n
            self.xy.append((x, y))
            self.out.append([])
            self.und.append([])
        return n

    def add_feature(self, fid, parts, direction):
        fw = direction in ('BOTH', 'FORWARD')
        bw = direction in ('BOTH', 'BACKWARD')
        cums, offs, idss, off = [], [], [], 0.0
        for pi, pts in enumerate(parts):
            cum = [0.0]
            for i in range(1, len(pts)):
                cum.append(cum[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
            ids = [self._node(x, y) for x, y in pts]
            for i in range(len(pts) - 1):
                L = cum[i + 1] - cum[i]
                if L <= 1e-9 or ids[i] == ids[i + 1]:
                    continue
                if fw:
                    self.out[ids[i]].append((ids[i + 1], fid, pi, cum[i], cum[i + 1], L))
                if bw:
                    self.out[ids[i + 1]].append((ids[i], fid, pi, cum[i + 1], cum[i], L))
                self.und[ids[i]].append((ids[i + 1], fid))
                self.und[ids[i + 1]].append((ids[i], fid))
            cums.append(cum); offs.append(off); idss.append(ids); off += cum[-1]
        self.feat[fid] = dict(parts=parts, cum=cums, off=offs, ids=idss, L=off, fw=fw, bw=bw)

    def project(self, fid, x, y):
        """Lotfusspunkt auf Segment fid -> (abstand, part, i, pos_im_part, px, py)."""
        best = None
        f = self.feat[fid]
        for pi, pts in enumerate(f['parts']):
            cum = f['cum'][pi]
            for i in range(len(pts) - 1):
                ax, ay = pts[i]; bx, by = pts[i + 1]
                dx, dy = bx - ax, by - ay
                l2 = dx * dx + dy * dy
                if l2 <= 0:
                    continue
                t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / l2))
                px, py = ax + t * dx, ay + t * dy
                d = math.hypot(x - px, y - py)
                if best is None or d < best[0]:
                    best = (d, pi, i, cum[i] + t * (cum[i + 1] - cum[i]), px, py)
        return best

    def _anbindung(self, fid, snap, ist_start):
        """Virtuelle Kanten vom Startpunkt weg bzw. zum Zielpunkt hin (Teilstuecke des Segments)."""
        _, pi, i, pos, _, _ = snap
        f = self.feat[fid]
        cum, ids = f['cum'][pi], f['ids'][pi]
        r = []
        if ist_start:
            if f['fw']:
                r.append((ids[i + 1], fid, pi, pos, cum[i + 1], abs(cum[i + 1] - pos)))
            if f['bw']:
                r.append((ids[i], fid, pi, pos, cum[i], abs(pos - cum[i])))
        else:
            if f['fw']:
                r.append((ids[i], (fid, pi, cum[i], pos, abs(pos - cum[i]))))
            if f['bw']:
                r.append((ids[i + 1], (fid, pi, cum[i + 1], pos, abs(cum[i + 1] - pos))))
        return r

    def route(self, s_fid, s_snap, t_fid, t_snap, kosten, punkte=None, abbiegen=None):
        """Dijkstra. kosten: dict fid -> Sekunden je Meter (fehlender fid = gesperrt).
        punkte: fid -> [(part, pos, sek oder None)]; None = Durchgang gesperrt, sonst Zeitzuschlag beim Passieren.
        -> (gesamtkosten_s, [(fid, part, pos_von, pos_bis, laenge_m)]) oder None."""
        punkte = punkte or {}
        turn = (abbiegen or {}).get('turn', {}); kurve = (abbiegen or {}).get('kurve', {})
        self.letzte_abbiegen = []
        S, T = -1, -2
        start_edges = self._anbindung(s_fid, s_snap, True)
        into_t = defaultdict(list)
        for node, (fid, pi, a, b, L) in self._anbindung(t_fid, t_snap, False):
            into_t[node].append((T, fid, pi, a, b, L))
        if s_fid == t_fid and s_snap[1] == t_snap[1]:
            f = self.feat[s_fid]; a, b = s_snap[3], t_snap[3]
            if (b >= a and f['fw']) or (b <= a and f['bw']):
                start_edges.append((T, s_fid, s_snap[1], a, b, abs(b - a)))
        S0 = (S, None)
        dist = {S0: 0.0}
        prev = {}
        pq = [(0.0, S, None)]
        inf = float('inf')
        ziel = None
        while pq:
            d, u, fin = heapq.heappop(pq)
            if u == T:
                ziel = (u, fin)
                break
            if d > dist.get((u, fin), inf):
                continue
            edges = start_edges if u == S else self.out[u]
            for lst in (edges, into_t.get(u, ())):
                for e in lst:
                    c = kosten.get(e[1])
                    if c is None:
                        continue
                    extra = 0.0
                    if fin is not None and e[1] != fin:
                        extra += turn.get((u, fin, e[1]), 0.0)
                    if e[1] != fin:
                        extra += kurve.get((e[1], 'fw' if e[4] >= e[3] else 'bw'), 0.0)
                    pl = punkte.get(e[1])
                    if pl:
                        lo, hi = min(e[3], e[4]), max(e[3], e[4])
                        sperre = False
                        for ppi, pos, sek in pl:
                            if ppi != e[2]:
                                continue
                            if sek is None:
                                if lo - 0.01 <= pos <= hi + 0.01:
                                    sperre = True
                                    break
                            elif lo + 0.01 < pos < hi - 0.01 or abs(pos - e[4]) <= 0.01:
                                extra += sek
                        if sperre:
                            continue
                    nd = d + e[5] * c + extra
                    key = (e[0], e[1])
                    if nd < dist.get(key, inf) - 1e-12:
                        dist[key] = nd
                        prev[key] = ((u, fin), e)
                        heapq.heappush(pq, (nd, e[0], e[1]))
        if ziel is None:
            return None
        weg, v = [], ziel
        while v != S0:
            (u, fin), e = prev[v]
            weg.append((e[1], e[2], e[3], e[4], e[5]))
            if fin is not None and e[1] != fin and (u, fin, e[1]) in turn:
                self.letzte_abbiegen.append((u, fin, e[1], turn[(u, fin, e[1])]))
            v = (u, fin)
        weg.reverse()
        self.letzte_abbiegen.reverse()
        return dist[ziel], weg

    def route_mehrfach(self, starts, ziele, kosten, punkte=None, abbiegen=None):
        """V9.2e: Dijkstra wie route, aber mit mehreren Start- und Zielanschluessen gleichzeitig.
        starts/ziele: [(fid, snap, zuschlag_s)]. Der Zuschlag (Restweg zu Fuss) zaehlt in der Suche mit -> guenstigstes Paar.
        -> (kosten_ohne_zuschlaege_s, weg, i_start, i_ziel) oder None."""
        punkte = punkte or {}
        turn = (abbiegen or {}).get('turn', {}); kurve = (abbiegen or {}).get('kurve', {})
        self.letzte_abbiegen = []
        S, T = -1, -2
        start_edges = []
        for i, (fid, sn, z) in enumerate(starts):
            for e in self._anbindung(fid, sn, True):
                start_edges.append(e + (z, i))
        into_t = defaultdict(list)
        for j, (fid, sn, z) in enumerate(ziele):
            for node, (tf, pi, a, b, L) in self._anbindung(fid, sn, False):
                into_t[node].append((T, tf, pi, a, b, L, z, j))
        for i, (sf, ss, zs) in enumerate(starts):
            for j, (tf, ts, zt) in enumerate(ziele):
                if sf == tf and ss[1] == ts[1]:
                    f = self.feat[sf]; a, b = ss[3], ts[3]
                    if (b >= a and f['fw']) or (b <= a and f['bw']):
                        start_edges.append((T, sf, ss[1], a, b, abs(b - a), zs + zt, i, j))
        S0 = (S, None)
        dist = {S0: 0.0}
        prev = {}
        pq = [(0.0, S, None)]
        inf = float('inf')
        ziel = None
        while pq:
            d, u, fin = heapq.heappop(pq)
            if u == T:
                ziel = (u, fin)
                break
            if d > dist.get((u, fin), inf):
                continue
            edges = start_edges if u == S else self.out[u]
            for virt, lst in ((u == S, edges), (True, into_t.get(u, ()))):
                for e in lst:
                    c = kosten.get(e[1])
                    if c is None:
                        continue
                    extra = e[6] if virt else 0.0
                    if fin is not None and e[1] != fin:
                        extra += turn.get((u, fin, e[1]), 0.0)
                    if e[1] != fin:
                        extra += kurve.get((e[1], 'fw' if e[4] >= e[3] else 'bw'), 0.0)
                    pl = punkte.get(e[1])
                    if pl:
                        lo, hi = min(e[3], e[4]), max(e[3], e[4])
                        sperre = False
                        for ppi, pos, sek in pl:
                            if ppi != e[2]:
                                continue
                            if sek is None:
                                if lo - 0.01 <= pos <= hi + 0.01:
                                    sperre = True
                                    break
                            elif lo + 0.01 < pos < hi - 0.01 or abs(pos - e[4]) <= 0.01:
                                extra += sek
                        if sperre:
                            continue
                    nd = d + e[5] * c + extra
                    key = (e[0], e[1])
                    if nd < dist.get(key, inf) - 1e-12:
                        dist[key] = nd
                        prev[key] = ((u, fin), e)
                        heapq.heappush(pq, (nd, e[0], e[1]))
        if ziel is None:
            return None
        weg, v, i_s, i_z = [], ziel, -1, -1
        while v != S0:
            (u, fin), e = prev[v]
            if e[0] == T:
                if u == S:
                    i_s, i_z = e[7], e[8]
                else:
                    i_z = e[7]
            elif u == S:
                i_s = e[7]
            weg.append((e[1], e[2], e[3], e[4], e[5]))
            if fin is not None and e[1] != fin and (u, fin, e[1]) in turn:
                self.letzte_abbiegen.append((u, fin, e[1], turn[(u, fin, e[1])]))
            v = (u, fin)
        weg.reverse()
        self.letzte_abbiegen.reverse()
        return dist[ziel] - starts[i_s][2] - ziele[i_z][2], weg, i_s, i_z

    def zusammenfassen(self, weg):
        """Aufeinanderfolgende Kanten desselben Segments (gleiche Richtung, lueckenlos) zusammenfassen."""
        rows = []
        for fid, pi, a, b, L in weg:
            if L <= 1e-9:
                continue
            if rows:
                r = rows[-1]
                if r[0] == fid and r[1] == pi and abs(r[3] - a) < 1e-6 and (r[3] - r[2]) * (b - a) >= 0:
                    rows[-1] = (fid, pi, r[2], b, r[4] + L)
                    continue
            rows.append((fid, pi, a, b, L))
        return rows

    def teilgeometrie(self, fid, pi, a, b):
        """Stuetzpunkte des Segmentteils zwischen pos a und b (in Fahrtrichtung)."""
        pts, cum = self.feat[fid]['parts'][pi], self.feat[fid]['cum'][pi]
        lo, hi = min(a, b), max(a, b)

        def at(p):
            for i in range(len(cum) - 1):
                if cum[i] - 1e-9 <= p <= cum[i + 1] + 1e-9:
                    t = 0.0 if cum[i + 1] == cum[i] else (p - cum[i]) / (cum[i + 1] - cum[i])
                    return (pts[i][0] + t * (pts[i + 1][0] - pts[i][0]), pts[i][1] + t * (pts[i + 1][1] - pts[i][1]))
            return pts[-1]
        out = [at(lo)] + [pts[i] for i in range(len(pts)) if lo + 1e-9 < cum[i] < hi - 1e-9] + [at(hi)]
        return out if b >= a else out[::-1]

    def ungerichtet_verbunden(self, s_fid, s_snap, t_fid, t_snap, erlaubt):
        """BFS ohne Fahrtrichtung, nur ueber Segmente in 'erlaubt' (None = alle)."""
        f, g = self.feat[s_fid], self.feat[t_fid]
        start = {f['ids'][s_snap[1]][s_snap[2]], f['ids'][s_snap[1]][s_snap[2] + 1]}
        ziel = {g['ids'][t_snap[1]][t_snap[2]], g['ids'][t_snap[1]][t_snap[2] + 1]}
        if start & ziel:
            return True
        seen, stack = set(start), list(start)
        while stack:
            u = stack.pop()
            for v, fid in self.und[u]:
                if v in seen or (erlaubt is not None and fid not in erlaubt):
                    continue
                if v in ziel:
                    return True
                seen.add(v)
                stack.append(v)
        return False
# ===================================================================== KERN ENDE

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (QApplication, QWidget, QDockWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                                 QLabel, QPushButton, QTextEdit, QMessageBox, QButtonGroup, QFrame,
                                 QTableWidget, QTableWidgetItem, QToolButton, QScrollArea, QComboBox, QLineEdit, QCheckBox)
from qgis.core import (QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsLineSymbol,
                       QgsMarkerSymbol, QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsSpatialIndex,
                       QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings,
                       QgsSimpleLineSymbolLayer)
from qgis.gui import QgsMapToolEmitPoint
from osgeo import ogr, osr

PROFILE = {
    'A': dict(kurz='NEF', label='A · NEF', width=2.20, height=1.70, tonnes=3.1),
    'B': dict(kurz='RTW', label='B · RTW', width=2.45, height=2.90, tonnes=5.5),
    'C': dict(kurz='Feuerwehr mittel', label='C · Feuerwehr mittel', width=2.90, height=3.20, tonnes=18.0),
    'D': dict(kurz='Feuerwehr gross', label='D · Feuerwehr gross', width=3.00, height=3.66, tonnes=28.4),
}
SIDE_RESERVE_M = 0.25
AKT_DIR = Path(globals().get('BORS_AKTUELL', P_SKRIPTE))
ZUFAHRT_RESTWEG_M = float(globals().get('BORS_RESTWEG_M', 60.0))
RESTWEG_SEK_PRO_M = 2.0
ABBIEGE_SEK = {'UNMOEGLICH': 120.0, 'NUR_MIT_NEBENFLAECHE': 45.0, 'ENG': 15.0}   # Zuschlag, keine Sperre (Modell = Obergrenze; NICHT_BELASTBAR = 0)
TURN_FZ = {'NEF': 'NEF', 'PW_X1': 'NEF', 'PW_ETRON': 'NEF', 'RTW': 'RTW', 'ITW': 'RTW', 'KLAW': 'RTW', 'GRUKW': 'RTW',
           'CTLF': 'CTLF', 'ADL': 'ADL', 'ADL_OST': 'ADL', 'TLF14': 'TLF14', 'TLF15': 'TLF14', 'TLF94': 'TLF14',
           'GTLF16': 'GTLF16', 'WAWE': 'WAWE', 'A': 'NEF', 'B': 'RTW', 'C': 'ADL', 'D': 'GTLF16'}


def _lade_fahrzeugliste():
    import csv
    p = AKT_DIR / 'BORS_Fahrzeuge_V1.csv'
    out = {}
    if not p.is_file():
        return out
    with open(str(p), encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter=';'):
            v = {k: r[k] for k in r}
            for k in ('breite_karosserie_m', 'breite_spiegel_m', 'hoehe_m', 'laenge_m', 'gewicht_t'):
                v[k] = float(r[k])
            out[r['id']] = v
    return out


FAHRZEUGE = _lade_fahrzeugliste()
for _k in ('A', 'B', 'C', 'D'):
    _m = [v for v in FAHRZEUGE.values() if v['kategorie'] == _k]
    if _m:
        PROFILE[_k].update(width=max(v['breite_karosserie_m'] for v in _m), spiegel=max(v['breite_spiegel_m'] for v in _m),
                           height=max(v['hoehe_m'] for v in _m), tonnes=max(v['gewicht_t'] for v in _m))
for _id, _v in FAHRZEUGE.items():
    PROFILE[_id] = dict(kurz=_v['bezeichnung'], label='{} · {}'.format(_v['kategorie'], _v['bezeichnung']), width=_v['breite_karosserie_m'],
                        spiegel=_v['breite_spiegel_m'], height=_v['hoehe_m'], tonnes=_v['gewicht_t'], kategorie=_v['kategorie'],
                        laenge=_v['laenge_m'], fahrzeug=True)
MAX_SNAP_M = float(globals().get('BORS_MAX_SNAP_M', 30.0))
DIAG_SUCHE_M = 500.0
F4_ANZAHL = 400          # V9.2e: alle zulaessigen Anschlussabschnitte (hoechstens so viele) werden in EINER Suche geprueft,
F4_MAX_M = 150.0         # ... im Umkreis von hoechstens 150 m (weiter wird es keine 'Zufahrt' mehr)
MODEL_SPEED_KMH = {'motorway': 85, 'motorway_link': 35, 'trunk': 65, 'trunk_link': 35, 'primary': 45,
                   'primary_link': 30, 'secondary': 40, 'secondary_link': 25, 'tertiary': 35, 'tertiary_link': 20,
                   'unclassified': 25, 'residential': 25, 'living_street': 15, 'service': 12, 'road': 20}
EINSATZRECHT = True
SONDERRECHT_FAKTOR = 1.2
OEFFNEN_FAKTOR = 1.5
BAUSTELLE_FAKTOR = 1.5
REF_ZUBRINGER_FAKTOR = 5.0
OEFFNEN_SEK = 30.0
SERVICE_DURCHFAHRT_FAKTOR = 3.0
DOMINANZ = bool(globals().get('BORS_DOMINANZ', True))   # V7.6: leichteres Fahrzeug nie langsamer als schwereres
SERVICE_DURCHFAHRT = {'driveway', 'parking_aisle', 'drive-through'}
HGV_HINWEIS = {'no', 'destination', 'delivery', 'private', 'agricultural', 'forestry', 'permit', 'discouraged'}
LKW_AB_T = 3.5
POLLER_OEFFNBAR = {'removable', 'rising', 'foldable', 'flexible', 'collapsible', 'retractable'}
TOR_OEFFNBAR = {'gate', 'lift_gate', 'swing_gate', 'sliding_gate', 'chain', 'yes', 'barrier_board', 'rope'}
FEST = {'block', 'jersey_barrier', 'log', 'planter', 'debris', 'wall', 'fence', 'bar'}
KLICK_MALUS_TUNNEL_M = 25.0
KLICK_MALUS_AUTOBAHN_M = 10.0
WACHE_AREAL_M = 80.0
RISIKO_FAKTOR = float(globals().get('BORS_RISIKO_FAKTOR', 2.0))   # V9: Fahrzeit x2 auf unvalidierten Abschnitten (experimentell)
KAT_FAKTOR = {'KEIN_HINWEIS': 1.0, 'UNGEKLAERT': RISIKO_FAKTOR, 'VERDACHT_GRENZFALL': RISIKO_FAKTOR}
V9_KAT = {'VALIDIERT': 'KEIN_HINWEIS', 'UNVALIDIERT': 'UNGEKLAERT', 'GESPERRT': 'BESCHRAENKUNG_BESTAETIGT'}
NETZ_LAYER = 'BORS Netz V5 (Routing)'
NETZ_LAYER_V7 = 'BORS Netz V7 (Routing)'
ZEITPUNKT = globals().get('BORS_ZEITPUNKT') or datetime.now().strftime('%Y-%m-%dT%H:%M')
BAUSTELLEN_LAYER = 'BORS Baustellen Segmente'
OUT_DIR = P_ROUTEN
BAU_DIR = P_BAUSTELLEN
NETZ_V2_DIR = P_VORSTUFEN
GRUPPE = '00 ROUTE (aktuell)'
FARBE = {'KEIN_HINWEIS': '#1a9850', 'VERDACHT_GRENZFALL': '#e6a700', 'UNGEKLAERT': '#e6a700',
         'BESCHRAENKUNG_BESTAETIGT': '#d62728', 'REFERENZ': '#4d4d4d'}
KAT_TEXT = {'KEIN_HINWEIS': 'validiert', 'VERDACHT_GRENZFALL': 'unvalidiert', 'UNGEKLAERT': 'unvalidiert (nicht entscheidbar)',
            'BESCHRAENKUNG_BESTAETIGT': 'gesperrt (nachgewiesen)', 'REFERENZ': 'Referenz'}
URSACHE_TEXT = {
    'KEIN_NETZ_IN_ZIELNAEHE': 'Keine Strasse in Klicknähe',
    'NETZ_VORHANDEN_ABER_FUER_FAHRZEUG_AUSGESCHLOSSEN': 'Strasse vorhanden, aber für dieses Fahrzeug gesperrt',
    'EINBAHNRICHTUNG_VERHINDERT_VERBINDUNG': 'Nur gegen Einbahnrichtung erreichbar',
    'FAHRZEUGBESCHRAENKUNG_TRENNT': 'Beschränkungen (Höhe/Gewicht/Breite/Sperre) trennen Start und Ziel',
    'AUSSERHALB_UNTERSUCHUNGSGEBIET': 'Start/Ziel ausserhalb Untersuchungsgebiet (Randpuffer) – keine Aussage',
    'UNTERSCHIEDLICHE_NETZKOMPONENTEN': 'Start und Ziel liegen in getrennten Netzteilen',
    'TECHNISCHER_FEHLER': 'Technischer Fehler (Details im Protokoll)',
    'ZIEL_NICHT_ANFAHRBAR': 'Ziel für dieses Fahrzeug nicht anfahrbar – Route bis zum nächsten zulässigen Punkt',
    'ZIEL_ZU_FUSS': 'Halt an geeigneter Strasse vor dem Ziel – letzte Meter zu Fuss / mit Schlauch',
    'START_NICHT_ANFAHRBAR': 'Start liegt an einer für dieses Fahrzeug gesperrten Strasse – Route ab nächstem zulässigen Punkt'}
NUM = re.compile(r'^\s*(\d+(?:[\.,]\d+)?)\s*(m|t)?\s*$', re.I)
HGV_RE = re.compile(r'"hgv"\s*=>\s*"([^"]*)"')
TAG_RE = re.compile(r'"((?:[^"\\]|\\.)*)"=>"((?:[^"\\]|\\.)*)"')
SPEED_RE = re.compile(r'"maxspeed"\s*=>\s*"(\d+(?:\.\d+)?)"')


def _num(v):
    if v is None or str(v).strip() in ('', 'NULL'):
        return None
    m = NUM.fullmatch(str(v).strip())
    return float(m.group(1).replace(',', '.')) if m else None


def _speed(hw, tags):
    v = MODEL_SPEED_KMH.get(hw, 20)
    m = SPEED_RE.search(str(tags or ''))
    if m and 5 <= float(m.group(1)) <= 130:
        v = min(v, float(m.group(1)))
    return float(v)


def _s(v):
    return '' if v is None or str(v) == 'NULL' else str(v)


def lade_baustellen_datei(pfad, zeitpunkt):
    """Baustellen mit Zeitbezug aus dem GeoPackage von 5_Baustellen (sqlite, ohne GDAL).
    -> ({seg_id: (restbreite, text, bis, lagequelle, von)}, quelle)"""
    import sqlite3
    c = sqlite3.connect(str(pfad))
    mel = {}
    try:
        for sid, von, bis, lq in c.execute('select situation_id, von, bis, lage_quelle from meldungen'):
            mel[sid] = (von or '', bis or '', lq or '')
    except Exception:
        pass
    out = {}
    n_zeit = 0
    for seg, sit, bis, rb, txt in c.execute('select seg_id, situation_id, bis, restbreite_m, text from segmente'):
        von, bis2, lq = mel.get(sit, ('', bis or '', ''))
        bis = bis or bis2
        if (von and von[:16] > zeitpunkt) or (bis and bis[:16] < zeitpunkt):
            n_zeit += 1
            continue
        rb = _num(rb)
        lage = 'TMC-Abschnitt, Lage ungenau' if lq == 'TMC' else ('Polygon Stadt Bern' if lq == 'STADT_BERN_POLYGON' else ('Koordinaten' if lq else 'Lage unbekannt'))
        old = out.get(seg)
        if old is None or (rb is not None and (old[0] is None or rb < old[0])):
            out[seg] = (rb, _s(txt)[:160], (bis or '')[:16], lage, (von or '')[:16])
    c.close()
    return out, '{} (Zeitpunkt {}; {} Eintraege ausserhalb Gueltigkeit; Richtung nicht in Daten -> beide)'.format(
        Path(pfad).name, zeitpunkt, n_zeit)


def lade_hindernispunkte():
    """V7.5: OSM-Hindernispunkte (barrier) auf dem Routingnetz aus Documents\\BORS_Netz_V2\\*.gpkg (ohne GDAL)."""
    import sqlite3
    import struct
    out = []
    kand = sorted(NETZ_V2_DIR.glob('BORS_Netz_V2_*.gpkg'), key=lambda p: p.stat().st_mtime, reverse=True) if NETZ_V2_DIR.exists() else []
    for p in kand:
        try:
            c = sqlite3.connect('file:{}?mode=ro'.format(p.as_posix()), uri=True)
            if not c.execute("select count(*) from sqlite_master where name='osm_hindernispunkte'").fetchone()[0]:
                c.close()
                continue
            for g, b, acc, em, sid, ot in c.execute('select geom, barrier, access, emergency, naechstes_seg_id, other_tags '
                                                    'from osm_hindernispunkte where auf_routingnetz = 1'):
                bb = bytes(g)
                o = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(bb[3] >> 1) & 7]
                bo = '<' if bb[o] == 1 else '>'
                x, y = struct.unpack(bo + 'dd', bb[o + 5:o + 21])
                out.append(dict(x=x, y=y, barrier=_s(b).lower(), access=_s(acc).lower(), emergency=_s(em).lower(),
                                seg_id=_s(sid), tags=dict(TAG_RE.findall(_s(ot)))))
            c.close()
            if out:
                return out
        except Exception:
            continue
    return out


def lade_poller(pfad):
    """Gesteuerte Poller der Stadt Bern (Tabelle stadt_poller aus 16_Stadt_Bern_Live.py) -> {seg_id: [(name, regel, dauersperre)]}"""
    import sqlite3
    out = {}
    try:
        c = sqlite3.connect(str(pfad))
        for name, regel, sid, ds, x, y in c.execute("select name, regel, seg_id, dauersperre, x, y from stadt_poller where seg_id <> ''"):
            out.setdefault(sid, []).append((name or '', regel or '', int(ds or 0), x, y))
        c.close()
    except Exception:
        pass
    return out


def evidenz_vorhanden(pfad):
    import sqlite3
    try:
        c = sqlite3.connect(str(pfad))
        ok = c.execute("select count(*) from sqlite_master where name='evidenz'").fetchone()[0] == 1
        c.close()
        return ok
    except Exception:
        return False


def lies_evidenz(pfad, code, seg_ids):
    import sqlite3
    c = sqlite3.connect(str(pfad))
    c.row_factory = sqlite3.Row
    out = []
    tab = 'evidenz_voll' if c.execute("select count(*) from sqlite_master where name='evidenz_voll'").fetchone()[0] else 'evidenz'
    ids = list(dict.fromkeys(seg_ids))
    for i in range(0, len(ids), 400):
        teil = ids[i:i + 400]
        q = 'select * from {} where profil = ? and seg_id in ({})'.format(tab, ','.join('?' * len(teil)))
        out += [dict(r) for r in c.execute(q, [code] + teil)]
    c.close()
    return out


def adresssuche(text, n=8):
    """Amtliches Gebaeudeadressverzeichnis ueber api3.geo.admin.ch (SearchServer, LV95). -> [(label, E, N)]"""
    import json
    import re as _re
    import urllib.parse
    import urllib.request
    url = ('https://api3.geo.admin.ch/rest/services/api/SearchServer?searchText={}&type=locations&origins=address'
           '&sr=2056&limit={}').format(urllib.parse.quote(text), n)
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'BFH-BCS-BORS'}), timeout=15) as r:
        d = json.loads(r.read().decode('utf-8'))
    out = []
    for it in d.get('results', []):
        a = it.get('attrs', {})
        e, nn = a.get('y'), a.get('x')                       # geo.admin: y = Ost (2'6xx'xxx), x = Nord (1'2xx'xxx)
        if e is None or nn is None:
            continue
        if e < nn:
            e, nn = nn, e
        out.append((_re.sub('<[^>]+>', '', a.get('label', '')), float(e), float(nn)))
    return out


def lade_wachen():
    """BORS_Wachen.csv (name;adresse;x;y) -> [(name, adresse, x|None, y|None)]"""
    import csv
    p = AKT_DIR / 'BORS_Wachen.csv'
    out = []
    if p.is_file():
        with open(str(p), encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter=';'):
                x = float(r['x']) if r.get('x') else None; y = float(r['y']) if r.get('y') else None
                out.append((r['name'], r['adresse'], x, y))
    return out


class BorsRouterV7:
    def __init__(self):
        self.prj = QgsProject.instance()
        self.canvas = iface.mapCanvas()
        if self.prj.crs().authid() != 'EPSG:2056':
            raise RuntimeError('Projekt-KBS muss EPSG:2056 sein.')
        cand = [l for l in self.prj.mapLayers().values() if l.name() == NETZ_LAYER_V7 and isinstance(l, QgsVectorLayer)]
        if not cand:
            cand = [l for l in self.prj.mapLayers().values() if l.name() == NETZ_LAYER and isinstance(l, QgsVectorLayer)]
        if len(cand) != 1:
            raise RuntimeError('Genau EIN Layer "{}" oder "{}" muss im Projekt sein (gefunden: {}).'.format(NETZ_LAYER_V7, NETZ_LAYER, len(cand)))
        self.src = cand[0]
        self.src_pfad = self.src.source().split('|')[0]
        self.netz_version = Path(self.src.source().split('|')[0]).name
        self.flds = set(self.src.fields().names())
        self._lade_baustellen()
        self._lade_netz()
        self.points = []
        self.busy = False
        self.code = 'C'
        self.letzte = {}
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        self._ui()
        self.tool = QgsMapToolEmitPoint(self.canvas)
        self.tool.canvasClicked.connect(self._klick)
        self._log('Netz: {} | {} Segmente im Graph | {} Knoten | Baustellen aktiv am {}: {} ({}) | Stadt-Poller: {} | Hindernispunkte: {} | Abbiegen: {} | Fahrzeuge: {} | Belege: {}'.format(
            self.netz_version, len(self.kern.feat), len(self.kern.xy), ZEITPUNKT, len(self.baustellen), self.bau_quelle, len(self.poller), getattr(self, 'punkte_stat', {}), self.abbiegen_quelle, len(FAHRZEUGE),
            'ja (Netzmaster V7)' if self.hat_evidenz else 'nein (nur V5-Netz geladen)'))

    # ------------------------------------------------------------------ Daten
    def _lade_baustellen(self):
        self.baustellen = {}
        self.poller = {}
        dateien = sorted(BAU_DIR.glob('baustellen_*.gpkg'))
        if dateien:
            self.baustellen, self.bau_quelle = lade_baustellen_datei(dateien[-1], ZEITPUNKT)
            self.poller = lade_poller(dateien[-1])
            return
        self.bau_quelle = 'Layer ' + BAUSTELLEN_LAYER
        for l in self.prj.mapLayers().values():
            if l.name() != BAUSTELLEN_LAYER:
                continue
            for bf in l.getFeatures():
                if bf['aktiv'] != 1:
                    continue
                rb = _num(bf['restbreite_m'])
                old = self.baustellen.get(bf['seg_id'])
                if old is None or (rb is not None and (old[0] is None or rb < old[0])):
                    self.baustellen[bf['seg_id']] = (rb, _s(bf['text'])[:160], _s(bf['bis'])[:10])

    def _lade_netz(self):
        self.kern = RoutingKern()
        self.info = {}
        self.sidx = QgsSpatialIndex(flags=QgsSpatialIndex.Flag.FlagStoreFeatureGeometries)
        self.global_aus = Counter()
        for f in self.src.getFeatures():
            hw = _s(f['highway_type']).lower()
            if hw not in ROAD_TYPES:
                self.global_aus['kein Fahrweg-Typ'] += 1
                continue
            g = f.geometry()
            if g.isNull() or g.isEmpty():
                continue
            parts = [[(p.x(), p.y()) for p in part] for part in (g.asMultiPolyline() if g.isMultipart() else [g.asPolyline()])]
            parts = [p for p in parts if len(p) >= 2]
            if not parts:
                continue
            d = _s(f['direction_osm']) or 'BOTH'
            if d not in ('BOTH', 'FORWARD', 'BACKWARD'):
                d = 'BOTH'
            self.kern.add_feature(f.id(), parts, d)
            self.sidx.addFeature(f)
            a = {k: f[k] for k in ('seg_id', 'name', 'access_class', 'maxwidth', 'maxheight', 'maxweight')}
            if 'zugang_v7' in self.flds and _s(f['zugang_v7']):
                a['access_class'] = _s(f['zugang_v7'])
                a['hinweis_zugang_v7'] = _s(f['zugang_v7_grund'])
            a['hw'] = hw
            a['speed'] = _speed(hw, f['other_tags'])
            a['hinweis_zugang'] = _s(f['bors_zugang_hinweis']) if 'bors_zugang_hinweis' in self.flds else ''
            a['oeffnen'] = int(f['hindernis_oeffnen'] or 0) if 'hindernis_oeffnen' in self.flds else 0
            a['hindernisse'] = _s(f['hindernisse']) if 'hindernisse' in self.flds else ''
            a['btl'] = _s(f['bruecke_tunnel_layer']) if 'bruecke_tunnel_layer' in self.flds else ''
            a['service'] = _s(f['service_type']).lower() if 'service_type' in self.flds else ''
            a['gemeinde'] = _s(f['gemeinde']) if 'gemeinde' in self.flds else ''     # V9.2f: fuer Randtest in der Diagnose
            mh = HGV_RE.search(_s(f['other_tags']))
            a['hgv'] = mh.group(1).lower() if mh else ''
            for c in 'abcd':
                if c + '_v9_status' in self.flds:
                    a[c + '_kat'] = V9_KAT.get(_s(f[c + '_v9_status']), 'UNGEKLAERT')
                    a[c + '_grund'] = _s(f[c + '_v9_grund'])
                    a[c + '_breite'] = '{} ({})'.format(_s(f[c + '_breite_v9']), _s(f[c + '_breite_v9_beleg']))
                    a[c + '_offen'] = ''; a[c + '_stufe'] = ''
                    continue
                kf = c + '_kat_v8' if c + '_kat_v8' in self.flds else (c + '_kat_v7' if c + '_kat_v7' in self.flds else c + '_kat')
                a[c + '_kat'] = _s(f[kf]) if kf in self.flds else 'UNGEKLAERT'
                a[c + '_grund'] = _s(f[c + '_kat_v8_grund']) if c + '_kat_v8_grund' in self.flds else (_s(f[c + '_grund']) if c + '_grund' in self.flds else '')
                if c + '_kat_v7_grund' in self.flds and _s(f[c + '_kat_v7_grund']).startswith('R'):
                    a[c + '_grund'] = _s(f[c + '_kat_v7_grund']) + ' | ' + a[c + '_grund']
                a[c + '_offen'] = _s(f[c + '_offen']) if c + '_offen' in self.flds else ''
                a[c + '_stufe'] = _s(f[c + '_stufe']) if c + '_stufe' in self.flds else ''
            self.info[f.id()] = a
        self.hat_evidenz = evidenz_vorhanden(self.src_pfad)
        sid2fid = {a['seg_id']: f for f, a in self.info.items()}
        for sid, lst in getattr(self, 'poller', {}).items():
            a = self.info.get(sid2fid.get(sid))
            if a is None:
                continue
            if not all(len(p) > 4 and p[3] is not None for p in lst):
                a['oeffnen'] += 1                       # nur ohne Koordinaten: Faktor auf den Abschnitt (V7.5)
            a['hindernisse'] = ('; '.join(x for x in [a['hindernisse']] + ['Stadt Bern Poller {} ({})'.format(p[0], p[1]) for p in lst] if x))[:250]
            if any(p[2] for p in lst) and _s(a['access_class']).upper() != 'RESTRICTED':
                a['access_class'] = 'RESTRICTED'
                a['hinweis_zugang_v7'] = 'Stadt Bern Polleranlage: Dauersperre'
        self._lade_punkte(sid2fid)
        self.sid2fid = sid2fid
        self.kosten = {}
        self.aus = {}
        self.fz_geladen = set()
        self._lade_abbiegen()

    def _lade_fahrzeug_kat(self, code):
        """V8: Kategorie je Abschnitt fuer ein Einzelfahrzeug aus Tabelle fahrzeug_kat_v8 -> info[fid][code.lower()+'_kat']."""
        if code in self.fz_geladen or code not in FAHRZEUGE:
            return
        import sqlite3
        k, g = code.lower() + '_kat', code.lower() + '_grund'
        cat = FAHRZEUGE[code]['kategorie'].lower()
        for a in self.info.values():
            a[k] = a[cat + '_kat']; a[g] = a[cat + '_grund']          # Fallback: Kategorie
        try:
            c = sqlite3.connect('file:{}?mode=ro'.format(Path(self.src_pfad).as_posix()), uri=True)
            n = 0
            for sid, kat, grund in c.execute('select seg_id, kategorie, grund from fahrzeug_kat_v8 where fahrzeug = ?', (code,)):
                fid = self.sid2fid.get(sid)
                if fid is not None:
                    self.info[fid][k] = kat; self.info[fid][g] = grund or ''; n += 1
            c.close()
            self._log('Fahrzeug {}: Bewertung fuer {} Abschnitte aus fahrzeug_kat_v8 geladen'.format(code, n))
        except Exception as ex:
            self._log('Fahrzeug {}: keine Einzelbewertung im Netzmaster ({}) -> Kategorie {} verwendet'.format(code, ex, cat.upper()))
        self.fz_geladen.add(code)

    def _lade_abbiegen(self):
        """V8: Schleppkurven-Ergebnisse (22_Abbiegen_Schleppkurven.py) -> je Abbiege-Fahrzeug Strafzeiten."""
        import sqlite3
        self.abbiegen_roh = []
        self.abbiegen = {}
        self.abbiegen_quelle = 'keine'
        d = Path(self.src_pfad).parent
        dateien = sorted(d.glob('BORS_Abbiegen_V8_*.gpkg'), key=lambda p: p.stat().st_mtime)
        if not dateien:
            return
        try:
            c = sqlite3.connect('file:{}?mode=ro'.format(dateien[-1].as_posix()), uri=True)
            cols = [r[1] for r in c.execute('pragma table_info(abbiegen_v8)')]
            for row in c.execute('select * from abbiegen_v8'):
                self.abbiegen_roh.append(dict(zip(cols, row)))
            c.close()
            self.abbiegen_quelle = dateien[-1].name
        except Exception as ex:
            self.abbiegen_quelle = 'Fehler: {}'.format(ex)

    def _abbiege_tabelle(self, code):
        """-> {'turn': {(knoten, fid_in, fid_out): sek}, 'kurve': {(fid, 'fw'|'bw'): sek}} fuer Profil code."""
        if code in self.abbiegen:
            return self.abbiegen[code]
        tab = {'turn': {}, 'kurve': {}, 'text': {}}
        tf = TURN_FZ.get(code)
        if code == 'REF':
            tf = 'NEF'
        if tf and self.abbiegen_roh:
            schwer = PROFILE.get(code, {}).get('tonnes', 2.0) > LKW_AB_T
            import struct as _st
            for r in self.abbiegen_roh:
                st = r.get('s_' + tf) or ''
                sek = ABBIEGE_SEK.get(st)
                if st == 'SPITZKEHRE':
                    sek = 240.0 if schwer else 60.0
                if not sek:
                    continue
                f1, f2 = self.sid2fid.get(r['in_seg']), self.sid2fid.get(r['out_seg'])
                if f1 is None or f2 is None:
                    continue
                g = bytes(r['geom']); o = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(g[3] >> 1) & 7]
                x, y = _st.unpack('<dd' if g[o] == 1 else '>dd', g[o + 5:o + 21])
                if r['art'] == 'KURVE':
                    tab['kurve'][(f1, 'fw' if r['in_ende'] == 'mitte' else 'bw')] = sek
                    tab['text'][('K', f1)] = '{} Kurve ({:.0f} Grad): {}'.format(r.get('strasse_in') or r['in_seg'], abs(r['winkel'] or 0), st)
                    continue
                kn = self.kern.nodes.get((round(x, 2), round(y, 2)))
                if kn is None:
                    continue
                tab['turn'][(kn, f1, f2)] = sek
                tab['text'][(kn, f1, f2)] = '{} -> {} ({:.0f} Grad): {}'.format(r.get('strasse_in') or r['in_seg'], r.get('strasse_out') or r['out_seg'],
                                                                             abs(r['winkel'] or 0), st)
        self.abbiegen[code] = tab
        return tab

    def _lade_punkte(self, sid2fid):
        """V7.5: Hindernis-PUNKTE. self.punkte[fid] = [(part, pos, 'FEST'|'OEFFNEN', text)]."""
        self.punkte = {}
        n = Counter()

        def add(sid, x, y, art, txt):
            fid = sid2fid.get(sid)
            if fid is None or fid not in self.kern.feat:
                n['ohne Segment'] += 1
                return
            sn = self.kern.project(fid, x, y)
            if sn is None or sn[0] > 3.0:
                n['zu weit vom Segment'] += 1
                return
            self.punkte.setdefault(fid, []).append((sn[1], sn[3], art, txt))
            n[art] += 1
        for h in lade_hindernispunkte():
            b, t = h['barrier'], h['tags']
            if h['emergency'] in ('yes', 'designated') or h['access'] in ('yes', 'emergency'):
                continue
            if b == 'bollard':
                typ = (t.get('bollard') or '').lower()
                art = 'FEST' if typ == 'fixed' else ('OEFFNEN' if typ in POLLER_OEFFNBAR else None)
            elif b in FEST:
                art = 'FEST'
            elif b in TOR_OEFFNBAR:
                art = 'OEFFNEN'
            else:
                art = None
            if art:
                add(h['seg_id'], h['x'], h['y'], art, '{} {}'.format(b, t.get('bollard', '')).strip())
        for sid, lst in getattr(self, 'poller', {}).items():
            for p in lst:
                if len(p) > 4 and p[3] is not None and not p[2]:
                    add(sid, p[3], p[4], 'OEFFNEN', 'Stadt Bern Poller ' + p[0])
        self.punkte_stat = dict(n)
        # Abschnitte, deren Kat. 3 NUR von einer festen Sperre kommt -> Kategorie ohne Hindernis aus den Belegen
        self.kat_ohne_hindernis = {}
        kand = [fid for fid, pl in self.punkte.items() if any(p[2] == 'FEST' for p in pl)]
        if kand and getattr(self, 'hat_evidenz', False):
            S = {'KEIN_HINWEIS': 0, 'UNGEKLAERT': 1, 'VERDACHT_GRENZFALL': 2, 'BESCHRAENKUNG_BESTAETIGT': 3}
            inv = {v: k for k, v in S.items()}
            for code in 'ABCD':
                worst = {}
                for e in lies_evidenz(self.src_pfad, code, [self.info[f]['seg_id'] for f in kand]):
                    if e.get('kriterium') in ('hindernis', 'zugang') or e.get('entscheidung') not in S:
                        continue
                    sid = e['seg_id']
                    worst[sid] = max(worst.get(sid, 0), S[e['entscheidung']])
                for f in kand:
                    sid = self.info[f]['seg_id']
                    self.kat_ohne_hindernis[(f, code)] = inv[worst[sid]] if sid in worst else 'UNGEKLAERT'

    def _nur_feste_sperre(self, fid, code):
        a = self.info[fid]
        g = a[code.lower() + '_grund']
        if not g.startswith('Hindernis:') or ' | ' in g:
            return False
        teile = [x.strip() for x in g[len('Hindernis:'):].split(';')]
        return all(('fest' in x) or ('oeffnen' in x) or ('Einsatz frei' in x) for x in teile) and \
            any(p[2] == 'FEST' for p in self.punkte.get(fid, []))

    def _punkte_fuer(self, code, kosten):
        """fid -> [(part, pos, sek|None)] fuer den Routing-Kern."""
        out = {}
        for fid, pl in self.punkte.items():
            if fid not in kosten:
                continue
            lst = []
            for pi, pos, art, txt in pl:
                if art == 'FEST':
                    lst.append((pi, pos, None))
                elif code != 'REF':
                    lst.append((pi, pos, OEFFNEN_SEK))
            if lst:
                out[fid] = lst
        return out

    def _profil_kosten(self, code):
        """-> (fid -> Sekunden/Meter, fid -> Kostengrund) und Ausschlussgruende je fid."""
        if code in self.kosten:
            return self.kosten[code]
        self._wachen_areal()
        self._lade_fahrzeug_kat(code)
        k, grund, aus = {}, {}, {}
        for fid, a in self.info.items():
            fak, why = 1.0, []
            if a.get('service') in SERVICE_DURCHFAHRT:
                fak *= SERVICE_DURCHFAHRT_FAKTOR
                why.append('Zufahrt/Parkplatz ({}) als Durchfahrt x{}'.format(a['service'], SERVICE_DURCHFAHRT_FAKTOR))
            if _s(a['access_class']).upper() == 'RESTRICTED':
                hz = (_s(a.get('hinweis_zugang_v7')) + ' ' + _s(a.get('hinweis_zugang'))).upper()
                if code == 'REF' and ('ZUBRINGER' in hz or 'DESTINATION' in hz or 'DELIVERY' in hz):
                    k[fid] = fak * REF_ZUBRINGER_FAKTOR / (a['speed'] / 3.6)       # V7.4: Zubringer fuer normales Auto erlaubt
                    grund[fid] = '; '.join(why + ['Zubringer/Anlieger x{} (nur Anfang/Ende)'.format(REF_ZUBRINGER_FAKTOR)])
                    continue
                if code == 'REF' or not EINSATZRECHT:
                    aus[fid] = 'Zufahrt eingeschraenkt (ohne Sonderrecht)'
                    continue
                fak *= SONDERRECHT_FAKTOR; why.append('Sonderrecht x{}'.format(SONDERRECHT_FAKTOR))
            elif code != 'REF' and PROFILE[code]['tonnes'] > LKW_AB_T and a.get('hgv') in HGV_HINWEIS:
                fak *= SONDERRECHT_FAKTOR
                why.append('LKW-Fahrverbot/Zubringer (hgv={}) -> Sonderrecht x{}'.format(a['hgv'], SONDERRECHT_FAKTOR))
            if code != 'REF':
                pr = PROFILE[code]
                stop = None
                for tag, attr, txt in (('maxwidth', 'width', 'OSM maxwidth'), ('maxheight', 'height', 'OSM maxheight'),
                                       ('maxweight', 'tonnes', 'OSM maxweight')):
                    lim = _num(a[tag])
                    if lim is not None and pr[attr] > lim + 1e-9:
                        stop = '{} {} < {}'.format(txt, lim, pr[attr]); break
                kat = a[code.lower() + '_kat'] or 'UNGEKLAERT'
                if stop is None and kat == 'BESCHRAENKUNG_BESTAETIGT' and self._nur_feste_sperre(fid, code):
                    kat = self.kat_ohne_hindernis.get((fid, code), 'UNGEKLAERT')     # V7.5: nur der Punkt ist gesperrt
                    why.append('feste Sperre: nur Durchgang am Punkt gesperrt')
                if stop is None and kat == 'BESCHRAENKUNG_BESTAETIGT':
                    stop = 'Kat. 3: ' + a[code.lower() + '_grund'][:120]
                if stop:
                    aus[fid] = stop
                    continue
                if getattr(self, 'modus', 'VALIDIERT') == 'VALIDIERT' and kat != 'KEIN_HINWEIS':
                    aus[fid] = 'nicht validiert: ' + (a[code.lower() + '_grund'] or kat)[:120]
                    continue
                kf = KAT_FAKTOR.get(kat, KAT_FAKTOR['UNGEKLAERT'])
                if kf != 1.0:
                    fak *= kf; why.append('{} x{}'.format(kat, kf))
                if a['oeffnen'] > 0 and not any(p[2] == 'OEFFNEN' for p in self.punkte.get(fid, [])):
                    fak *= OEFFNEN_FAKTOR; why.append('Tor/Poller oeffnen x{} (Oeffnung nicht garantiert)'.format(OEFFNEN_FAKTOR))
                b = self.baustellen.get(a['seg_id'])
                if b is not None:
                    bedarf = pr['width'] + 2 * SIDE_RESERVE_M
                    lage = b[3] if len(b) > 3 else ''
                    if b[0] is not None and b[0] < bedarf:
                        fak *= KAT_FAKTOR['VERDACHT_GRENZFALL']; why.append('Baustelle Restbreite {:.1f} m x{} [{} bis {}]'.format(b[0], KAT_FAKTOR['VERDACHT_GRENZFALL'], lage, b[2]))
                    else:
                        fak *= BAUSTELLE_FAKTOR; why.append('Baustelle x{} [{} bis {}]'.format(BAUSTELLE_FAKTOR, lage, b[2]))
            k[fid] = fak / (a['speed'] / 3.6)
            grund[fid] = '; '.join(why)
        self.kosten[code] = (k, grund)
        self.aus[code] = aus
        return self.kosten[code]

    # ------------------------------------------------------------------ Routing + Diagnose
    def _naechste(self, pt, erlaubt):
        """-> (naechste Strasse, naechste zulaessige) je als (abstand, fid, snap) oder None."""
        any_, ok_ = None, None
        for fid in self.sidx.nearestNeighbor(QgsPointXY(pt[0], pt[1]), 80, DIAG_SUCHE_M):
            if fid not in self.kern.feat:
                continue
            sn = self.kern.project(fid, pt[0], pt[1])
            if sn is None:
                continue
            m = sn[0] + self._klick_malus(fid)
            if any_ is None or m < any_[3]:
                any_ = (sn[0], fid, sn, m)
            if fid in erlaubt and (ok_ is None or m < ok_[3]):
                ok_ = (sn[0], fid, sn, m)
        return (any_[:3] if any_ else None), (ok_[:3] if ok_ else None)

    def _anschluesse(self, pt, erlaubt):
        """V9.2e: alle zulaessigen Anschluesse bis F4_MAX_M um den Bezugspunkt -> [(fid, snap, zuschlag_s)].
        Zuschlag = (Luftlinie + Klickmalus) x RESTWEG_SEK_PRO_M. Weiter weg gibt es keinen Ersatzanschluss mehr
        (vorher galt beim nicht anfahrbaren Start/Ziel der naechste zulaessige Abschnitt bis DIAG_SUCHE_M)."""
        out = []
        for fid in self.sidx.nearestNeighbor(QgsPointXY(pt[0], pt[1]), F4_ANZAHL, F4_MAX_M):
            if fid not in self.kern.feat or fid not in erlaubt:
                continue
            sn = self.kern.project(fid, pt[0], pt[1])
            if sn is None or sn[0] > F4_MAX_M:
                continue
            out.append((fid, sn, (sn[0] + self._klick_malus(fid)) * RESTWEG_SEK_PRO_M))
        return out

    def _klick_malus(self, fid):
        """V7.4: Klick soll nicht in einen Tunnel/auf die Autobahn unter bzw. neben der gemeinten Strasse springen."""
        a = self.info.get(fid, {})
        btl = (a.get('btl') or '').lower()
        m = 0.0
        if 'tunnel' in btl or 'layer=-' in btl:
            m += KLICK_MALUS_TUNNEL_M
        if a.get('hw') in ('motorway', 'motorway_link', 'trunk', 'trunk_link'):
            m += KLICK_MALUS_AUTOBAHN_M
        return m

    def _wachen_areal(self):
        """V9.1: Zufahrten/Hofflaechen (service) bis WACHE_AREAL_M um die Wachen aus BORS_Wachen.csv. Positive betriebliche
        Evidenz: die Fahrzeuge sind dort stationiert. Gilt nur fuer UNVALIDIERT, nie fuer nachweislich gesperrte Abschnitte."""
        if getattr(self, '_wa', None) is not None:
            return self._wa
        self._wa = set()
        for name, adr, x, y in lade_wachen():
            if x is None:
                continue
            for fid, a in self.info.items():
                if a.get('hw') != 'service' or fid not in self.kern.feat:
                    continue
                sn = self.kern.project(fid, x, y)
                if sn is not None and sn[0] <= WACHE_AREAL_M:
                    self._wa.add(fid)
        for fid in self._wa:
            a = self.info[fid]
            for c in 'abcd':
                if a.get(c + '_kat') == 'UNGEKLAERT':
                    a[c + '_kat'] = 'KEIN_HINWEIS'
                    a[c + '_grund'] = 'Wachenareal (Fahrzeuge dort stationiert, taeglich befahren) | vorher: ' + (a.get(c + '_grund') or '')[:150]
        return self._wa

    def _setze_modus(self, m):
        if getattr(self, 'modus', None) != m:
            self.modus = m
            self.kosten = {}
            self.aus = {}

    def berechne(self, p1, p2, codes):
        """V9: zuerst VALIDIERT; Profile ohne validierte Route zusaetzlich EXPERIMENTELL (deutlich gekennzeichnet)."""
        wahl = getattr(self, 'modus_ui', 'VALIDIERT')
        self._setze_modus(wahl)
        res = self._berechne_modus(p1, p2, codes)
        for c in codes:
            res[c]['modus'] = wahl
        if wahl == 'VALIDIERT':
            fehl = [c for c in codes if c != 'REF' and not res[c]['ok']
                    and res[c].get('ursache') not in ('KEIN_NETZ_IN_STARTNAEHE', 'KEIN_NETZ_IN_ZIELNAEHE', 'AUSSERHALB_UNTERSUCHUNGSGEBIET')]
            if fehl:
                self._setze_modus('EXPERIMENTELL')
                rx = self._berechne_modus(p1, p2, codes)
                for c in fehl:
                    alt = res[c]
                    res[c] = rx[c]
                    res[c]['modus'] = 'EXPERIMENTELL'
                    res[c]['validiert_ergebnis'] = '{}: {}'.format(alt.get('ursache') or 'ok', (alt.get('text') or '')[:160])
                    # V9.1: unvalidiert nur am Anfang/Ende (Zufahrt/Ausfahrt), dazwischen alles validiert
                    rr = res[c].get('rows') or []
                    ok_i = [i for i, x in enumerate(rr) if x['kategorie'] == 'KEIN_HINWEIS']
                    if rr and ok_i and all(rr[i]['kategorie'] == 'KEIN_HINWEIS' for i in range(ok_i[0], ok_i[-1] + 1)):
                        a_m = sum(x['laenge_m'] for x in rr[:ok_i[0]]); z_m = sum(x['laenge_m'] for x in rr[ok_i[-1] + 1:])
                        res[c]['modus'] = 'VALIDIERT_BIS_ZUFAHRT'
                        res[c]['zufahrt_m'] = round(a_m + z_m, 1)
                        res[c]['zufahrt_text'] = 'Route validiert bis auf die Zufahrt: {}{}nicht nachgewiesen (Zufahrt vor Ort pruefen / zu Fuss).'.format(
                            'erste {:.0f} m '.format(a_m) if a_m else '', ('und ' if a_m and z_m else '') + ('letzte {:.0f} m '.format(z_m) if z_m else ''))
                self._setze_modus('VALIDIERT')
        for c in codes:
            r = res[c]
            if c != 'REF' and r.get('ok') and r.get('modus') == 'VALIDIERT' and r.get('ursache') in ('ZIEL_NICHT_ANFAHRBAR', 'START_NICHT_ANFAHRBAR'):
                # V9.1: Start/Ziel an nicht validierter Strasse -> validierte Route ab/bis naechstem validierten Punkt; die Zufahrt
                # dazwischen ist NICHT nachgewiesen und wird ausgewiesen (Luftlinie).
                d = r.get('diag', {})
                zs = d.get('start_restdistanz_luftlinie_m') or 0; zz = d.get('ziel_restdistanz_luftlinie_m') or 0
                r['modus'] = 'VALIDIERT_BIS_ZUFAHRT'
                r['zufahrt_m'] = round(zs + zz, 1)
                r['zufahrt_text'] = 'Validierte Route {}{}. Zufahrt dazwischen nicht nachgewiesen ({}).'.format(
                    'ab {:.0f} m vom Start'.format(zs) if zs else '', (' bis {:.0f} m vor dem Ziel'.format(zz)) if zz else '',
                    (d.get('ziel_gesperrt_grund') or d.get('start_gesperrt_grund') or '')[:120])
        for c in codes:
            r = res[c]
            if r.get('ok') and c != 'REF':
                r['unvalidiert_m'] = sum(x['laenge_m'] for x in r['rows'] if x['kategorie'] != 'KEIN_HINWEIS')
        return res

    def _berechne_modus(self, p1, p2, codes):
        reihe = ['A', 'B', 'C', 'D']
        alle = list(codes)
        if DOMINANZ:
            for c in codes:
                if c in reihe:
                    alle += [h for h in reihe[reihe.index(c) + 1:] if h not in alle]
        res = {}
        for code in alle:
            try:
                res[code] = self._route_profil(code, p1, p2)
            except Exception as ex:
                res[code] = dict(code=code, ok=False, ursache='TECHNISCHER_FEHLER', text='{}: {}'.format(type(ex).__name__, ex),
                                 diag={})
        if DOMINANZ:
            for i, x in enumerate(reihe):
                rx = res.get(x)
                if not rx or not rx['ok'] or rx.get('ursache'):
                    continue
                for y in reihe[i + 1:]:
                    ry = res.get(y)
                    if ry and ry['ok'] and not ry.get('ursache') and ry.get('dominanz_von') is None and \
                            ry['fahrzeit_min'] < rx['fahrzeit_min'] - 0.05:
                        rx = res[x] = self._uebernehme(x, ry, rx)
        return {c: res[c] for c in codes}

    def _uebernehme(self, x, ry, rx_alt):
        """V7.6 Dominanz: Route des schwereren Fahrzeugs ist fuer das leichtere zulaessig und schneller -> uebernehmen."""
        kx, gx = self._profil_kosten(x)
        rows = []
        for r in ry['rows']:
            f = r['_fid']; info = self.info[f]
            n = dict(r)
            kat = info[x.lower() + '_kat'] or 'UNGEKLAERT'
            if kat == 'BESCHRAENKUNG_BESTAETIGT' and self._nur_feste_sperre(f, x):
                kat = self.kat_ohne_hindernis.get((f, x), 'UNGEKLAERT')
            n.update(profil=x, kategorie=kat, grund=info[x.lower() + '_grund'],
                     zusatzkosten_s=round(r['laenge_m'] * kx.get(f, 0) - r['grundkosten_s'], 2),
                     kostengrund='; '.join(t for t in [gx.get(f, ''), 'Route von {} uebernommen'.format(ry['code'])] if t))
            rows.append(n)
        out = dict(ry)
        out.update(code=x, rows=rows, modell_min=sum(r['laenge_m'] * kx.get(r['_fid'], 0) for r in rows) / 60.0,
                   kat_m=dict(sum((Counter({r['kategorie']: r['laenge_m']}) for r in rows), Counter())),
                   dominanz_von=ry['code'],
                   dominanz_text='{} uebernimmt die Route von {}: dort fuer {} zulaessig und {:.1f} min schneller als die eigene vorsichtigere '
                                 'Route ({:.0f} m). Verdacht-Abschnitte stehen in der Liste.'.format(
                                     x, ry['code'], ry['code'], rx_alt['fahrzeit_min'] - ry['fahrzeit_min'], rx_alt['laenge_m']))
        out['belege'] = self._belege(x, rows)
        return out

    def _route_profil(self, code, p1, p2):
        kosten, grund = self._profil_kosten(code)
        diag = {}
        snaps, ersatz, bezug = [], [], []
        for name, p in (('start', p1), ('ziel', p2)):
            any_, ok_ = self._naechste(p, kosten)
            diag[name + '_naechste_strasse_m'] = round(any_[0], 1) if any_ else None
            diag[name + '_naechste_strasse_seg'] = self.info[any_[1]]['seg_id'] if any_ else None
            diag[name + '_naechste_zulaessig_m'] = round(ok_[0], 1) if ok_ else None
            diag[name + '_naechste_zulaessig_seg'] = self.info[ok_[1]]['seg_id'] if ok_ else None
            gesperrt_naeher = (any_ is not None and ok_ is not None and any_[1] not in kosten and ok_[0] - any_[0] > 5.0)
            if any_ is not None and any_[0] <= MAX_SNAP_M and ok_ is not None and (ok_[0] > MAX_SNAP_M or gesperrt_naeher):
                # Klick ist am Netz, aber die Strasse ist fuer das Fahrzeug gesperrt -> Alternativpunkt (nicht ueberbrueckt)
                diag[name + '_status'] = ('ZIEL' if name == 'ziel' else 'START') + '_NICHT_ANFAHRBAR'
                diag[name + '_gesperrt_seg'] = self.info[any_[1]]['seg_id']
                diag[name + '_gesperrt_grund'] = self.aus.get(code, {}).get(any_[1], '?')
                diag[name + '_alternativ_x'], diag[name + '_alternativ_y'] = round(ok_[2][4], 2), round(ok_[2][5], 2)
                diag[name + '_restdistanz_luftlinie_m'] = round(math.hypot(ok_[2][4] - any_[2][4], ok_[2][5] - any_[2][5]), 1)
                snaps.append(ok_); ersatz.append(True); bezug.append((any_[2][4], any_[2][5]))
                continue
            if ok_ is None or ok_[0] > MAX_SNAP_M:
                if any_ is None or any_[0] > MAX_SNAP_M:
                    u = 'KEIN_NETZ_IN_ZIELNAEHE'
                    t = '{}: naechste Strasse {} m entfernt (max. {:.0f} m)'.format(
                        name.capitalize(), '{:.0f}'.format(any_[0]) if any_ else '> {:.0f}'.format(DIAG_SUCHE_M), MAX_SNAP_M)
                else:
                    u = 'NETZ_VORHANDEN_ABER_FUER_FAHRZEUG_AUSGESCHLOSSEN'
                    t = '{}: naechste Strasse {} ({:.0f} m) ist fuer {} gesperrt: {}; naechste zulaessige {}'.format(
                        name.capitalize(), _s(self.info[any_[1]]['name']) or self.info[any_[1]]['seg_id'], any_[0], code,
                        self.aus.get(code, {}).get(any_[1], '?'),
                        '{:.0f} m ({})'.format(ok_[0], _s(self.info[ok_[1]]['name']) or self.info[ok_[1]]['seg_id']) if ok_ else 'nicht im Umkreis')
                return dict(code=code, ok=False, ursache=u, text=t, diag=diag)
            snaps.append(ok_); ersatz.append(False); bezug.append(p)
        (d1, f1, s1), (d2, f2, s2) = snaps
        diag['snap_start_m'], diag['snap_ziel_m'] = round(d1, 2), round(d2, 2)
        pkt = self._punkte_fuer(code, kosten)
        abb = self._abbiege_tabelle(code)
        direkt = not ersatz[0] and not ersatz[1]
        r = self.kern.route(f1, s1, f2, s2, kosten, pkt, abb) if direkt or code == 'REF' else None
        if r is None and code != 'REF':
            # V9.2e: Ersatzanschluss nach Gesamtkosten (Fahrzeit + Restweg x RESTWEG_SEK_PRO_M) statt nach Abstand, eine Suche
            # ueber alle zulaessigen Anschluesse. Zuerst nur die nicht anfahrbare Seite; findet das nichts (oder war alles
            # direkt, der naechste zulaessige Abschnitt aber abgeschnitten = F4): beide Seiten.
            versuche = [(True, True)] if direkt else [(ersatz[0], ersatz[1]), (True, True)]
            leer = [False, False]
            for vs, vz in versuche:
                ks = self._anschluesse(bezug[0], kosten) if vs else [(f1, s1, 0.0)]
                kz = self._anschluesse(bezug[1], kosten) if vz else [(f2, s2, 0.0)]
                leer = [leer[0] or (ersatz[0] and not ks), leer[1] or (ersatz[1] and not kz)]
                rr = self.kern.route_mehrfach(ks, kz, kosten, pkt, abb)
                if rr is None:
                    continue
                r = (rr[0], rr[1])
                a_, b_ = ks[rr[2]], kz[rr[3]]
                if vs and vz:
                    diag['f4_anschluss'] = 'naechster zulaessiger Abschnitt ohne Verbindung; guenstigster von {} x {} Anschluessen verwendet'.format(len(ks), len(kz))
                for i, (name, f_alt, neu, pt) in enumerate((('start', f1, a_, p1), ('ziel', f2, b_, p2))):
                    if not ersatz[i] and neu[0] == f_alt:
                        continue
                    if not ersatz[i]:
                        diag[name + '_status'] = ('ZIEL' if name == 'ziel' else 'START') + '_NICHT_ANFAHRBAR'
                        diag[name + '_gesperrt_seg'] = self.info[f_alt]['seg_id']
                        diag[name + '_gesperrt_grund'] = 'naechster zulaessiger Abschnitt {} ist vom uebrigen zulaessigen Netz abgeschnitten'.format(self.info[f_alt]['seg_id'])
                    diag[name + '_alternativ_x'], diag[name + '_alternativ_y'] = round(neu[1][4], 2), round(neu[1][5], 2)
                    diag[name + '_restdistanz_luftlinie_m'] = round(math.hypot(neu[1][4] - bezug[i][0], neu[1][5] - bezug[i][1]), 1)
                (f1, s1), (f2, s2) = a_[:2], b_[:2]
                d1, d2 = s1[0], s2[0]
                snaps = [(d1, f1, s1), (d2, f2, s2)]
                diag['snap_start_m'], diag['snap_ziel_m'] = round(d1, 2), round(d2, 2)
                break
            if r is None and True in leer:
                i = leer.index(True); name = ('start', 'ziel')[i]
                t = '{}: naechste Strasse ist fuer {} gesperrt: {}; naechster zulaessiger Anschluss {:.0f} m entfernt (max. {:.0f} m)'.format(
                    name.capitalize(), code, diag.get(name + '_gesperrt_grund', '?'), snaps[i][0], F4_MAX_M)
                return dict(code=code, ok=False, ursache='NETZ_VORHANDEN_ABER_FUER_FAHRZEUG_AUSGESCHLOSSEN', text=t, diag=diag)
        abb_genutzt = list(getattr(self.kern, 'letzte_abbiegen', []))
        if r is not None and code != 'REF':
            alt = self._restweg(code, p2, kosten, pkt, abb, f1, s1, r[0])
            if alt is not None:
                r, (f2, s2), restweg, abb_genutzt = alt
                diag['ziel_status'] = 'ZIEL_ZU_FUSS'
                diag['ziel_restdistanz_luftlinie_m'] = round(restweg, 1)
                diag['ziel_alternativ_x'], diag['ziel_alternativ_y'] = round(s2[4], 2), round(s2[5], 2)
                diag['ziel_gesperrt_seg'] = self.info[snaps[1][1]]['seg_id']
                diag['ziel_gesperrt_grund'] = 'Zufahrt fuer {} kritisch ({})'.format(code, (self.info[snaps[1][1]][code.lower() + '_grund'] or '')[:80])
        if r is None:
            if self.kern.ungerichtet_verbunden(f1, s1, f2, s2, kosten):
                u, t = 'EINBAHNRICHTUNG_VERHINDERT_VERBINDUNG', 'Verbindung nur entgegen der Einbahnrichtung'
            elif self.kern.ungerichtet_verbunden(f1, s1, f2, s2, None):
                u, t = 'FAHRZEUGBESCHRAENKUNG_TRENNT', 'Im Gesamtnetz verbunden, aber nicht ueber fuer {} zulaessige Strassen'.format(code)
            else:
                u, t = 'UNTERSCHIEDLICHE_NETZKOMPONENTEN', 'Start und Ziel liegen in getrennten Netzteilen'
            rand = [w for w, f_ in (('Start', f1), ('Ziel', f2))
                    if (self.info[f_].get('gemeinde') or '') == 'ausserhalb AOI']     # V9.2f: vorher ['_row'] -> KeyError
            if rand and u != 'EINBAHNRICHTUNG_VERHINDERT_VERBINDUNG':
                # V8.1: am Rand ist das Netz nur ein Puffer (abgeschnitten) -> keine Aussage ueber echte Erreichbarkeit
                u = 'AUSSERHALB_UNTERSUCHUNGSGEBIET'
                t = '{} liegt ausserhalb des Untersuchungsgebiets (Netz dort nur als Randpuffer, abgeschnitten) – keine Aussage moeglich. ({})'.format(' und '.join(rand), t)
            return dict(code=code, ok=False, ursache=u, text=t, diag=diag)
        sek, weg = r
        rows = []
        fahrzeit_s = 0.0
        laenge_exakt = sum(L for _, _, _, _, L in self.kern.zusammenfassen(weg))
        for seq, (fid, pi, a, b, L) in enumerate(self.kern.zusammenfassen(weg), 1):
            info = self.info[fid]; F = self.kern.feat[fid]
            off = F['off'][pi]
            spm = kosten[fid]
            basis = L / (info['speed'] / 3.6)
            n_auf = 0
            for ppi, pos, psek in pkt.get(fid, []):
                if psek is not None and ppi == pi and (min(a, b) + 0.01 < pos < max(a, b) - 0.01 or abs(pos - b) <= 0.01):
                    n_auf += 1
            fahrzeit_s += basis + n_auf * OEFFNEN_SEK
            kat = 'REFERENZ' if code == 'REF' else (info[code.lower() + '_kat'] or 'UNGEKLAERT')
            if kat == 'BESCHRAENKUNG_BESTAETIGT' and self._nur_feste_sperre(fid, code):
                kat = self.kat_ohne_hindernis.get((fid, code), 'UNGEKLAERT')      # V7.5: Abschnitt nur bis zur Sperre befahren
            rows.append(dict(route_id='', seq=seq, seg_id=info['seg_id'], strasse=_s(info['name']),
                             fahrtrichtung='mit Digitalisierung' if b >= a else 'gegen Digitalisierung',
                             anteil_von=round((off + a) / F['L'], 4) if F['L'] else 0, anteil_bis=round((off + b) / F['L'], 4) if F['L'] else 0,
                             laenge_m=round(L, 2), profil=code, kategorie=kat, grundkosten_s=round(basis, 2),
                             zusatzkosten_s=round(L * spm - basis, 2),
                             kostengrund='; '.join(x for x in [grund.get(fid, ''), '{} x Tor/Poller oeffnen +{:.0f} s'.format(n_auf, OEFFNEN_SEK) if n_auf else ''] if x),
                             grund=info[code.lower() + '_grund'] if code != 'REF' else '', netz_version=self.netz_version,
                             _pts=self.kern.teilgeometrie(fid, pi, a, b), _fid=fid))
        laenge = laenge_exakt
        status = [diag[k] for k in ('start_status', 'ziel_status') if diag.get(k)]
        abb_txt = [abb['text'].get((u, fi, fo), '') for u, fi, fo, _ in abb_genutzt]
        for fid_k in {r_['_fid'] for r_ in rows}:
            t_k = abb['text'].get(('K', fid_k))
            if t_k:
                abb_txt.append(t_k)
        out = dict(code=code, ok=True, laenge_m=laenge, modell_min=sek / 60.0, fahrzeit_min=fahrzeit_s / 60.0, rows=rows, diag=diag,
                   abbiegen=[t for t in abb_txt if t],
                   kat_m=dict(sum((Counter({r['kategorie']: r['laenge_m']}) for r in rows), Counter())))
        if diag.get('ziel_status') == 'ZIEL_ZU_FUSS':
            out['ursache'] = 'ZIEL_ZU_FUSS'
            out['text'] = 'Halt an geeigneter Strasse, letzte {:.0f} m zu Fuss/Schlauch: {}'.format(
                diag['ziel_restdistanz_luftlinie_m'], diag['ziel_gesperrt_grund'])
        elif status:
            out['ursache'] = status[-1]
            out['text'] = '; '.join('{}: {} gesperrt ({}), Alternativpunkt {:.0f}/{:.0f}, Restdistanz {} m Luftlinie NICHT befahren'.format(
                n, diag[n + '_gesperrt_seg'], diag[n + '_gesperrt_grund'], diag[n + '_alternativ_x'], diag[n + '_alternativ_y'],
                diag[n + '_restdistanz_luftlinie_m']) for n in ('start', 'ziel') if diag.get(n + '_status'))
        out['belege'] = self._belege(code, rows)
        return out

    def _restweg(self, code, p2, kosten, pkt, abb, f1, s1, kosten_orig):
        """V8: Haltepunkt an geeigneter, oeffentlicher Strasse bis ZUFAHRT_RESTWEG_M vor dem Ziel pruefen."""
        import math as _m
        geeignet = {f: c for f, c in kosten.items()
                    if self.info[f][code.lower() + '_kat'] == 'KEIN_HINWEIS' and self.info[f].get('hw') != 'service'}
        best = None
        for fid in self.sidx.nearestNeighbor(QgsPointXY(p2[0], p2[1]), 30, ZUFAHRT_RESTWEG_M):
            if fid not in geeignet or fid not in self.kern.feat:
                continue
            sn = self.kern.project(fid, p2[0], p2[1])
            if sn and sn[0] <= ZUFAHRT_RESTWEG_M and (best is None or sn[0] < best[0]):
                best = (sn[0], fid, sn)
        if best is None:
            return None
        r2 = self.kern.route(f1, s1, best[1], best[2], kosten, pkt, abb)
        if r2 is None:
            return None
        if r2[0] + best[0] * RESTWEG_SEK_PRO_M < kosten_orig - 1.0:
            return r2, (best[1], best[2]), best[0], list(getattr(self.kern, 'letzte_abbiegen', []))
        return None

    def _monotonie(self, res):
        """V7.6: leichteres Fahrzeug faehrt weiter als schwereres -> begruenden."""
        out = []
        reihe = [c for c in ('A', 'B', 'C', 'D') if res.get(c) and res[c]['ok']]
        for i, x in enumerate(reihe):
            for y in reihe[i + 1:]:
                rx, ry = res[x], res[y]
                if rx['laenge_m'] <= ry['laenge_m'] + 20:
                    continue
                kx, _ = self._profil_kosten(x)
                def risiko(rows):
                    m = Counter()
                    for r in rows:
                        k = self.info[r['_fid']][x.lower() + '_kat'] or 'UNGEKLAERT'
                        if k in ('VERDACHT_GRENZFALL', 'UNGEKLAERT'):
                            m[k] += r['laenge_m']
                        if 'Baustelle' in r['kostengrund']:
                            m['Baustelle'] += r['laenge_m']
                    return m
                auf_y, auf_x = risiko(ry['rows']), risiko(rx['rows'])
                teile = ['{:.0f} m {}'.format(auf_y[k] - auf_x[k], {'VERDACHT_GRENZFALL': 'Verdacht', 'UNGEKLAERT': 'ungeklaert'}.get(k, k))
                         for k in ('VERDACHT_GRENZFALL', 'UNGEKLAERT', 'Baustelle') if auf_y[k] - auf_x[k] > 1]
                out.append('{} faehrt {:.0f} m weiter als {}: auf der {}-Route laegen fuer {} {} mehr. {} meidet das; fuer {} ist '
                           'die Ausweichstrecke selbst kritisch (z. B. Gewicht/Breite), darum nimmt {} den kuerzeren Weg.'.format(
                               x, rx['laenge_m'] - ry['laenge_m'], y, y, x, ', '.join(teile) or 'Aufschlaege', x, y, y))
        return out

    def _belege(self, code, rows):
        if not getattr(self, 'hat_evidenz', False) or code == 'REF' or not rows:
            return []
        return lies_evidenz(self.src_pfad, code, [r['seg_id'] for r in rows])

    # ------------------------------------------------------------------ Speichern + Karte
    def _speichern(self, run_id, res, p1, p2):
        gp = OUT_DIR / 'BORS_Route_{}.gpkg'.format(run_id)
        srs = osr.SpatialReference(); srs.ImportFromEPSG(2056)
        ds = ogr.GetDriverByName('GPKG').CreateDataSource(str(gp))
        el = ds.CreateLayer('route_edges', srs, ogr.wkbLineString)
        cols = ['route_id', 'seq', 'seg_id', 'strasse', 'fahrtrichtung', 'anteil_von', 'anteil_bis', 'laenge_m', 'profil',
                'kategorie', 'grundkosten_s', 'zusatzkosten_s', 'kostengrund', 'grund', 'netz_version']
        typ = {'seq': ogr.OFTInteger, 'anteil_von': ogr.OFTReal, 'anteil_bis': ogr.OFTReal, 'laenge_m': ogr.OFTReal,
               'grundkosten_s': ogr.OFTReal, 'zusatzkosten_s': ogr.OFTReal}
        for c in cols:
            el.CreateField(ogr.FieldDefn(c, typ.get(c, ogr.OFTString)))
        dl = ds.CreateLayer('diagnose', None, ogr.wkbNone)
        dcols = ['route_id', 'profil', 'route_gefunden', 'ursache', 'text', 'laenge_m', 'fahrzeit_min', 'modellzeit_min', 'start_x', 'start_y',
                 'ziel_x', 'ziel_y', 'snap_start_m', 'snap_ziel_m', 'start_naechste_strasse_m', 'start_naechste_strasse_seg',
                 'start_naechste_zulaessig_m', 'start_naechste_zulaessig_seg', 'ziel_naechste_strasse_m',
                 'ziel_naechste_strasse_seg', 'ziel_naechste_zulaessig_m', 'ziel_naechste_zulaessig_seg', 'kat_laengen',
                 'kostenfaktoren', 'netz_version', 'zeitpunkt', 'baustellen_quelle', 'start_status', 'ziel_status',
                 'ziel_gesperrt_seg', 'ziel_gesperrt_grund', 'ziel_alternativ_x', 'ziel_alternativ_y', 'ziel_restdistanz_luftlinie_m',
                 'start_gesperrt_seg', 'start_gesperrt_grund', 'start_alternativ_x', 'start_alternativ_y', 'start_restdistanz_luftlinie_m']
        for c in dcols:
            dl.CreateField(ogr.FieldDefn(c, ogr.OFTString))
        ds.StartTransaction()
        for code, r in res.items():
            rid = '{}_{}'.format(run_id, code)
            for row in r.get('rows', []):
                f = ogr.Feature(el.GetLayerDefn())
                row['route_id'] = rid
                for c in cols:
                    f.SetField(c, row[c])
                ln = ogr.Geometry(ogr.wkbLineString)
                for x, y in row['_pts']:
                    ln.AddPoint_2D(x, y)
                f.SetGeometry(ln); el.CreateFeature(f)
            f = ogr.Feature(dl.GetLayerDefn())
            vals = dict(route_id=rid, profil=code, route_gefunden=('JA, ALTERNATIVPUNKT' if r.get('ursache', '').endswith('NICHT_ANFAHRBAR') else 'JA') if r['ok'] else 'NEIN',
                        zeitpunkt=ZEITPUNKT, baustellen_quelle=self.bau_quelle, ursache=r.get('ursache', ''),
                        text=r.get('text', ''), laenge_m='{:.1f}'.format(r['laenge_m']) if r['ok'] else '',
                        modellzeit_min='{:.2f}'.format(r['modell_min']) if r['ok'] else '',
                        fahrzeit_min='{:.2f}'.format(r['fahrzeit_min']) if r['ok'] else '', start_x='{:.2f}'.format(p1[0]),
                        start_y='{:.2f}'.format(p1[1]), ziel_x='{:.2f}'.format(p2[0]), ziel_y='{:.2f}'.format(p2[1]),
                        kat_laengen='; '.join('{} {:.1f} m'.format(k, v) for k, v in r.get('kat_m', {}).items()),
                        kostenfaktoren=str(KAT_FAKTOR), netz_version=self.netz_version)
            vals.update({k: '' if v is None else str(v) for k, v in r.get('diag', {}).items()})
            for c in dcols:
                if vals.get(c) not in (None, ''):
                    f.SetField(c, str(vals[c]))
            dl.CreateFeature(f)
        bl = ds.CreateLayer('route_belege', None, ogr.wkbNone)
        bcols = ['route_id', 'seq', 'seg_id', 'profil', 'kriterium', 'quelle', 'evidenzklasse', 'stufe', 'messwert', 'einheit',
                 'methode', 'erhebungsdatum', 'validierungsstatus', 'entscheidungsregel', 'entscheidung', 'begruendung']
        for c in bcols:
            bl.CreateField(ogr.FieldDefn(c, ogr.OFTString))
        for code, r in res.items():
            seqs = {}
            for row in r.get('rows', []):
                seqs.setdefault(row['seg_id'], row['seq'])
            for b in r.get('belege', []):
                f = ogr.Feature(bl.GetLayerDefn())
                vals = dict(b); vals['route_id'] = '{}_{}'.format(run_id, code); vals['seq'] = seqs.get(b['seg_id'], '')
                for c in bcols:
                    if vals.get(c) not in (None, ''):
                        f.SetField(c, str(vals[c]))
                bl.CreateFeature(f)
        ds.CommitTransaction(); ds = None
        with (OUT_DIR / 'BORS_Route_{}_route_edges.csv'.format(run_id)).open('w', newline='', encoding='utf-8-sig') as fh:
            w = csv.DictWriter(fh, fieldnames=cols, delimiter=';', extrasaction='ignore')
            w.writeheader()
            for r in res.values():
                w.writerows(r.get('rows', []))
        return gp

    def _gruppe(self):
        root = self.prj.layerTreeRoot()
        g = root.findGroup(GRUPPE)
        if g is None:
            g = root.insertGroup(0, GRUPPE)
        for ch in list(g.children()):               # alte Anzeige entfernen (Dateien bleiben gespeichert)
            if hasattr(ch, 'layerId'):
                self.prj.removeMapLayer(ch.layerId())
        g.removeAllChildren()
        return g

    def _karte(self, res, gp, sichtbar):
        g = self._gruppe()
        pl = QgsVectorLayer('Point?crs=EPSG:2056&field=name:string(20)', 'Start / Ziel', 'memory')
        fs = []
        for nm, p in (('Start', self.points[0]), ('Ziel', self.points[1])):
            f = QgsFeature(pl.fields()); f.setAttributes([nm]); f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(*p))); fs.append(f)
        pl.dataProvider().addFeatures(fs)
        pl.setRenderer(QgsCategorizedSymbolRenderer('name', [
            QgsRendererCategory('Start', QgsMarkerSymbol.createSimple({'name': 'circle', 'color': '#ffffff', 'outline_color': '#1f4e9c', 'outline_width': '1.2', 'size': '4.2'}), 'Start'),
            QgsRendererCategory('Ziel', QgsMarkerSymbol.createSimple({'name': 'circle', 'color': '#1f4e9c', 'outline_color': '#ffffff', 'outline_width': '0.8', 'size': '4.6'}), 'Ziel')]))
        try:
            ls = QgsPalLayerSettings(); ls.fieldName = 'name'
            tf = QgsTextFormat(); tf.setSize(10); bf = QgsTextBufferSettings(); bf.setEnabled(True); bf.setSize(1.2); tf.setBuffer(bf)
            ls.setFormat(tf)
            pl.setLabeling(QgsVectorLayerSimpleLabeling(ls)); pl.setLabelsEnabled(True)
        except Exception:
            pass
        self.prj.addMapLayer(pl, False); g.addLayer(pl)
        first = None
        for code in ['A', 'B', 'C', 'D', 'REF']:
            r = res.get(code)
            if not r or not r['ok']:
                continue
            name = 'Referenz (Auto, ohne Sonderrecht)' if code == 'REF' else 'Route {}'.format(PROFILE[code]['label'])
            lyr = QgsVectorLayer('{}|layername=route_edges'.format(gp), name, 'ogr')
            lyr.setSubsetString('"profil" = \'{}\''.format(code))
            if not lyr.isValid():
                self._log('Routen-Layer {} konnte nicht geladen werden ({})'.format(code, gp))
                continue
            if code == 'REF':
                lyr.renderer().setSymbol(QgsLineSymbol.createSimple({'line_color': FARBE['REFERENZ'], 'line_width': '0.9', 'line_style': 'dash'}))
            else:
                cats = []
                for k in ('KEIN_HINWEIS', 'VERDACHT_GRENZFALL', 'UNGEKLAERT'):
                    sym = QgsLineSymbol.createSimple({'line_color': '#ffffff', 'line_width': '3.0'})
                    top = QgsSimpleLineSymbolLayer(QColor(FARBE[k]), 2.0)
                    sym.appendSymbolLayer(top)
                    cats.append(QgsRendererCategory(k, sym, KAT_TEXT[k]))
                lyr.setRenderer(QgsCategorizedSymbolRenderer('kategorie', cats))
            self.prj.addMapLayer(lyr, False)
            node = g.addLayer(lyr)
            node.setItemVisibilityChecked(code in sichtbar)
            if code in sichtbar and first is None:
                first = lyr
        if first is not None:
            rect = first.extent(); rect.scale(1.25)
            self.canvas.setExtent(rect)
        self.canvas.refresh()

    # ------------------------------------------------------------------ Oberflaeche
    def _ui(self):
        self.dock = QDockWidget('BORS Bern · Fahrzeugrouting', iface.mainWindow())
        self.dock.setObjectName('BORS_Router_V7')
        outer = QScrollArea(); outer.setWidgetResizable(True)
        w = QWidget(); w.setObjectName('bors')
        w.setStyleSheet("""
            QWidget#bors { background: #f6f7f9; }
            QLabel { color: #1d2430; }
            QLabel#titel { font-size: 15pt; font-weight: 600; }
            QLabel#sub { color: #5b6573; font-size: 8.5pt; }
            QLabel#sektion { color: #5b6573; font-size: 8pt; font-weight: 600; letter-spacing: 1px; margin-top: 6px; }
            QPushButton#fz { background: #ffffff; border: 1px solid #d5d9e0; border-radius: 8px; padding: 8px;
                             text-align: left; color: #1d2430; font-size: 9pt; }
            QPushButton#fz:checked { background: #e8f0fe; border: 2px solid #1f4e9c; }
            QPushButton#primaer { background: #1f4e9c; color: white; border: none; border-radius: 8px; padding: 10px;
                                  font-size: 10pt; font-weight: 600; }
            QPushButton#primaer:hover { background: #163a75; }
            QPushButton#sekundaer { background: #ffffff; color: #1f4e9c; border: 1px solid #1f4e9c; border-radius: 8px;
                                    padding: 8px; font-size: 9pt; }
            QFrame#karte { background: #ffffff; border: 1px solid #e1e4e8; border-radius: 10px; }
            QLabel#status { color: #5b6573; font-size: 9pt; }
            QTextEdit { background: #ffffff; border: 1px solid #e1e4e8; font-family: Consolas, monospace; font-size: 8pt; }
            QTableWidget { background: #ffffff; border: none; font-size: 9pt; }
            QToolButton { border: none; color: #5b6573; font-size: 8.5pt; }
        """)
        lay = QVBoxLayout(w); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(8)
        t = QLabel('BORS Bern'); t.setObjectName('titel'); lay.addWidget(t)
        s = QLabel('Fahrzeugabhängiges Routing · Prototyp BFH · keine Einsatzfreigabe'); s.setObjectName('sub'); s.setWordWrap(True)
        lay.addWidget(s)
        k = QLabel('FAHRZEUG'); k.setObjectName('sektion'); lay.addWidget(k)
        grid = QGridLayout(); grid.setSpacing(6)
        self.fz = QButtonGroup(w); self.fz.setExclusive(True)
        for i, code in enumerate(['A', 'B', 'C', 'D']):          # V9.2b: nur die vier Profile (Einzelfahrzeuge nutzten V8-Kategorien)
            p = PROFILE[code]
            b = QPushButton('{}\n{:.2f} m breit · {:.2f} m hoch · {:.1f} t'.format(p['label'], p['width'], p['height'], p['tonnes']))
            b.setObjectName('fz'); b.setCheckable(True); b.setChecked(code == self.code)
            b.clicked.connect(lambda _=False, c=code: self._wahl(c))
            self.fz.addButton(b); grid.addWidget(b, i // 2, i % 2)
        lay.addLayout(grid)
        self.fzwahl = QComboBox()
        self.fzwahl.addItem('Konkretes Fahrzeug wählen …', '')
        for fid_, v in sorted(FAHRZEUGE.items(), key=lambda kv: (kv[1]['kategorie'], kv[1]['gewicht_t'])):
            self.fzwahl.addItem('{} · {} ({:.2f} m / {:.2f} m hoch / {:.1f} t)'.format(v['kategorie'], v['bezeichnung'], v['breite_karosserie_m'],
                                                                                 v['hoehe_m'], v['gewicht_t']), fid_)
        self.fzwahl.currentIndexChanged.connect(self._fz_liste)
        lay.addWidget(self.fzwahl)
        self.fzwahl.setVisible(False)          # V9: nur Profile A-D in der Oberflaeche (Einzelfahrzeuge nur als Referenz)
        self.modus_ui = 'VALIDIERT'
        self.cb_exp = QCheckBox('Experimentell: unvalidierte Abschnitte zulassen (Risikozuschlag x{:.1f})'.format(RISIKO_FAKTOR))
        self.cb_exp.setToolTip('Standard: nur validierte Abschnitte. Gibt es keine validierte Route, wird die experimentelle Route '
                               'automatisch berechnet und rot als UNVALIDIERT markiert.')
        self.cb_exp.toggled.connect(self._modus_umschalten)
        lay.addWidget(self.cb_exp)
        k3 = QLabel('START / ZIEL'); k3.setObjectName('sektion'); lay.addWidget(k3)
        self.wachen = QComboBox(); self.wachen.addItem('Start ab Wache …', None)
        for w_ in lade_wachen():
            self.wachen.addItem(w_[0], (w_[1], w_[2], w_[3]))
        self.wachen.currentIndexChanged.connect(self._wache)
        lay.addWidget(self.wachen)
        rs = QHBoxLayout()
        self.suche = QLineEdit(); self.suche.setPlaceholderText('Adresse, z. B. Kramgasse 49 Bern')
        self.suche.returnPressed.connect(self._suchen)
        bs = QPushButton('Suchen'); bs.setObjectName('sekundaer'); bs.clicked.connect(self._suchen)
        rs.addWidget(self.suche, 1); rs.addWidget(bs); lay.addLayout(rs)
        self.treffer = QComboBox(); self.treffer.setVisible(False); lay.addWidget(self.treffer)
        rz = QHBoxLayout()
        self.b_als_start = QPushButton('als Start'); self.b_als_start.setObjectName('sekundaer'); self.b_als_start.clicked.connect(lambda: self._setze(0))
        self.b_als_ziel = QPushButton('als Ziel → berechnen'); self.b_als_ziel.setObjectName('sekundaer'); self.b_als_ziel.clicked.connect(lambda: self._setze(1))
        rz.addWidget(self.b_als_start); rz.addWidget(self.b_als_ziel); lay.addLayout(rz)
        self.b_als_start.setVisible(False); self.b_als_ziel.setVisible(False)
        self.adr = [None, None]
        b1 = QPushButton('Start und Ziel auf der Karte setzen'); b1.setObjectName('primaer'); b1.clicked.connect(self._start)
        lay.addWidget(b1)
        row = QHBoxLayout()
        b2 = QPushButton('Alle Fahrzeuge vergleichen'); b2.setObjectName('sekundaer'); b2.clicked.connect(self._vergleich)
        row.addWidget(b2); lay.addLayout(row)
        self.status = QLabel('Fahrzeug wählen, dann Start und Ziel anklicken.'); self.status.setObjectName('status')
        self.status.setWordWrap(True); lay.addWidget(self.status)
        k2 = QLabel('ERGEBNIS'); k2.setObjectName('sektion'); lay.addWidget(k2)
        self.karte = QFrame(); self.karte.setObjectName('karte')
        kl = QVBoxLayout(self.karte); kl.setContentsMargins(12, 10, 12, 10)
        self.ergebnis = QLabel('<span style="color:#8a94a3">Noch keine Route berechnet.</span>')
        self.ergebnis.setWordWrap(True); self.ergebnis.setTextFormat(Qt.TextFormat.RichText)
        kl.addWidget(self.ergebnis)
        self.tabelle = QTableWidget(0, 5)
        self.tabelle.setHorizontalHeaderLabels(['Fahrzeug', 'Länge', 'Modellzeit', 'Δ Referenz', 'Befund'])
        self.tabelle.verticalHeader().setVisible(False)
        self.tabelle.horizontalHeader().setStretchLastSection(True)
        self.tabelle.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabelle.setVisible(False); self.tabelle.setMinimumHeight(170)
        kl.addWidget(self.tabelle)
        lay.addWidget(self.karte)
        self.tgl = QToolButton(); self.tgl.setText('▸ Technisches Protokoll'); self.tgl.setCheckable(True)
        self.tgl.toggled.connect(self._toggle); lay.addWidget(self.tgl)
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMinimumHeight(180); self.log.setVisible(False)
        lay.addWidget(self.log)
        foot = QLabel('Modellzeiten aus angenommenen Geschwindigkeiten und Kostenfaktoren – keine realen Einsatzzeiten. '
                      'Breiten aus amtlicher Vermessung (MOPUBE) minus Parkfelder; nicht alle Hindernisse erfasst.')
        foot.setObjectName('sub'); foot.setWordWrap(True); lay.addWidget(foot)
        lay.addStretch(1)
        outer.setWidget(w)
        self.dock.setWidget(outer)
        self.dock.setMinimumWidth(360)
        iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.show()

    # ------------------------------------------------------------------ V8: Fahrzeugliste, Wachen, Adresssuche
    def _modus_umschalten(self, on):
        self.modus_ui = 'EXPERIMENTELL' if on else 'VALIDIERT'
        self.status.setText('Modus: {}'.format('EXPERIMENTELL (unvalidiert, Risikozuschlag)' if on else 'VALIDIERT'))
        if len(self.points) == 2 and not self.busy:
            self._rechnen(['REF', self.code], vergleich=False)

    def _fz_liste(self, i):
        code = self.fzwahl.itemData(i)
        if code:
            for b in self.fz.buttons():
                b.setChecked(False)
            self._wahl(code)
            self.status.setText('Fahrzeug: {}. {}'.format(PROFILE[code]['kurz'], 'Route wird neu berechnet …' if len(self.points) == 2
                                                           else 'Start und Ziel setzen (Karte oder Adresse).'))

    def _wache(self, i):
        d = self.wachen.itemData(i)
        if not d:
            return
        name, x, y = self.wachen.itemText(i), d[1], d[2]
        if x is None:
            r = adresssuche(d[0])
            if not r:
                self.status.setText('Wache: Adresse nicht gefunden ({})'.format(d[0])); return
            x, y = r[0][1], r[0][2]
        self.adr[0] = (name, x, y)
        self.points = [(x, y)] + self.points[1:2] if len(self.points) == 2 else [(x, y)]
        self.status.setText('Start: {} – jetzt Ziel suchen oder auf der Karte anklicken.'.format(name))
        if len(self.points) == 2:
            self._rechnen(['REF', self.code], vergleich=False)
        else:
            self.canvas.setMapTool(self.tool)

    def _suchen(self):
        txt = self.suche.text().strip()
        if not txt:
            return
        self.status.setText('Suche …'); QApplication.processEvents()
        try:
            res = adresssuche(txt)
        except Exception as ex:
            self.status.setText('Adresssuche nicht erreichbar: {}'.format(ex)); return
        self.treffer.clear()
        for label, x, y in res:
            self.treffer.addItem(label, (x, y))
        ok = bool(res)
        self.treffer.setVisible(ok); self.b_als_start.setVisible(ok); self.b_als_ziel.setVisible(ok)
        self.status.setText('{} Treffer. Ziel = Gebaeudeeingang; angefahren wird die naechste geeignete Strasse.'.format(len(res)) if ok
                            else 'Keine Adresse gefunden.')

    def _setze(self, idx):
        d = self.treffer.currentData()
        if not d:
            return
        lab = self.treffer.currentText()
        self.adr[idx] = (lab, d[0], d[1])
        if idx == 0:
            self.points = [(d[0], d[1])] + (self.points[1:2] if len(self.points) == 2 else [])
            self.status.setText('Start: {}'.format(lab))
            if len(self.points) == 2:
                self._rechnen(['REF', self.code], vergleich=False)
            return
        if not self.points:
            self.status.setText('Zuerst Start setzen (Wache, Adresse oder Karte).'); return
        self.points = [self.points[0], (d[0], d[1])]
        self._log('Ziel per Adresse: {} ({:.1f}/{:.1f})'.format(lab, d[0], d[1]))
        self._rechnen(['REF', self.code], vergleich=False)

    def _toggle(self, on):
        self.log.setVisible(on)
        self.tgl.setText(('▾ ' if on else '▸ ') + 'Technisches Protokoll')

    def _wahl(self, code):
        self.code = code
        if code in ('A', 'B', 'C', 'D') and hasattr(self, 'fzwahl') and self.fzwahl.currentIndex() != 0:
            self.fzwahl.blockSignals(True); self.fzwahl.setCurrentIndex(0); self.fzwahl.blockSignals(False)
        if len(self.points) == 2 and not self.busy:
            self._rechnen(['REF', code], vergleich=False)

    def _log(self, m):
        self.log.append(str(m))
        print('BORS ROUTER V9.2f:', m)

    def _start(self):
        if self.busy:
            return
        self.points = []
        self.status.setText('START auf der Karte anklicken …')
        self.canvas.setMapTool(self.tool)

    def _klick(self, pt, button):
        try:
            if button != Qt.MouseButton.LeftButton or len(self.points) >= 2 or self.busy:
                return
            self.points.append((float(pt.x()), float(pt.y())))
            self._log('Klick {}: {:.1f}/{:.1f}'.format(len(self.points), self.points[-1][0], self.points[-1][1]))
            if len(self.points) == 1:
                self.status.setText('ZIEL auf der Karte anklicken …')
                return
            self.status.setText('Berechne …')
            QTimer.singleShot(50, self._nach_klick)      # erst rechnen, wenn QGIS den Klick fertig verarbeitet hat
        except Exception as ex:
            self._log('FEHLER beim Klick: {}: {}'.format(type(ex).__name__, ex))

    def _nach_klick(self):
        try:
            iface.actionPan().trigger()
        except Exception:
            pass
        QTimer.singleShot(50, lambda: self._rechnen(['REF', self.code], vergleich=False))

    def _vergleich(self):
        if len(self.points) != 2:
            QMessageBox.information(self.dock, 'BORS', 'Zuerst Start und Ziel auf der Karte setzen.')
            return
        self._rechnen(['REF', 'A', 'B', 'C', 'D'], vergleich=True)

    def _rechnen(self, codes, vergleich):
        self.busy = True
        self.status.setText('Berechne …'); QApplication.processEvents()
        try:
            p1, p2 = self.points
            run_id = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:4]
            self._log('--- Lauf {} | Start {:.1f}/{:.1f} | Ziel {:.1f}/{:.1f} | Profile {}'.format(run_id, p1[0], p1[1], p2[0], p2[1], codes))
            res = self.berechne(p1, p2, codes)
            gp = self._speichern(run_id, res, p1, p2)
            self.letzte = res
            self._karte(res, gp, {'REF', self.code})
            self._anzeigen(res, vergleich)
            for code, r in res.items():
                if r['ok']:
                    self._log('{} [{}{}]: {:.0f} m | {:.2f} Fahrzeit-min | Snap {}/{} m | Kategorien {}'.format(
                        code, r.get('modus', ''), ', {:.0f} m unvalidiert'.format(r.get('unvalidiert_m', 0)) if r.get('modus') == 'EXPERIMENTELL' else '',
                        r['laenge_m'], r['fahrzeit_min'], r['diag'].get('snap_start_m'), r['diag'].get('snap_ziel_m'),
                        {k: round(v) for k, v in r['kat_m'].items()}))
                    if r.get('ursache'):
                        self._log('   STATUS {}: {}'.format(r['ursache'], r['text']))
                    if r.get('dominanz_text'):
                        self._log('   ' + r['dominanz_text'])
                    for t in r.get('abbiegen', [])[:10]:
                        self._log('   ABBIEGEN ' + t)
                    if r.get('belege'):
                        st = Counter(); offen = Counter()
                        lmap = {x['seg_id']: x['laenge_m'] for x in r['rows']}
                        for b in r['belege']:
                            st[(b['kriterium'], b['stufe'])] += lmap.get(b['seg_id'], 0)
                        self._log('   BELEGE {} (m je Kriterium/Stufe): {}'.format(code, ', '.join(
                            '{} {} {:.0f}'.format(k[0], k[1], v) for k, v in sorted(st.items()))))
                        self._log('   KEIN_HINWEIS = nicht nachgewiesen passierbar; Belege je Segment in Tabelle route_belege.')
                    for row in r['rows']:
                        if row['kategorie'] not in ('KEIN_HINWEIS', 'REFERENZ') or row['kostengrund']:
                            self._log('   {} {} {:.0f} m | {} | {} | {}'.format(row['seq'], row['strasse'] or row['seg_id'], row['laenge_m'],
                                                                     row['kategorie'], row['kostengrund'], row['grund'][:120]))
                else:
                    self._log('{}: KEINE ROUTE | {} | {} | Diagnose {}'.format(code, r['ursache'], r['text'], r['diag']))
            for t in self._monotonie(res):
                self._log('HINWEIS: ' + t)
            self._log('Gespeichert: {}'.format(gp))
            self.status.setText('Fertig. Ergebnisse gespeichert (route_edges + Diagnose).')
        except Exception as ex:
            self._log('FEHLER: {}: {}'.format(type(ex).__name__, ex))
            self.status.setText('Fehler – Details im technischen Protokoll.')
        finally:
            self.busy = False

    def _befund(self, r):
        if not r['ok']:
            return URSACHE_TEXT.get(r['ursache'], r['ursache'])
        teile = []
        if r.get('ursache', '').endswith('NICHT_ANFAHRBAR'):
            teile.append('nur bis Alternativpunkt')
        v = r['kat_m'].get('VERDACHT_GRENZFALL', 0); u = r['kat_m'].get('UNGEKLAERT', 0)
        if v:
            teile.append('{:.0f} m Verdacht'.format(v))
        if u:
            teile.append('{:.0f} m ungeklärt'.format(u))
        sr = sum(1 for x in r['rows'] if 'Sonderrecht' in x['kostengrund'])
        if sr:
            teile.append('{} × Sonderrecht'.format(sr))
        if any('Baustelle' in x['kostengrund'] for x in r['rows']):
            teile.append('Baustelle')
        if any('oeffnen' in x['kostengrund'] for x in r['rows']):
            teile.append('Tor/Poller')
        return ', '.join(teile) or 'keine Hinweise'

    def _balken(self, r):
        tot = r['laenge_m'] or 1
        cells = ''.join('<td style="background:{};" width="{}%">&nbsp;</td>'.format(FARBE[k], max(1, int(100 * r['kat_m'].get(k, 0) / tot)))
                        for k in ('KEIN_HINWEIS', 'VERDACHT_GRENZFALL', 'UNGEKLAERT') if r['kat_m'].get(k, 0) > 0)
        return '<table width="100%" cellspacing="0" cellpadding="0" style="margin:4px 0;"><tr>{}</tr></table>'.format(cells)

    def _anzeigen(self, res, vergleich):
        ref = res.get('REF')
        r = res.get(self.code)
        html = []
        if r is not None:
            p = PROFILE[self.code]
            html.append('<div style="font-size:9pt;color:#5b6573">{}</div>'.format(p['label']))
            if r.get('modus') == 'VALIDIERT_BIS_ZUFAHRT' and self.code != 'REF':
                html.append('<div style="background:#fff8e1;border-left:4px solid #e6a700;padding:4px 6px;margin:4px 0">'
                            '<b>VALIDIERT BIS ZUR ZUFAHRT.</b> {}</div>'.format(r.get('zufahrt_text', '')))
            elif r.get('modus') == 'EXPERIMENTELL' and self.code != 'REF':
                html.append('<div style="background:#fdecea;border-left:4px solid #b42318;padding:4px 6px;margin:4px 0">'
                            '<b>KEINE VALIDIERTE ROUTE.</b> Angezeigt: experimentelle Route (UNVALIDIERT){}.<br>'
                            '<span style="font-size:8pt">{}</span></div>'.format(
                                ', {:.0f} m nicht nachgewiesen'.format(r.get('unvalidiert_m', 0)) if r.get('ok') else '',
                                r.get('validiert_ergebnis', '') if getattr(self, 'modus_ui', 'VALIDIERT') == 'VALIDIERT' else
                                'Modus experimentell gewaehlt; unvalidierte Abschnitte mit Risikozuschlag x{:.1f}'.format(RISIKO_FAKTOR)))
            elif r.get('ok') and self.code != 'REF':
                html.append('<div style="background:#e8f5e9;border-left:4px solid #1a9850;padding:4px 6px;margin:4px 0">'
                            '<b>VALIDIERTE ROUTE</b> (Breite nachgewiesen, keine Hinweise auf Hoehe/Gewicht/Hindernis; '
                            'aktuelle Baustellen und Kurven separat beachten)</div>')
            if r['ok'] and r.get('ursache', '').endswith('NICHT_ANFAHRBAR'):
                html.append('<div style="color:#b42318;font-weight:600">{}</div><div style="color:#5b6573;font-size:8.5pt">{}</div>'.format(
                    URSACHE_TEXT.get(r['ursache'], r['ursache']), r['text']))
            if r['ok']:
                html.append('<div style="font-size:18pt;font-weight:600">{:.2f} km · {:.1f} min</div><div style="color:#5b6573;font-size:8pt">Fahrzeit nach Modellgeschwindigkeit, ohne Unsicherheitsaufschläge</div>'.format(r['laenge_m'] / 1000, r['fahrzeit_min']))
                if ref and ref['ok']:
                    d = r['laenge_m'] - ref['laenge_m']; dt = r['fahrzeit_min'] - ref['fahrzeit_min']
                    html.append('<div style="color:#5b6573">{:+.0f} m · {:+.1f} min gegenüber normalem Auto-Routing</div>'.format(d, dt))
                if r.get('dominanz_text'):
                    html.append('<div style="color:#1f4e9c;font-size:8.5pt">' + r['dominanz_text'] + '</div>')
                if r.get('ursache') == 'ZIEL_ZU_FUSS':
                    html.append('<div style="color:#b54708;font-weight:600">' + r['text'] + '</div>')
                if r.get('abbiegen'):
                    html.append('<div style="margin-top:4px;font-weight:600">Abbiegen/Kurven (Schleppkurve)</div><ul style="margin:2px 0 0 -18px">' +
                                ''.join('<li>{}</li>'.format(t) for t in r['abbiegen'][:5]) + '</ul>')
                html.append(self._balken(r))
                html.append('<div style="font-size:8.5pt">' + ' &nbsp; '.join(
                    '<span style="color:{}">■</span> {} {:.0f} m'.format(FARBE[k], KAT_TEXT[k], v) for k, v in r['kat_m'].items() if v > 0) + '</div>')
                hin = [x for x in r['rows'] if x['kategorie'] in ('VERDACHT_GRENZFALL', 'UNGEKLAERT') or x['kostengrund']]
                if hin:
                    html.append('<div style="margin-top:6px;font-weight:600">Hinweise auf der Route</div><ul style="margin:2px 0 0 -18px">')
                    for x in sorted(hin, key=lambda x: -x['laenge_m'])[:6]:
                        html.append('<li>{} ({:.0f} m): {}</li>'.format(x['strasse'] or x['seg_id'], x['laenge_m'],
                                    x['grund'][:90] if x['kategorie'] != 'KEIN_HINWEIS' else x['kostengrund']))
                    html.append('</ul>')
            else:
                html.append('<div style="font-size:14pt;font-weight:600;color:#b42318">Keine Route</div>')
                html.append('<div>{}</div><div style="color:#5b6573;font-size:8.5pt">{}</div>'.format(
                    URSACHE_TEXT.get(r['ursache'], r['ursache']), r['text']))
        if vergleich:
            mh = self._monotonie(res)
            if mh:
                html.append('<div style="margin-top:6px;font-size:8.5pt;color:#5b6573">' + '<br>'.join(mh) + '</div>')
        self.ergebnis.setText(''.join(html))
        self.tabelle.setVisible(vergleich)
        if vergleich:
            order = ['REF', 'A', 'B', 'C', 'D']
            self.tabelle.setRowCount(len(order))
            for i, c in enumerate(order):
                x = res.get(c)
                vals = ['Referenz Auto' if c == 'REF' else PROFILE[c]['label'],
                        '{:.0f} m'.format(x['laenge_m']) if x and x['ok'] else '–',
                        '{:.1f} min'.format(x['fahrzeit_min']) if x and x['ok'] else '–',
                        '{:+.0f} m'.format(x['laenge_m'] - ref['laenge_m']) if x and x['ok'] and ref and ref['ok'] and c != 'REF' else '',
                        self._befund(x) if x else '']
                for j, v in enumerate(vals):
                    it = QTableWidgetItem(v)
                    if x and not x['ok']:
                        it.setForeground(QColor('#b42318'))
                    self.tabelle.setItem(i, j, it)
            self.tabelle.resizeColumnsToContents()

    def close(self):
        try:
            iface.actionPan().trigger()
            iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
        except Exception:
            pass


for _alt in ('BORS_ROUTER', 'BORS_ZWEI_KLICK_APP_V1'):
    try:
        globals()[_alt].close()
    except Exception:
        pass
try:
    import faulthandler
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _BORS_FH = open(str(OUT_DIR / 'absturz_protokoll.txt'), 'w', encoding='utf-8')
    faulthandler.enable(file=_BORS_FH, all_threads=True)
except Exception:
    pass
BORS_ROUTER = BorsRouterV7()
print('BORS ROUTER V9.2f bereit: Dock rechts. Fahrzeug waehlen -> "Start und Ziel auf der Karte setzen".')
