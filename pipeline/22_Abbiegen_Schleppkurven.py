# -*- coding: utf-8 -*-
r"""BORS Bern - 22: Abbiegen und Kurven je Fahrzeug pruefen (Schleppkurven-Simulation auf der amtlichen Strassenflaeche).

Fuer jeden Knoten (Kreuzung, Einmuendung) und jede starke Kurve im Zielgebiet und jede Fahrbeziehung
"von Abschnitt X nach Abschnitt Y" mit 30-120 Grad Richtungsaenderung wird simuliert, ob das Fahrzeug die Bewegung auf
der befestigten Strassenflaeche (AV-Bodenbedeckung Strasse/Weg; bei Zufahrten zusaetzlich uebrige befestigte Flaechen)
fahren kann. Methode: bors_schleppkurve.py (Vorderachse folgt geglaetteter/versetzter Bahn, Hinterachse Traktrix,
ganze Karosserie geprueft). Ergebnis je Fahrzeug: OK | ENG (nur ohne 0.25 m Reserve) | NUR_MIT_NEBENFLAECHE |
UNMOEGLICH | KEINE_DATEN. Richtungsaenderungen > 120 Grad = SPITZKEHRE (wie Wenden), Kreisel werden nicht geprueft.
Negativkontrolle: das NEF (Personenwagen) muss fast ueberall OK sein - die Quote steht im Bericht.
Parkierte Fahrzeuge an der Ecke sind nicht bekannt -> Ergebnis ist die bestmoegliche Situation (Obergrenze).

Ergebnis: NEUE Datei Documents\BORS_V7_QA\netzmaster\BORS_Abbiegen_V8_<zeit>.gpkg (Punktlayer abbiegen_v8 + Bericht).
Der Router V8 liest die neueste Datei automatisch.

STARTEN (QGIS-Konsole oder Python 3):
    from pathlib import Path
    p = Path.home() / 'Downloads' / 'BORS_AKTUELL' / '22_Abbiegen_Schleppkurven.py'
    exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'))
Dauer: ca. 30-60 min (Fortschritt in der Konsole). Optional vorher BORS_ABBIEGEN_MAX_KNOTEN = 300 fuer einen Schnelltest.
"""
import math
import sqlite3
import struct
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import numpy as np

HOME = Path(globals().get('BORS_HOME', Path.home()))
DOC = HOME / 'Documents'
AKT = Path(globals().get('BORS_AKTUELL', HOME / 'Downloads' / 'BORS_AKTUELL'))
NMDIR = DOC / 'BORS_V7_QA' / 'netzmaster'
STAMP = datetime.now().strftime('%Y%m%d_%H%M')
MAXK = int(globals().get('BORS_ABBIEGEN_MAX_KNOTEN', 0))
for _m in ('bors_geo.py', 'bors_bewertung_v8.py', 'bors_schleppkurve.py'):
    exec(compile((AKT / _m).read_text(encoding='utf-8'), str(AKT / _m), 'exec'))
FZ = lade_fahrzeuge(AKT / 'BORS_Fahrzeuge_V1.csv')
FAHRZEUGE = ['NEF', 'RTW', 'CTLF', 'ADL', 'TLF14', 'GTLF16', 'WAWE']
REP = []
T0 = time.time()
try:
    from qgis.PyQt.QtWidgets import QApplication
except Exception:
    QApplication = None


def log(m):
    print('BORS ABBIEGEN:', m); REP.append(str(m))


nm = sorted(NMDIR.glob('BORS_Netzmaster_V8_*.gpkg'), key=lambda p: p.stat().st_mtime)
if not nm:
    raise RuntimeError('Kein Netzmaster V8 - zuerst 21_Netzmaster_V8.py')
NM = nm[-1]
mop = sorted((DOC / 'BORS_V5').glob('mopube_v5_*.gpkg'), key=lambda p: p.stat().st_mtime)
if not mop:
    raise RuntimeError('mopube_v5_*.gpkg (AV-Strassenflaechen) fehlt in Documents\\BORS_V5')
log('Netz {} | Flaechen {}'.format(NM.name, mop[-1].name))

# ------------------------------------------------------------------ Flaechen
P = {1: [], 7: []}; IDX = {1: Raster(200.0), 7: Raster(200.0)}
c = sqlite3.connect('file:{}?mode=ro'.format(mop[-1].as_posix()), uri=True)
for g, art in c.execute('select geom, art from flaechen'):
    k = 1 if art == 1 else 7
    for poly in ringe(g):
        a = np.asarray(poly[0])
        IDX[k].add(len(P[k]), a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max())
        P[k].append(poly)
c.close()
log('AV-Flaechen: Strasse/Weg {} | uebrige befestigte {}'.format(len(P[1]), len(P[7])))

# ------------------------------------------------------------------ Netz
c = sqlite3.connect('file:{}?mode=ro'.format(NM.as_posix()), uri=True)
SRS = c.execute('select srs_name, srs_id, organization, organization_coordsys_id, definition, description from gpkg_spatial_ref_sys').fetchall()
SEG = {}
for sid, g, name, hw, zone, ot, d in c.execute('select seg_id, geom, name, highway_type, zone, other_tags, direction_osm from netz_v5 where ist_routingtyp = 1'):
    ls = linien(g)
    if not ls:
        continue
    SEG[sid] = dict(pts=ls[0], name=name or '', hw=hw, zone=zone, kreisel=('roundabout' in (ot or '') or 'circular' in (ot or '')),
                    fw=(d or 'BOTH') in ('BOTH', 'FORWARD'), bw=(d or 'BOTH') in ('BOTH', 'BACKWARD'))
c.close()
ENDS = defaultdict(list)
for sid, s in SEG.items():
    l = s['pts']
    ENDS[(round(l[0][0], 2), round(l[0][1], 2))].append((sid, 'start'))
    ENDS[(round(l[-1][0], 2), round(l[-1][1], 2))].append((sid, 'ende'))


def achse(sid, ende, zum_knoten, laenge_m=25.0):
    pts = SEG[sid]['pts']; L = laenge(pts)
    if ende == 'ende':
        s0 = max(0.0, L - laenge_m); q = [punkt_bei(pts, x)[0] for x in np.linspace(s0, L, max(2, int((L - s0)) + 1))]
    else:
        s1 = min(L, laenge_m); q = [punkt_bei(pts, x)[0] for x in np.linspace(0, s1, max(2, int(s1) + 1))]
    if (zum_knoten and ende == 'start') or (not zum_knoten and ende == 'ende'):
        q = q[::-1]
    return q


def winkel(ain, aout):
    a = np.asarray(ain[-min(len(ain), 11):]); b = np.asarray(aout[:min(len(aout), 11)])
    u1 = a[-1] - a[0]; u2 = b[-1] - b[0]
    return math.degrees(math.atan2(u1[0] * u2[1] - u1[1] * u2[0], u1[0] * u2[0] + u1[1] * u2[1]))


# Fahrbeziehungen an Knoten
aufgaben = []          # (x, y, art, in_seg, in_end, out_seg, out_end, ain, aout, winkel)
for node, lst in ENDS.items():
    if len(lst) < 2 or not any(SEG[s]['zone'] == 'BEWERTUNG' for s, _ in lst):
        continue
    for s1, e1 in lst:
        if not (SEG[s1]['fw'] if e1 == 'ende' else SEG[s1]['bw']):
            continue
        for s2, e2 in lst:
            if s1 == s2 or not (SEG[s2]['fw'] if e2 == 'start' else SEG[s2]['bw']):
                continue
            ain, aout = achse(s1, e1, True), achse(s2, e2, False)
            w = winkel(ain, aout)
            if abs(w) < 30:
                continue
            aufgaben.append((node[0], node[1], 'KNOTEN', s1, e1, s2, e2, ain, aout, w))
# starke Kurven innerhalb eines Abschnitts (Richtungsaenderung >= 45 Grad ueber +-10 m)
for sid, s in SEG.items():
    if s['zone'] != 'BEWERTUNG' or s['kreisel']:
        continue
    pts = s['pts']; L = laenge(pts)
    if L < 25:
        continue
    pos = np.arange(10.0, L - 10.0, 2.0)
    if not len(pos):
        continue
    hd = []
    for x in pos:
        a = punkt_bei(pts, x - 10)[0]; b = punkt_bei(pts, x)[0]; cpt = punkt_bei(pts, x + 10)[0]
        u1 = (b[0] - a[0], b[1] - a[1]); u2 = (cpt[0] - b[0], cpt[1] - b[1])
        hd.append(abs(math.degrees(math.atan2(u1[0] * u2[1] - u1[1] * u2[0], u1[0] * u2[0] + u1[1] * u2[1]))))
    hd = np.asarray(hd)
    i = 0
    while i < len(hd):
        if hd[i] >= 45:
            j = i
            while j + 1 < len(hd) and hd[j + 1] >= 45:
                j += 1
            k = i + int(np.argmax(hd[i:j + 1]))
            x = pos[k]; b = punkt_bei(pts, x)[0]
            ain = [punkt_bei(pts, t)[0] for t in np.linspace(max(0, x - 25), x, 26)]
            aout = [punkt_bei(pts, t)[0] for t in np.linspace(x, min(L, x + 25), 26)]
            if s['fw']:
                aufgaben.append((b[0], b[1], 'KURVE', sid, 'mitte', sid, 'mitte', ain, aout, winkel(ain, aout)))
            if s['bw']:
                aufgaben.append((b[0], b[1], 'KURVE', sid, 'mitte_rueck', sid, 'mitte_rueck', aout[::-1], ain[::-1], winkel(aout[::-1], ain[::-1])))
            i = j + 1
        else:
            i += 1
log('Fahrbeziehungen >= 30 Grad: {} (davon Kurven in Abschnitten {})'.format(len(aufgaben), sum(1 for a in aufgaben if a[2] == 'KURVE')))
by_node = defaultdict(list)
for a in aufgaben:
    by_node[(round(a[0], 1), round(a[1], 1))].append(a)
knoten = list(by_node)
if MAXK:
    import random
    random.Random(1).shuffle(knoten); knoten = knoten[:MAXK]

# ------------------------------------------------------------------ Simulation
erg = []
stat = Counter()
SCHLECHT = ('UNMOEGLICH', 'NUR_MIT_NEBENFLAECHE')
stat_k = Counter()


def kalibriere(rec):
    """Negativkontrolle je Ort: scheitert schon der Personenwagen (NEF) an einer Stelle, die Autos taeglich befahren,
    liegt ein Datenfehler vor (Flaeche fehlt, Hofeinfahrt nicht kartiert). Dann ist die Simulation dort fuer KEIN
    Fahrzeug belastbar -> NICHT_BELASTBAR (Router: kein Zuschlag, nur Hinweis). Rohwert bleibt in roh_<fz>."""
    for f in FAHRZEUGE:
        rec['roh_' + f] = rec['s_' + f]
    rec['kontrolle'] = ''
    if 'NEF' in FAHRZEUGE and rec['s_NEF'] in SCHLECHT:
        rec['kontrolle'] = 'NEF_SCHEITERT'
        for f in FAHRZEUGE:
            if rec['s_' + f] in SCHLECHT + ('ENG',):
                rec['s_' + f] = 'NICHT_BELASTBAR'


for kn_i, kn in enumerate(knoten, 1):
    cx, cy = kn
    p1 = [P[1][i] for i in IDX[1].nahe(cx - 45, cy - 45, cx + 45, cy + 45)]
    p7 = [P[7][i] for i in IDX[7].nahe(cx - 45, cy - 45, cx + 45, cy + 45)]
    m1, x0, y0 = maske(cx, cy, p1)
    m7, _, _ = maske(cx, cy, p7)
    ma = m1 | m7
    for (x, y, art, s1, e1, s2, e2, ain, aout, w) in by_node[kn]:
        serv = SEG[s1]['hw'] == 'service' or SEG[s2]['hw'] == 'service'
        rec = dict(x=x, y=y, art=art, in_seg=s1, in_ende=e1, out_seg=s2, out_ende=e2, winkel=round(w, 1),
                   strasse_in=SEG[s1]['name'], strasse_out=SEG[s2]['name'], zufahrt=int(serv))
        if SEG[s1]['kreisel'] or SEG[s2]['kreisel']:
            for f in FAHRZEUGE:
                rec['s_' + f] = 'KREISEL'
        elif abs(w) > 120:
            for f in FAHRZEUGE:
                rec['s_' + f] = 'SPITZKEHRE'
        else:
            ms = ma if serv else m1
            for f in FAHRZEUGE:
                rec['s_' + f] = bewerte_fahrt(ain, aout, FZ[f], ms, ma, x0, y0)[0]
        for f in FAHRZEUGE:
            stat[(f, 'Zufahrt' if serv else 'oeffentlich', rec['s_' + f])] += 1
        kalibriere(rec)
        for f in FAHRZEUGE:
            stat_k[(f, 'Zufahrt' if serv else 'oeffentlich', rec['s_' + f])] += 1
        erg.append(rec)
    if kn_i % 250 == 0:
        el = time.time() - T0
        print('BORS ABBIEGEN: {}/{} Knoten | {:.0f} s | Rest ca. {:.0f} min'.format(kn_i, len(knoten), el, el / kn_i * (len(knoten) - kn_i) / 60))
        if QApplication:
            try:
                QApplication.processEvents()
            except Exception:
                pass

# ------------------------------------------------------------------ Schreiben (neue GPKG, Punktlayer)
OUT = NMDIR / 'BORS_Abbiegen_V8_{}.gpkg'.format(STAMP)
o = sqlite3.connect(str(OUT))
o.execute('PRAGMA application_id = 1196444487'); o.execute('PRAGMA user_version = 10200')
o.execute('CREATE TABLE gpkg_spatial_ref_sys (srs_name TEXT NOT NULL, srs_id INTEGER PRIMARY KEY, organization TEXT NOT NULL, '
          'organization_coordsys_id INTEGER NOT NULL, definition TEXT NOT NULL, description TEXT)')
for r in SRS:
    o.execute('insert into gpkg_spatial_ref_sys values (?,?,?,?,?,?)', r)
o.execute("CREATE TABLE gpkg_contents (table_name TEXT NOT NULL PRIMARY KEY, data_type TEXT NOT NULL, identifier TEXT UNIQUE, "
          "description TEXT DEFAULT '', last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), "
          "min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE, srs_id INTEGER)")
o.execute('CREATE TABLE gpkg_geometry_columns (table_name TEXT NOT NULL, column_name TEXT NOT NULL, geometry_type_name TEXT NOT NULL, '
          'srs_id INTEGER NOT NULL, z TINYINT NOT NULL, m TINYINT NOT NULL, CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name))')
felder = ['art', 'in_seg', 'in_ende', 'out_seg', 'out_ende', 'winkel', 'strasse_in', 'strasse_out', 'zufahrt', 'kontrolle'] + ['s_' + f for f in FAHRZEUGE] + ['roh_' + f for f in FAHRZEUGE]
o.execute('CREATE TABLE abbiegen_v8 (fid INTEGER PRIMARY KEY AUTOINCREMENT, geom POINT, {})'.format(
    ', '.join('"{}" {}'.format(f, 'REAL' if f == 'winkel' else 'INTEGER' if f == 'zufahrt' else 'TEXT') for f in felder)))
if erg:
    xs = [r['x'] for r in erg]; ys = [r['y'] for r in erg]
    o.execute("insert into gpkg_contents (table_name, data_type, identifier, description, min_x, min_y, max_x, max_y, srs_id) "
              "values ('abbiegen_v8','features','BORS Abbiegen V8','Schleppkurven je Fahrzeug',?,?,?,?,2056)", (min(xs), min(ys), max(xs), max(ys)))
o.execute("insert into gpkg_geometry_columns values ('abbiegen_v8','geom','POINT',2056,0,0)")


def gp_punkt(x, y):
    return b'GP' + bytes([0, 1]) + struct.pack('<i', 2056) + struct.pack('<BIdd', 1, 1, x, y)


o.executemany('insert into abbiegen_v8 (geom, {}) values (?, {})'.format(', '.join('"{}"'.format(f) for f in felder), ','.join('?' * len(felder))),
              [[gp_punkt(r['x'], r['y'])] + [r[f] for f in felder] for r in erg])
o.execute("CREATE TABLE bors_meta (schluessel TEXT, wert TEXT)")
o.executemany('insert into bors_meta values (?,?)', [('netz', NM.name), ('erstellt', STAMP), ('fahrzeuge', ','.join(FAHRZEUGE)),
                                                     ('methode', 'bors_schleppkurve.py: Vorderachse Kandidatenbahn, Hinterachse Traktrix, Raster 0.25 m, Schliessen 1.5 m, Reserve 0.25 m'),
                                                     ('kalibrierung', 'NEF scheitert am Ort -> NICHT_BELASTBAR fuer alle Fahrzeuge (Rohwerte roh_<fz>)')])
o.commit(); o.close()
log('')
log('Ergebnis je Fahrzeug (Fahrbeziehungen 30-120 Grad):')
for f in FAHRZEUGE:
    for typ in ('oeffentlich', 'Zufahrt'):
        tot = sum(v for k, v in stat.items() if k[0] == f and k[1] == typ and k[2] not in ('KREISEL', 'SPITZKEHRE'))
        if tot:
            log('  {:<7} {:<11} OK {:>5.1%} | ENG {:>5.1%} | nur mit Nebenflaeche {:>5.1%} | UNMOEGLICH {:>5.1%} | keine Daten {:>5.1%}  (n={})'.format(
                f, typ, *(stat[(f, typ, s)] / tot for s in ('OK', 'ENG', 'NUR_MIT_NEBENFLAECHE', 'UNMOEGLICH', 'KEINE_DATEN')), tot))
log('')
log('Nach Negativkontrolle je Ort (NEF scheitert -> NICHT_BELASTBAR fuer alle):')
for f in FAHRZEUGE:
    for typ in ('oeffentlich', 'Zufahrt'):
        tot = sum(v for k, v in stat_k.items() if k[0] == f and k[1] == typ and k[2] not in ('KREISEL', 'SPITZKEHRE'))
        if tot:
            log('  {:<7} {:<11} OK {:>5.1%} | ENG {:>5.1%} | nur mit Nebenflaeche {:>5.1%} | UNMOEGLICH {:>5.1%} | nicht belastbar {:>5.1%} | keine Daten {:>5.1%}'.format(
                f, typ, *(stat_k[(f, typ, s)] / tot for s in ('OK', 'ENG', 'NUR_MIT_NEBENFLAECHE', 'UNMOEGLICH', 'NICHT_BELASTBAR', 'KEINE_DATEN'))))
tot = sum(v for k, v in stat.items() if k[0] == 'NEF' and k[1] == 'oeffentlich' and k[2] not in ('KREISEL', 'SPITZKEHRE', 'KEINE_DATEN'))
log('NEGATIVKONTROLLE NEF (Personenwagen) auf oeffentlichen Strassen: UNMOEGLICH {:.1%} -> geschaetzte Quote falscher Warnungen des Modells'.format(
    stat[('NEF', 'oeffentlich', 'UNMOEGLICH')] / max(tot, 1)))
log('Fertig in {:.0f} min: {}'.format((time.time() - T0) / 60, OUT))
(NMDIR / (OUT.stem + '_BERICHT.txt')).write_text('\n'.join(REP), encoding='utf-8')
