# -*- coding: utf-8 -*-
r"""BORS 29 (V9.2f_BORS, 1.11.2026): netz.json der Web-App auf den Stand eines Netzmasters V9 bringen (Status, Gruende, Kosten).
Laeuft in normalem Python (kein QGIS), z. B.:
    python 01_Skripte/Aktuell/29_Web_Netz_V9_2f_BORS.py
oder in der QGIS-Python-Konsole wie die anderen Skripte (exec).
Warum so: Das urspruengliche Exportskript (Netz V9.2b -> netz.json) ist nicht in der Ablage. Graph, Geometrie, Hindernisse,
Abbiegen, Baustellen und REF bleiben deshalb aus der bestehenden netz.json; neu geschrieben werden je Klasse A-D nur
kat, grund, aus (V/E), kosten (V/E) und die Breiten-Attribute - mit denselben Regeln wie 7_Router_V9_2e_BORS._profil_kosten:
  - OSM maxwidth/maxheight/maxweight oder "Zufahrt eingeschraenkt" sperrt unabhaengig vom Netzmaster -> unveraendert (kat 2)
  - Wachenareal (service bis WACHE_AREAL_M = 80 m um eine Wache): UNVALIDIERT gilt als validiert (Text "Wachenareal ...")
  - VALIDIERT:   kat 0, kosten V = E = Basis,     aus V/E leer
  - UNVALIDIERT: kat 1, kosten V = 0, E = 2*Basis, aus V = "nicht validiert: " + Grund[:120]
  - GESPERRT:    kat 2, kosten V = E = 0,         aus V/E = "Kat. 3: " + Grund[:120]
  Basis = bisherige Kosten (kat 0: V, kat 1: E/2). Fehlt sie (bisher gesperrt) oder ist die Sperre nur ein fester
  Hindernispunkt (Regel V7.5), bricht das Skript ab: dann braucht es das echte Exportskript.
Vorher prueft das Skript, dass die bestehende netz.json diese Regeln fuer jeden Abschnitt einhaelt.
Ausgabe: NEUER Ordner (Standard 04_WebApp/Entwicklung_V8_Netz_V9_2f/netz.json) + Bericht <ordner>/netz_aenderungen.csv.
"""
import csv
import json
import math
import sqlite3
from collections import Counter
from pathlib import Path

_BR = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
exec(compile((_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py').read_text(encoding='utf-8'), str(_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py'), 'exec'))

QUELLE = Path(globals().get('BORS_WEB_QUELLE', BORS_ROOT / '04_WebApp' / 'Entwicklung_V7_Fahrerwahl' / 'netz.json'))
ZIEL = Path(globals().get('BORS_WEB_ZIEL', BORS_ROOT / '04_WebApp' / 'Entwicklung_V8_Netz_V9_2f' / 'netz.json'))
NM = globals().get('BORS_NETZMASTER')
# neuester nach Zeitstempel im Namen (nicht nach Aenderungsdatum: QGIS schreibt beim Oeffnen in aeltere Dateien)
NM = Path(NM) if NM else sorted(P_AKTUELL.glob('BORS_Netzmaster_V9_2*.gpkg'), key=lambda p: p.stem.split('_V9_')[1])[-1]
WACHE_AREAL_M, RISIKO = 80.0, 2.0
KAT = {'VALIDIERT': 0, 'UNVALIDIERT': 1, 'GESPERRT': 2}
WACHE_TXT = 'Wachenareal (Fahrzeuge dort stationiert, taeglich befahren) | vorher: '

if ZIEL.exists():
    raise FileExistsError('{} existiert schon'.format(ZIEL))
D = json.loads(QUELLE.read_text(encoding='utf-8'))
T = D['texte']
tidx = {t: i for i, t in enumerate(T)}
assert D['konst']['RISIKO_FAKTOR'] == RISIKO


def text(t):
    if t not in tidx:
        tidx[t] = len(T); T.append(t)
    return tidx[t]


def stop_txt(c, f):
    return T[D['aus']['V'][c][f]].startswith(('OSM max', 'Zufahrt eingeschr'))


# 1. Regeln an der bestehenden Datei pruefen (muss fuer jeden Abschnitt gelten)
fehler = []
for c in 'ABCD':
    for f in range(len(D['attr'])):
        k, V, E = D['kat'][c][f], D['kosten']['V'][c][f], D['kosten']['E'][c][f]
        av, ae, g = T[D['aus']['V'][c][f]], T[D['aus']['E'][c][f]], T[D['grund'][c][f]]
        if stop_txt(c, f):
            ok = k == 2 and V == 0 and E == 0 and av == ae
        elif k == 0:
            ok = V > 0 and abs(V - E) < 1e-9 and av == '' and ae == ''
        elif k == 1:
            ok = V == 0 and E > 0 and av == 'nicht validiert: ' + g[:120] and ae == ''
        else:
            ok = V == 0 and E == 0 and av == ae == 'Kat. 3: ' + g[:120]
        if not ok:
            fehler.append((c, D['attr'][f][0]))
if fehler:
    raise RuntimeError('bestehende netz.json folgt den Regeln nicht: {} Faelle, z.B. {}'.format(len(fehler), fehler[:5]))

# 2. Wachenareal wie im Router (service, Abstand Wache -> Abschnitt <= 80 m)
ac = {c: i for i, c in enumerate(D['attr_cols'])}
pts = lambda f: [[(D['nodes'][2 * i] / 100, D['nodes'][2 * i + 1] / 100) for i in p] for p in D['segs'][f][0]]


def abstand(parts, x, y):
    b = 1e18
    for P in parts:
        for i in range(len(P) - 1):
            (x1, y1), (x2, y2) = P[i], P[i + 1]; dx, dy = x2 - x1, y2 - y1; L2 = dx * dx + dy * dy
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2)) if L2 else 0
            b = min(b, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return b


WA = {f for f in range(len(D['attr'])) if D['attr'][f][ac['highway_type']] == 'service'
      and any(abstand(pts(f), w[1] / 100, w[2] / 100) <= WACHE_AREAL_M for w in D['wachen'])}
alt_wa = {f for c in 'ABCD' for f in range(len(D['attr'])) if T[D['grund'][c][f]].startswith('Wachenareal')}
assert alt_wa <= WA, 'Wachenareal weicht ab: {}'.format(sorted(alt_wa - WA)[:5])

# 3. Netzmaster lesen und uebertragen
db = sqlite3.connect('file:{}?mode=ro'.format(NM.as_posix()), uri=True)
NMD = {r[0]: r[1:] for r in db.execute('select seg_id, ' + ', '.join('{0}_v9_status, {0}_v9_grund, {0}_breite_v9, {0}_breite_v9_grund'.format(p) for p in 'abcd')
                                       + ' from netz_v5')}
meta = dict(db.execute('select schluessel, wert from bors_meta'))
prot, n = [], Counter()
for f, a in enumerate(D['attr']):
    sid = a[0]
    r = NMD[sid]
    for i, c in enumerate('ABCD'):
        st, g, br, brg = r[4 * i:4 * i + 4]
        g = g or ''
        k_neu = KAT[st]
        if f in WA and k_neu == 1:
            k_neu, g = 0, WACHE_TXT + g[:150]
        k_alt, g_alt = D['kat'][c][f], T[D['grund'][c][f]]
        bg_alt = a[ac[c + '_breite_grund']]                  # Begruendung als Verweis in texte (wie in der Quelle)
        if a[ac[c + '_breite']] != br or (T[bg_alt] if isinstance(bg_alt, int) else bg_alt) != (brg or ''):
            a[ac[c + '_breite']], a[ac[c + '_breite_grund']] = br, text(brg or ''); n[(c, 'Breite-Attribut')] += 1
        if stop_txt(c, f):                                   # OSM-Sperre / Zufahrt: Netzmaster aendert nichts
            if g != g_alt:
                D['grund'][c][f] = text(g); n['nur Text (OSM-Sperre bleibt)'] += 1
            continue
        if k_neu == k_alt and g == g_alt:
            continue
        if k_neu != k_alt:
            if k_alt == 2:
                raise RuntimeError('{} {}: bisher gesperrt, jetzt {} - Basiskosten unbekannt, echtes Exportskript noetig'.format(sid, c, st))
            if k_neu == 2 and g.startswith('Hindernis:'):
                raise RuntimeError('{} {}: Sperre durch Hindernis (Regel feste Sperre) - echtes Exportskript noetig'.format(sid, c))
        basis = D['kosten']['V'][c][f] if k_alt == 0 else D['kosten']['E'][c][f] / RISIKO
        if k_neu == 0:
            V = E = basis; av = ae = ''
        elif k_neu == 1:
            V, E = 0, basis * RISIKO; av, ae = 'nicht validiert: ' + g[:120], ''
        else:
            V = E = 0; av = ae = 'Kat. 3: ' + g[:120]
        D['kat'][c][f] = k_neu; D['grund'][c][f] = text(g)
        D['kosten']['V'][c][f] = round(V, 6) if V else 0; D['kosten']['E'][c][f] = round(E, 6) if E else 0
        D['aus']['V'][c][f] = text(av); D['aus']['E'][c][f] = text(ae)
        art = 'Status {}->{}'.format(k_alt, k_neu) if k_neu != k_alt else 'nur Text'
        n[(c, art)] += 1
        if k_neu != k_alt:
            prot.append([sid, a[ac['name']] or '', c, ['VALIDIERT', 'UNVALIDIERT', 'GESPERRT'][k_alt], ['VALIDIERT', 'UNVALIDIERT', 'GESPERRT'][k_neu], g[:200]])

D['version'] = 'V9.2f Netz / Router V9.2e'
D['netz'] = NM.name
ZIEL.parent.mkdir(parents=True, exist_ok=True)
ZIEL.write_text(json.dumps(D, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
with open(str(ZIEL.parent / 'netz_aenderungen.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh, delimiter=';'); w.writerow(['seg_id', 'name', 'klasse', 'vorher', 'nachher', 'grund_neu']); w.writerows(prot)
print('BORS 29: {} -> {} (Netzmaster {}, Befunde: {})'.format(QUELLE.name, ZIEL, NM.name, meta.get('v9_2f', '-')))
print('BORS 29: Wachenareal {} Abschnitte; Aenderungen: {}'.format(len(WA), dict(sorted(n.items(), key=str))))
print('BORS 29: Statuswechsel {} (Liste: netz_aenderungen.csv)'.format(len(prot)))
