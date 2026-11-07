# -*- coding: utf-8 -*-
r"""BORS 32 (6.11.2026): Parkfelder fuer die Web-App als Ebene exportieren (parkfelder.json).
Laeuft in normalem Python (kein QGIS, nur sqlite3):
    python 01_Skripte/Aktuell/32_Web_Parkfelder_BORS.py
Quelle: dieselbe Datei, die 25_Breite_V9_1 von der Fahrbahnbreite abzieht und die 6_Projekt in QGIS als
«Parkfelder (von der Breite abgezogen)» zeigt: P_VORSTUFEN / parkierung_v5_*.gpkg (Stadt Bern + OSM).
Nur zur Anzeige; Router und netz.json bleiben unveraendert. Keine Personendaten (Felder: quelle, art, lage).

Format (wie basis.json): {"x0","y0","kat":[Namen], "f":[[kat, ungenau, Ring1, Ring2, ...], ...]}
Ringe als flache Liste in Dezimetern relativ zu x0/y0, erster Punkt absolut, danach Differenzen.
Globale: BORS_PARK_DATEI (gpkg), BORS_WEB_ZIEL (parkfelder.json, darf es noch nicht geben).
"""
import json
import sqlite3
import struct
from collections import Counter
from pathlib import Path

_BR = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
exec(compile((_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py').read_text(encoding='utf-8'), str(_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py'), 'exec'))

PARK = Path(globals().get('BORS_PARK_DATEI') or sorted(P_VORSTUFEN.glob('parkierung_v5_*.gpkg'))[-1])
ZIEL = Path(globals().get('BORS_WEB_ZIEL', BORS_ROOT / '04_WebApp' / 'Entwicklung_V11_Parkfelder' / 'parkfelder.json'))
X0, Y0 = 2580000.0, 1180000.0          # Nullpunkt von netz.json / basis.json

KAT = ['Blaue Zone', 'Weiss / gebührenpflichtig', 'Spezialfelder (Gehbehinderte, Taxi, Car, LKW …)', 'OSM: Parkieren am Strassenrand']
WEISS = {'P weiss (APK)', 'P weiss (Kurzzeit)', 'nummeriert', 'nicht nummeriert'}

if ZIEL.exists():
    raise FileExistsError('Zieldatei existiert schon (nichts ueberschreiben): {}'.format(ZIEL))


def kategorie(quelle, art):
    if quelle == 'OSM':
        return 3
    if art == 'P blau (APK)':
        return 0
    return 1 if art in WEISS else 2


def polygone(blob):
    """GeoPackage-Blob -> Liste von Polygonen (Liste von Ringen mit (x, y)). Nur 2D (Multi)Polygon."""
    b = bytes(blob)
    if b[:2] != b'GP':
        raise ValueError('kein GeoPackage-Blob')
    env = (b[3] >> 1) & 7
    o = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[env]

    def lies(o):
        bo = '<' if b[o] == 1 else '>'
        typ = struct.unpack_from(bo + 'I', b, o + 1)[0]
        o += 5
        if typ == 3:
            nr = struct.unpack_from(bo + 'I', b, o)[0]; o += 4; ringe = []
            for _ in range(nr):
                n = struct.unpack_from(bo + 'I', b, o)[0]; o += 4
                ringe.append(list(struct.iter_unpack(bo + 'dd', b[o:o + 16 * n]))); o += 16 * n
            return [ringe], o
        if typ == 6:
            n = struct.unpack_from(bo + 'I', b, o)[0]; o += 4; alle = []
            for _ in range(n):
                p, o = lies(o); alle += p
            return alle, o
        raise ValueError('Geometrietyp {} nicht unterstuetzt'.format(typ))
    return lies(o)[0]


def ring_kodiert(ring):
    pts = [(round((x - X0) * 10), round((y - Y0) * 10)) for x, y in ring]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]                                    # Web schliesst den Ring selbst
    out, px, py = [], 0, 0
    for x, y in pts:
        if out and x == px and y == py:
            continue
        out += [x - px, y - py]; px, py = x, y
    return out


con = sqlite3.connect(str(PARK))
con.text_factory = lambda bt: bt.decode('utf-8', 'replace')
F, z = [], Counter()
for geom, quelle, art, lage in con.execute('SELECT geom, quelle, art, lage FROM parkierung'):
    if geom is None:
        continue
    k = kategorie(quelle or '', art or '')
    ungenau = 1 if (lage or '').startswith('ungenau') or quelle == 'OSM' else 0
    for poly in polygone(geom):
        ringe = [r for r in (ring_kodiert(r) for r in poly) if len(r) >= 6]
        if ringe:
            F.append([k, ungenau] + ringe); z[(KAT[k], ungenau)] += 1
con.close()

ZIEL.parent.mkdir(parents=True, exist_ok=True)
with open(ZIEL, 'w', encoding='utf-8') as fh:
    json.dump({'x0': X0, 'y0': Y0, 'quelle': PARK.name, 'kat': KAT, 'f': F}, fh, ensure_ascii=False, separators=(',', ':'))
print('BORS 32: {} Flaechen aus {} -> {} ({:.0f} kB)'.format(len(F), PARK.name, ZIEL, ZIEL.stat().st_size / 1024))
for (k, u), n in sorted(z.items()):
    print('  {:<60} {:<8} {:>5}'.format(k, 'ungenau' if u else 'genau', n))
