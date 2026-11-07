# -*- coding: utf-8 -*-
r"""BORS Bern - 16 (V3_BORS, 5.11.2026): Baustellen, Installationsplaetze und Polleranlagen der STADT BERN (Geoportal).
Wie 16_Stadt_Bern_Live_V2 (Logik unveraendert), neu:
 - Pfade aus bors_pfade.py: Netz = neuester Netzmaster V9 in P_AKTUELL (Tabelle netz_v5), ASTRA-Quelle = neueste reine
   ASTRA-Datei baustellen_JJJJMMTT_HHMM.gpkg in P_BAUSTELLEN, Ausgabe = P_BAUSTELLEN/baustellen_<zeit>_stadt.gpkg.
 - Daten wahlweise aus einem Abruf von 30_Stadt_Geoportal_Abruf_BORS.py (Global BORS_GEOPORTAL_ORDNER oder, wenn nicht
   gesetzt, der neueste Ordner Stadt_Bern/Geoportal_*), sonst live wie V2 (BORS_GEOPORTAL_ORDNER = 'live').
 - Bricht ab, wenn die Zieldatei schon existiert.

STARTEN (normales Python oder QGIS-Python-Konsole):
    python 01_Skripte/Aktuell/16_Stadt_Bern_Live_V3_BORS.py
Danach liest der Router (7_Router_V9_2f_BORS) automatisch die neueste Baustellendatei inkl. Stadt Bern und stadt_poller.

ERGEBNIS: Kopie der neuesten ASTRA-Baustellendatei PLUS
 - Stadt-Bern-Baustellen und -Installationsplaetze, die zum BORS_ZEITPUNKT (Standard jetzt) gueltig sind ODER spaeter
   beginnen (der Router filtert nach seinem BORS_ZEITPUNKT), als Meldungen (Umriss) und betroffene Netzsegmente
   (lage_quelle = STADT_BERN_POLYGON),
 - Tabelle stadt_poller: gesteuerte Poller/Schranken mit naechstem Netzsegment und Zufahrtsregel.
Es werden KEINE Personendaten (Bauherrschaft, Bauleitung, Telefon) uebernommen.
Restbreite ist in den Stadtdaten nicht angegeben -> Router: Aufschlag x1.5, keine Sperre.
"""
import json
import math
import re
import shutil
import sqlite3
import struct
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

_BR = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
exec(compile((_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py').read_text(encoding='utf-8'), str(_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py'), 'exec'))
BASE = 'https://map.bern.ch/arcgis/rest/services/Geoportal/'
ZEIT = globals().get('BORS_ZEITPUNKT') or datetime.now().strftime('%Y-%m-%dT%H:%M')
FELDER = 'Locality,Project,Startdate,Enddate,Displaynumber,Statustxt'
MIN_UEBERLAPP_M = 5.0
REP = []


def log(m):
    print('BORS STADT BERN:', m); REP.append(str(m))


def hole(pfad, felder):
    url = '{}{}/query?where=1%3D1&outFields={}&outSR=2056&geometryPrecision=1&f=geojson'.format(BASE, pfad, felder)
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'BFH-BCS-BORS'}), timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))['features']


def iso(ms):
    return datetime.fromtimestamp(ms / 1000.0).strftime('%Y-%m-%dT%H:%M') if ms else ''


# ------------------------------------------------------------------ Geometrie-Helfer (ohne GDAL)
def wkb_linie(blob):
    b = bytes(blob); o = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(b[3] >> 1) & 7]
    bo = '<' if b[o] == 1 else '>'; t = struct.unpack(bo + 'I', b[o + 1:o + 5])[0]; o += 5
    dim = 3 if (t // 1000 in (1, 2) or t & 0x80000000) else 2
    n = struct.unpack(bo + 'I', b[o:o + 4])[0]; o += 4
    return [struct.unpack(bo + 'd' * dim, b[o + 8 * dim * i:o + 8 * dim * (i + 1)])[:2] for i in range(n)]


def gp_linie(pts):
    wkb = struct.pack('<BII', 1, 2, len(pts)) + b''.join(struct.pack('<dd', x, y) for x, y in pts)
    return b'GP' + bytes([0, 1]) + struct.pack('<i', 2056) + wkb


def ringe(g):
    if g['type'] == 'Polygon':
        return [g['coordinates']]
    if g['type'] == 'MultiPolygon':
        return g['coordinates']
    return []


def in_poly(x, y, polys):
    for rings in polys:
        ins = False
        for r in rings:
            for i in range(len(r) - 1):
                (x1, y1), (x2, y2) = r[i][:2], r[i + 1][:2]
                if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                    ins = not ins
        if ins:
            return True
    return False


def dist_rand(x, y, polys):
    best = 1e9
    for rings in polys:
        for r in rings:
            for (ax, ay), (bx, by) in zip([p[:2] for p in r], [p[:2] for p in r[1:]]):
                dx, dy = bx - ax, by - ay; l2 = dx * dx + dy * dy
                t = 0 if l2 == 0 else max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / l2))
                best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


# ------------------------------------------------------------------ Eingaben
NM = sorted(P_AKTUELL.glob('BORS_Netzmaster_V9_*.gpkg'))
if not NM:
    raise FileNotFoundError('Kein Netzmaster V9 in {}'.format(P_AKTUELL))
NM = NM[-1]
BAU = sorted(p for p in P_BAUSTELLEN.glob('baustellen_*.gpkg') if re.fullmatch(r'baustellen_\d{8}_\d{4}\.gpkg', p.name))
if not BAU:
    raise FileNotFoundError('Keine ASTRA-Baustellendatei in {}'.format(P_BAUSTELLEN))
QUELLE = BAU[-1]
OUT = P_BAUSTELLEN / 'baustellen_{}_stadt.gpkg'.format(datetime.now().strftime('%Y%m%d_%H%M'))
if OUT.exists():
    raise FileExistsError('Zieldatei existiert schon (nichts ueberschreiben): {}'.format(OUT))
daten = globals().get('BORS_STADT_DATEN')          # nur fuer Tests: vorab geladene GeoJSON-Features
ORDNER = globals().get('BORS_GEOPORTAL_ORDNER')
if daten is None and ORDNER != 'live':
    kand = sorted(d for d in P_STADT.glob('Geoportal_*') if (d / 'baustellen.geojson').exists())
    ORDNER = Path(ORDNER) if ORDNER else (kand[-1] if kand else None)
    if ORDNER is not None:
        lies = lambda n: json.loads((Path(ORDNER) / (n + '.geojson')).read_text(encoding='utf-8'))['features']
        daten = {'bs': lies('baustellen'), 'ip': lies('installationsplaetze'), 'po': lies('polleranlagen')}
        log('Quelle: Abruf {}'.format(Path(ORDNER).name))
if daten is None:
    daten = {'bs': hole('Baustellen_2/MapServer/2', FELDER), 'ip': hole('Baustellen_2/MapServer/1', FELDER),
             'po': hole('Polleranlagen_Schranken/MapServer/0', 'Name,Typ_beschrieb,Bemerkung,Ausnahmen_vom_Fahrverbot')}
    log('Quelle: Geoportal live')
log('Netz: {} | ASTRA-Quelle: {}'.format(NM.name, QUELLE.name))
log('Geoportal Stadt Bern: {} Baustellen, {} Installationsplaetze, {} Polleranlagen (gesamt)'.format(
    len(daten['bs']), len(daten['ip']), len(daten['po'])))

db = sqlite3.connect(str(NM))
seg, blob, grid = {}, {}, defaultdict(set)
G = 50.0
for sid, name, g in db.execute('select seg_id, name, geom from netz_v5 where ist_routingtyp = 1'):
    pts = wkb_linie(g)
    seg[sid] = (name or '', pts); blob[sid] = g
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        for t in (0, 0.5, 1):
            grid[(int((x1 + t * (x2 - x1)) // G), int((y1 + t * (y2 - y1)) // G))].add(sid)
db.close()


def kandidaten(xmin, ymin, xmax, ymax):
    out = set()
    for i in range(int(xmin // G) - 1, int(xmax // G) + 2):
        for j in range(int(ymin // G) - 1, int(ymax // G) + 2):
            out |= grid.get((i, j), set())
    return out


def ueberlappung(pts, polys):
    """Laenge des Segments innerhalb der Flaeche (+1 m Rand), Stichprobe alle 2 m."""
    L = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        d = math.hypot(x2 - x1, y2 - y1); n = max(1, int(d / 2.0))
        for k in range(n):
            t = (k + 0.5) / n
            x, y = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
            if in_poly(x, y, polys) or dist_rand(x, y, polys) <= 1.0:
                L += d / n
    return L


# ------------------------------------------------------------------ Baustellen + Installationsplaetze
meld, segz = [], []
stat = Counter()
for art, feats in (('Baustelle Stadt Bern', daten['bs']), ('Installationsplatz Stadt Bern', daten['ip'])):
    for f in feats:
        p = f['properties']; von, bis = iso(p.get('Startdate')), iso(p.get('Enddate'))
        if bis and bis < ZEIT:
            stat[art + ' bereits beendet'] += 1
            continue
        if von and von > ZEIT:
            stat[art + ' beginnt spaeter (mitgespeichert, Router filtert nach BORS_ZEITPUNKT)'] += 1
        polys = ringe(f['geometry'])
        if not polys:
            continue
        xs = [c[0] for poly in polys for r in poly for c in r]; ys = [c[1] for poly in polys for r in poly for c in r]
        betroffen = []
        for sid in kandidaten(min(xs), min(ys), max(xs), max(ys)):
            L = ueberlappung(seg[sid][1], polys)
            if L >= MIN_UEBERLAPP_M or (L > 0 and L >= 0.5 * sum(math.dist(a, b) for a, b in zip(seg[sid][1], seg[sid][1][1:]))):
                betroffen.append((sid, L))
        sit = 'STADTBERN:{}'.format(p.get('Displaynumber') or '?')
        text = '{}: {} ({}), gueltig {} bis {} | Quelle Geoportal Stadt Bern, Restbreite nicht angegeben'.format(
            art, p.get('Project') or '', p.get('Locality') or '', von[:10], bis[:10])
        meld.append((gp_linie([tuple(c[:2]) for c in polys[0][0]]), sit, art, 1, von, bis, None, 'nicht angegeben',
                     'STADT_BERN_POLYGON', '', len(betroffen), text[:500]))
        for sid, L in betroffen:
            segz.append((blob[sid], sid, seg[sid][0], sit, art, 1, bis, None, text[:300]))
        stat[art + (' gueltig' if not (von and von > ZEIT) else ' kuenftig')] += 1
        stat[art + ' mit Netzsegmenten'] += 1 if betroffen else 0
log('Zeitpunkt {}: {}'.format(ZEIT, dict(stat)))
log('Betroffene Netzsegmente (Stadt Bern): {}'.format(len({s[1] for s in segz})))

# ------------------------------------------------------------------ Polleranlagen
poller = []
for f in daten['po']:
    p = f['properties']; x, y = f['geometry']['coordinates'][:2]
    best = None
    for sid in kandidaten(x - 20, y - 20, x + 20, y + 20):
        pts = seg[sid][1]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            dx, dy = bx - ax, by - ay; l2 = dx * dx + dy * dy
            t = 0 if l2 == 0 else max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / l2))
            d = math.hypot(x - ax - t * dx, y - ay - t * dy)
            if best is None or d < best[0]:
                best = (d, sid)
    regel = p.get('Ausnahmen_vom_Fahrverbot') or ''
    poller.append(dict(name=p.get('Name') or '', typ=p.get('Typ_beschrieb') or '', bemerkung=p.get('Bemerkung') or '', regel=regel,
                       seg_id=best[1] if best and best[0] <= 15 else '', abstand_m=round(best[0], 1) if best else None,
                       dauersperre=1 if 'Dauersperre' in regel else 0, x=x, y=y))
log('Polleranlagen: {} | einem Netzsegment zugeordnet (<= 15 m): {} | Dauersperre: {}'.format(
    len(poller), sum(1 for p in poller if p['seg_id']), sum(p['dauersperre'] for p in poller)))

# ------------------------------------------------------------------ Ausgabe: neue Baustellendatei
shutil.copyfile(str(QUELLE), str(OUT))
o = sqlite3.connect(str(OUT))


def _pts(b):
    try:
        return wkb_linie(b)
    except Exception:
        return []


o.create_function('ST_IsEmpty', 1, lambda b: 0 if b is not None and _pts(b) else 1, deterministic=True)
for _n, _i, _f in (('ST_MinX', 0, min), ('ST_MaxX', 0, max), ('ST_MinY', 1, min), ('ST_MaxY', 1, max)):
    o.create_function(_n, 1, (lambda i, f: (lambda b: f(p[i] for p in _pts(b)) if b is not None and _pts(b) else None))(_i, _f), deterministic=True)
o.executemany('INSERT INTO meldungen (geom, situation_id, typ, aktiv, von, bis, restbreite_m, restbreite_hinweis, lage_quelle, '
              'strasse_nr, anzahl_segmente, text) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', meld)
o.executemany('INSERT INTO segmente (geom, seg_id, strasse, situation_id, typ, aktiv, bis, restbreite_m, text) VALUES (?,?,?,?,?,?,?,?,?)', segz)
o.execute('DROP TABLE IF EXISTS stadt_poller')
o.execute('CREATE TABLE stadt_poller (fid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, typ TEXT, bemerkung TEXT, regel TEXT, seg_id TEXT, '
          'abstand_m REAL, dauersperre INTEGER, x REAL, y REAL)')
o.executemany('INSERT INTO stadt_poller (name, typ, bemerkung, regel, seg_id, abstand_m, dauersperre, x, y) VALUES (?,?,?,?,?,?,?,?,?)',
              [(p['name'], p['typ'], p['bemerkung'], p['regel'], p['seg_id'], p['abstand_m'], p['dauersperre'], p['x'], p['y']) for p in poller])
o.execute('DELETE FROM gpkg_contents WHERE table_name = ?', ('stadt_poller',))
o.execute("INSERT INTO gpkg_contents (table_name, data_type, identifier, last_change) VALUES ('stadt_poller', 'attributes', 'Polleranlagen Stadt Bern', ?)",
          (datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),))
o.commit()
n_s = o.execute("select count(*) from segmente where situation_id like 'STADTBERN:%'").fetchone()[0]
chk = o.execute('pragma integrity_check').fetchone()[0]
o.close()
log('Geschrieben: {} (ASTRA-Datei {} + {} Stadt-Segmentzeilen) | Pruefung: {}'.format(OUT.name, QUELLE.name, n_s, chk))
log('Jetzt in QGIS 7_Router_V9_2f_BORS starten (liest die neueste Baustellendatei inkl. Stadt Bern und stadt_poller).')
(P_BAUSTELLEN / (OUT.stem + '_STADT_BERICHT.txt')).write_text('\n'.join(REP), encoding='utf-8')
