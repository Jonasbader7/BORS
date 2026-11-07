# -*- coding: utf-8 -*-
r"""BORS 31 (5.11.2026): Baustellen in netz.json der Web-App auf einen neuen Stand bringen.
Laeuft in normalem Python (kein QGIS):
    python 01_Skripte/Aktuell/31_Web_Baustellen_BORS.py
Warum: Die Web-App hat die Baustellen fest in netz.json (bisher Stand 28.10.2026); 29_Web_Netz uebernimmt sie unveraendert.
QGIS liest dagegen die neueste baustellen_*.gpkg und filtert nach Datum. Dieses Skript bringt die Web-App auf denselben
Stand wie QGIS zum gewaehlten Zeitpunkt.

Regeln (wie 7_Router_V9_2f_BORS._profil_kosten und lade_baustellen_datei):
  - aktiv = von <= ZEITPUNKT <= bis (auf Minuten); je Abschnitt zaehlt die kleinste Restbreite.
  - Faktor je Klasse A-D: Restbreite bekannt und < Profilbreite + 2 x 0.25 m -> x RISIKO_FAKTOR (2.0), sonst x1.5. REF ohne Faktor.
  - Kosten (Modus V und E) eines Abschnitts: alt / Faktor_alt * Faktor_neu. Gesperrte (0) bleiben 0.
  - bau-Liste neu: [Abschnitt, Restbreite, Quelle, Lage, bis, Text]; Text nur bei ASTRA (Stadt: leer wie bisher).
Prueft vorher: Jeder bisherige bau-Eintrag erklaert die Kosten (Kosten x Tempo / Faktor ergibt einen Faktor ohne Baustelle).
Globale: BORS_WEB_QUELLE (netz.json), BORS_WEB_ZIEL (neue netz.json, Ordner darf es noch nicht geben), BORS_BAU_DATEI, BORS_ZEITPUNKT.
Ausgabe: <Zielordner>/netz.json und <Zielordner>/netz_baustellen_aenderungen.csv.
"""
import csv
import json
import shutil
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

_BR = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
exec(compile((_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py').read_text(encoding='utf-8'), str(_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py'), 'exec'))

QUELLE = Path(globals().get('BORS_WEB_QUELLE', BORS_ROOT / '04_WebApp' / 'Entwicklung_V9_Netz_V9_2g' / 'netz.json'))
ZIEL = Path(globals().get('BORS_WEB_ZIEL', BORS_ROOT / '04_WebApp' / 'Entwicklung_V10_Baustellen_Vergleich' / 'netz.json'))
BAU_DATEI = Path(globals().get('BORS_BAU_DATEI') or sorted(P_BAUSTELLEN.glob('baustellen_*.gpkg'))[-1])
ZEITPUNKT = globals().get('BORS_ZEITPUNKT') or datetime.now().strftime('%Y-%m-%dT%H:%M')
BREITE = {'A': 2.20, 'B': 2.45, 'C': 2.90, 'D': 3.00}     # PROFILE[code]['width'] im Router
RESERVE, F_BAU, F_ENG = 0.25, 1.5, 2.0

if ZIEL.parent.exists():
    raise FileExistsError('Zielordner existiert schon (nichts ueberschreiben): {}'.format(ZIEL.parent))


def faktor(rb, c):
    if rb is None:
        return F_BAU
    return F_ENG if rb < BREITE[c] + 2 * RESERVE else F_BAU


D = json.loads(QUELLE.read_text(encoding='utf-8'))
ac = {c: i for i, c in enumerate(D['attr_cols'])}
sid2f = {a[ac['seg_id']]: f for f, a in enumerate(D['attr'])}
alt = {}
for b in D['bau']:
    f = b[0]
    if f not in alt or (b[1] is not None and (alt[f] is None or b[1] < alt[f])):
        alt[f] = b[1]

# Pruefung der bisherigen Datei: ohne Baustellenfaktor muss ein gewohnter Faktor uebrig bleiben
erlaubt = set()
for f, a in enumerate(D['attr']):
    if f in alt:
        continue
    for m in 'VE':
        for c in 'ABCD':
            k = D['kosten'][m][c][f]
            if k:
                erlaubt.add(round(k * a[ac['speed']] / 3.6, 3))
fehl = 0
for f, rb in alt.items():
    for m in 'VE':
        for c in 'ABCD':
            k = D['kosten'][m][c][f]
            if k and round(k * D['attr'][f][ac['speed']] / 3.6 / faktor(rb, c), 3) not in erlaubt:
                fehl += 1
if fehl:
    raise RuntimeError('{} Kostenwerte lassen sich nicht als Basis x Baustellenfaktor erklaeren - Abbruch'.format(fehl))

# Neue Baustellen zum Zeitpunkt (wie lade_baustellen_datei im Router)
c = sqlite3.connect(str(BAU_DATEI))
mel = {r[0]: (r[1] or '', r[2] or '', r[3] or '') for r in c.execute('select situation_id, von, bis, lage_quelle from meldungen')}
neu, ausserhalb, ohne_abschnitt = {}, 0, 0
for seg, sit, bis, rb, txt in c.execute('select seg_id, situation_id, bis, restbreite_m, text from segmente'):
    von, bis2, lq = mel.get(sit, ('', bis or '', ''))
    bis = bis or bis2
    if (von and von[:16] > ZEITPUNKT) or (bis and bis[:16] < ZEITPUNKT):
        ausserhalb += 1
        continue
    f = sid2f.get(seg)
    if f is None:
        ohne_abschnitt += 1
        continue
    rb = float(rb) if rb not in (None, '') else None
    lage = 'TMC-Abschnitt, Lage ungenau' if lq == 'TMC' else ('Polygon Stadt Bern' if lq == 'STADT_BERN_POLYGON' else ('Koordinaten' if lq else 'Lage unbekannt'))
    stadt = str(sit).startswith('STADTBERN')
    eintrag = [f, rb, 'Stadt Bern Baustellen' if stadt else 'ASTRA Verkehrsinfo', lage, (bis or '')[:10], '' if stadt else (txt or '')[:160]]
    if f not in neu or (rb is not None and (neu[f][1] is None or rb < neu[f][1])):
        neu[f] = eintrag
c.close()

# Kosten anpassen
st = Counter()
for f in set(alt) | set(neu):
    fa = {cc: (faktor(alt[f], cc) if f in alt else 1.0) for cc in 'ABCD'}
    fn = {cc: (faktor(neu[f][1], cc) if f in neu else 1.0) for cc in 'ABCD'}
    for m in 'VE':
        for cc in 'ABCD':
            k = D['kosten'][m][cc][f]
            if k and fa[cc] != fn[cc]:
                D['kosten'][m][cc][f] = round(k / fa[cc] * fn[cc], 6)
                st['Kosten geaendert ({} {})'.format(m, cc)] += 1
zeilen = []
for f in sorted(set(alt) | set(neu)):
    art = 'weiter aktiv' if f in alt and f in neu else ('beendet' if f in alt else 'neu')
    st[art] += 1
    zeilen.append({'seg_id': D['attr'][f][ac['seg_id']], 'strasse': D['attr'][f][ac['name']] or '', 'aenderung': art,
                   'quelle_neu': neu[f][2] if f in neu else '', 'bis_neu': neu[f][4] if f in neu else '', 'restbreite_neu': neu[f][1] if f in neu else ''})
# Polleranlagen mit Dauersperre (Tabelle stadt_poller): der Router setzt den Abschnitt auf RESTRICTED -> REF gesperrt
# ("Zufahrt eingeschraenkt (ohne Sonderrecht)"), A-D Sonderrecht x1.2 (statt eines allfaelligen LKW-Faktors x1.2).
# Verglichen wird die Zuordnung der Baustellendatei, aus der die Quelle stammt (BORS_BAU_ALT), mit der neuen Datei.
BAU_ALT = globals().get('BORS_BAU_ALT') or (P_BAUSTELLEN / 'baustellen_20261027_2309_stadt.gpkg')
REF_TXT = 'Zufahrt eingeschraenkt (ohne Sonderrecht)'
SERVICE_DURCHFAHRT, LKW_AB_T, F_SONDER = {'driveway', 'parking_aisle', 'drive-through'}, 3.5, 1.2
HGV_HINWEIS = {'no', 'destination', 'delivery', 'private', 'agricultural', 'forestry', 'permit', 'discouraged'}
TONNEN = {'A': 3.1, 'B': 5.5, 'C': 18.0, 'D': 28.4}      # PROFILE[code]['tonnes'] im Router


def dauersperren(pfad):
    try:
        cc = sqlite3.connect(str(pfad))
        s = {r[0] for r in cc.execute("select seg_id from stadt_poller where seg_id <> '' and dauersperre = 1")}
        cc.close()
        return s
    except Exception:
        return set()


ds_alt, ds_neu = dauersperren(BAU_ALT), dauersperren(BAU_DATEI)
if ds_alt != ds_neu:
    import re
    nm = sorted(P_AKTUELL.glob('BORS_Netzmaster_V9_*.gpkg'))[-1]
    cc = sqlite3.connect('file:{}?mode=ro'.format(nm.as_posix()), uri=True)
    hgv = {}
    for sid, ot in cc.execute('select seg_id, other_tags from netz_v5 where seg_id in ({})'.format(','.join('?' * len(ds_alt ^ ds_neu))), list(ds_alt ^ ds_neu)):
        m = re.search(r'"hgv"\s*=>\s*"([^"]*)"', ot or '')
        hgv[sid] = m.group(1).lower() if m else ''
    cc.close()
    ti ={t: i for i, t in enumerate(D['texte'])}
    if REF_TXT not in ti:
        D['texte'].append(REF_TXT)
        ti[REF_TXT] = len(D['texte']) - 1
    for sid in sorted(ds_alt ^ ds_neu):
        f = sid2f.get(sid)
        if f is None or D['attr'][f][ac['access_class']] == 'RESTRICTED':
            continue                                    # schon ohne Poller eingeschraenkt: keine Aenderung
        a = D['attr'][f]
        lkw = {cc_: TONNEN[cc_] > LKW_AB_T and hgv.get(sid, '') in HGV_HINWEIS for cc_ in 'ABCD'}
        if sid in ds_alt:                               # Dauersperre entfaellt: REF wieder frei, A-D ohne Sonderrecht
            basis = (3.0 if a[ac['service_type']] in SERVICE_DURCHFAHRT else 1.0) / (a[ac['speed']] / 3.6)
            for m in 'VE':
                D['kosten'][m]['REF'][f] = round(basis, 6)
                D['aus'][m]['REF'][f] = 0
                for cc_ in 'ABCD':
                    if D['kosten'][m][cc_][f] and not lkw[cc_]:
                        D['kosten'][m][cc_][f] = round(D['kosten'][m][cc_][f] / F_SONDER, 6)
            art = 'Poller-Dauersperre entfaellt'
        else:                                           # neue Dauersperre: REF gesperrt, A-D Sonderrecht
            for m in 'VE':
                D['kosten'][m]['REF'][f] = 0
                D['aus'][m]['REF'][f] = ti[REF_TXT]
                for cc_ in 'ABCD':
                    if D['kosten'][m][cc_][f] and not lkw[cc_]:
                        D['kosten'][m][cc_][f] = round(D['kosten'][m][cc_][f] * F_SONDER, 6)
            art = 'Poller-Dauersperre neu'
        st[art] += 1
        zeilen.append({'seg_id': sid, 'strasse': a[ac['name']] or '', 'aenderung': art, 'quelle_neu': 'stadt_poller', 'bis_neu': '', 'restbreite_neu': ''})

D['bau'] = [neu[f] for f in sorted(neu)]
D['baustellen_stand'] = ZEITPUNKT
D['baustellen_quelle'] = BAU_DATEI.name

ZIEL.parent.mkdir(parents=True)
ZIEL.write_text(json.dumps(D, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
with open(ZIEL.parent / 'netz_baustellen_aenderungen.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=list(zeilen[0].keys()) if zeilen else ['leer'], delimiter=';')
    w.writeheader()
    w.writerows(zeilen)
print('BORS 31: {} -> {}'.format(QUELLE, ZIEL))
print('  Baustellendatei {} | Zeitpunkt {} | ausserhalb Gueltigkeit {} | ohne Abschnitt {}'.format(BAU_DATEI.name, ZEITPUNKT, ausserhalb, ohne_abschnitt))
print('  Abschnitte mit Baustelle: bisher {} -> neu {} | {}'.format(len(alt), len(neu), dict(st)))
