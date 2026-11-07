# -*- coding: utf-8 -*-
"""BORS 27 (V9.2c_BORS, 29.10.2026): identisch mit 27_QGIS_Test_V9_2c.py; Protokoll nach 05_Berichte/QA_Tests/tests.
STARTEN (QGIS-Python-Konsole, Ablage BORS):
    from pathlib import Path
    p = Path.home() / 'OneDrive' / 'Desktop' / 'BORS' / '01_Skripte' / 'Aktuell' / '27_QGIS_Test_V9_2c_BORS.py'
    exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'))
BORS 27: Oberflaechentest V9.1 in QGIS (P0-3). Voraussetzung: Projekt V9 offen, 7_Router_V9_2c.py gestartet.
Prueft ueber die echte Oberflaeche:
  1. Adresssuche mit Hausnummern (5 Adressen)
  2. 24 Routen A-D (Wache -> Adresse und Zufall), abwechselnd Modus validiert / experimentell (Haekchen)
  3. Banner: "VALIDIERTE ROUTE" / "VALIDIERT BIS ZUR ZUFAHRT" / "KEINE VALIDIERTE ROUTE" passt zum Ergebnis
  4. validierte Routen enthalten nur validierte Abschnitte; experimentelle weisen unvalidierte Meter aus
  5. wiederholte Kartenaktualisierung ohne Absturz (jeder Fall wird VOR dem Rechnen protokolliert)
Protokoll: Documents\\BORS_V7_QA\\tests\\v9_oberflaeche_<zeit>.csv  -> bitte an Claude schicken.
"""
import random
import time
from datetime import datetime
from pathlib import Path
# BORS-Ablage: zentrale Pfade aus 01_Skripte/Aktuell/bors_pfade.py (BORS_ROOT ueberschreibbar)
_BR = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
exec(compile((_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py').read_text(encoding='utf-8'), str(_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py'), 'exec'))
from qgis.PyQt.QtCore import QTimer

R = globals().get('BORS_ROUTER')
if R is None:
    raise RuntimeError('Zuerst 7_Router_V9_2c_BORS.py starten.')
adr_fn = globals().get('adresssuche')
out = P_TESTS
out.mkdir(parents=True, exist_ok=True)
prot = out / 'v9_oberflaeche_{}.csv'.format(datetime.now().strftime('%Y%m%d_%H%M'))
f = open(str(prot), 'w', encoding='utf-8-sig')
f.write('nr;test;profil;modus_ui;eingabe;ergebnis;modus_router;unvalidiert_m;banner;pruefung;fehler\n'); f.flush()
stat = {'PASS': 0, 'FAIL': 0}


def schreibe(*w):
    f.write(';'.join(str(x).replace(';', ',').replace('\n', ' ') for x in w) + '\n'); f.flush()


# 1 Adresssuche
ADRESSEN = ['Kramgasse 49 Bern', 'Viktoriastrasse 70 Bern', 'Bundesplatz 3 Bern', 'Thunstrasse 100 Bern', 'Bernstrasse 1 Ostermundigen']
ziele = []
for a in ADRESSEN:
    try:
        r = adr_fn(a) if adr_fn else []
        ok = bool(r) and r[0][1] > 2590000 and 1190000 < r[0][2] < 1210000
        schreibe(len(ziele) + 1, 'adresse', '', '', a, r[0][0] if r else 'kein Treffer', '', '', '', 'PASS' if ok else 'FAIL', '')
        stat['PASS' if ok else 'FAIL'] += 1
        if r:
            ziele.append((a, (r[0][1], r[0][2])))
    except Exception as ex:
        schreibe(0, 'adresse', '', '', a, '', '', '', '', 'FAIL', repr(ex)[:150]); stat['FAIL'] += 1

# 2 Routen
WACHE = (2601003.25, 1200397.25)
rnd = random.Random(27)
fids = [fid for fid in R.info if fid in R.kern.feat]
faelle = []
for i in range(24):
    code = 'ABCD'[i % 4]
    modus = 'EXPERIMENTELL' if (i // 4) % 2 else 'VALIDIERT'
    if i < len(ziele) * 2:
        p1, p2, txt = WACHE, ziele[i % len(ziele)][1], 'Wache -> ' + ziele[i % len(ziele)][0]
    else:
        def zp():
            pts = max(R.kern.feat[rnd.choice(fids)]['parts'], key=len)
            return pts[len(pts) // 2]
        p1, p2 = zp(), zp(); txt = 'Zufall {:.0f}/{:.0f} -> {:.0f}/{:.0f}'.format(p1[0], p1[1], p2[0], p2[1])
    faelle.append((i + 1, code, modus, p1, p2, txt))


def naechster(k=0):
    if k >= len(faelle):
        schreibe('ENDE', '', '', '', '', str(stat), '', '', '', '', '')
        f.close()
        print('BORS V9 OBERFLAECHENTEST fertig: {} | Protokoll {}'.format(stat, prot))
        return
    nr, code, modus, p1, p2, txt = faelle[k]
    schreibe(nr, 'START', code, modus, txt, '', '', '', '', '', '')
    fehler = ''
    try:
        R.cb_exp.setChecked(modus == 'EXPERIMENTELL')
        R.modus_ui = modus
        R._wahl(code)
        R.points = [p1, p2]
        R._rechnen(['REF', code], vergleich=False)
        r = (R.letzte or {}).get(code, {})
        html = R.ergebnis.text()
        banner = ('KEINE VALIDIERTE ROUTE' if 'KEINE VALIDIERTE ROUTE' in html else
                  'VALIDIERT BIS ZUR ZUFAHRT' if 'VALIDIERT BIS ZUR ZUFAHRT' in html else
                  'VALIDIERTE ROUTE' if 'VALIDIERTE ROUTE' in html else '-')
        m = r.get('modus', '')
        ok = True
        if r.get('ok') and m == 'VALIDIERT':
            ok = banner == 'VALIDIERTE ROUTE' and all(x['kategorie'] == 'KEIN_HINWEIS' for x in r['rows'])
        elif r.get('ok') and m == 'EXPERIMENTELL':
            ok = banner == 'KEINE VALIDIERTE ROUTE' and r.get('unvalidiert_m', -1) >= 0
        elif r.get('ok') and m == 'VALIDIERT_BIS_ZUFAHRT':
            ok = banner == 'VALIDIERT BIS ZUR ZUFAHRT'
        erg = 'Route {:.0f} m'.format(r['laenge_m']) if r.get('ok') else 'keine Route: {}'.format(r.get('ursache'))
        schreibe(nr, 'FERTIG', code, modus, txt, erg, m, round(r.get('unvalidiert_m', 0)), banner, 'PASS' if ok else 'FAIL', '')
        stat['PASS' if ok else 'FAIL'] += 1
        print('BORS V9 TEST {}/{} {} {}: {} [{}] Banner {}'.format(nr, len(faelle), code, modus, erg, m, banner))
    except Exception as ex:
        schreibe(nr, 'FEHLER', code, modus, txt, '', '', '', '', 'FAIL', repr(ex)[:200]); stat['FAIL'] += 1
    QTimer.singleShot(900, lambda: naechster(k + 1))


print('BORS V9 OBERFLAECHENTEST: {} Adressen, {} Routen -> {}'.format(len(ADRESSEN), len(faelle), prot))
QTimer.singleShot(500, naechster)
