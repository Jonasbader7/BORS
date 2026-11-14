# -*- coding: utf-8 -*-
"""Regressionstests bors_breite_v9_3.py (normales Python + numpy, kein QGIS, keine Rohdaten).
    python test_breite_v9_3.py      -> je Pruefung PASS / FAIL, Exit-Code 1 bei FAIL
Geprueft: normale Strasse, Profil ganz in einer Flaeche, Loch, Mehrfachflaeche, konkave Flaeche, kurze Engstelle,
Spiegel je Profil, Durchgaengigkeit, fehlende Messdaten (keine Freigabe), Rueckwaertskompatibilitaet."""
import sys
from pathlib import Path

import numpy as np

HIER = Path(__file__).resolve().parent
ERG = []


def lade(kompatibel=False):
    ns = {'BORS_BREITE_V91_KOMPATIBEL': kompatibel}
    exec(compile((HIER / 'bors_breite_v9_3.py').read_text(encoding='utf-8'), 'bors_breite_v9_3.py', 'exec'), ns)
    return ns


def pruefe(name, ok, info=''):
    ERG.append(ok)
    print('{} {}{}'.format('PASS' if ok else 'FAIL', name, '  ' + str(info) if not ok or info else ''))


def rechteck(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def messe(B, ringe_je_fid, P=(0.0, 0.0), N=(0.0, 1.0), umschl=True, halb=20.0):
    """Profil P + t*N, t in [-halb, halb] gegen Flaechen {fid: [Ring, ...]} -> vereinigte Intervalle [(lo, hi)]."""
    idx = B['Kantenindex']()
    for fid, ringe in ringe_je_fid.items():
        idx.add(fid, ringe)
    idx.fertig()
    Pa, Na = np.array([P], float), np.array([N], float)
    K, F = idx.nahe(P[0] - halb - 1, P[1] - halb - 1, P[0] + halb + 1, P[1] + halb + 1)
    kand = list(idx.umschliessend(P[0] - halb - 1, P[1] - halb - 1, P[0] + halb + 1, P[1] + halb + 1)) if umschl else None
    T = B['schnitte'](Pa, Na, K, halb)
    iv = B['intervalle'](T, F, halb, Pa, Na, idx, kand)[0]
    return [(round(a, 6), round(b, 6)) for a, b, _, _ in B['vereinigen'](iv)]


B = lade()
B91 = lade(kompatibel=True)

# 1 Normale Strasse 6 m breit: unveraendert gegenueber V9.1
str6 = {1: [rechteck(-100, -3, 100, 3)]}
pruefe('normale Strasse [-3, 3]', messe(B, str6) == [(-3.0, 3.0)], messe(B, str6))
pruefe('normale Strasse = V9.1', messe(B, str6) == messe(B91, str6, umschl=False))
# 2 Reproduktion Befund 1: Quadrat (-50,-50)..(50,50), Zentrum (0,0), Richtung (0,1), Halbprofil 20 m
q = {1: [rechteck(-50, -50, 50, 50)]}
pruefe('V9.1-Fehler reproduziert: ganz enthaltenes Profil leer', messe(B91, q, umschl=False) == [], messe(B91, q, umschl=False))
pruefe('ganz enthaltenes Profil = [-20, 20] (Suchgrenze)', messe(B, q) == [(-20.0, 20.0)], messe(B, q))
# 3 Loch: Quadrat mit Loch y -5..5 -> innen [-20,-5] und [5,20]
loch = {1: [rechteck(-50, -50, 50, 50), rechteck(-30, -5, 30, 5)]}
pruefe('V9.1-Fehler reproduziert: Loch invertiert', messe(B91, loch, umschl=False) == [(-5.0, 5.0)], messe(B91, loch, umschl=False))
pruefe('Loch: [-20,-5] und [5,20]', messe(B, loch) == [(-20.0, -5.0), (5.0, 20.0)], messe(B, loch))
# 3b Profil ganz im Loch -> leer
gross_loch = {1: [rechteck(-60, -60, 60, 60), rechteck(-40, -40, 40, 40)]}
pruefe('Profil ganz im Loch: leer', messe(B, gross_loch) == [], messe(B, gross_loch))
# 4 Mehrfachflaeche (eine fid, zwei Teile y -30..-2 und 2..30)
multi = {1: [[rechteck(-50, -30, 50, -2)], [rechteck(-50, 2, 50, 30)]]}
pruefe('Mehrfachflaeche: [-20,-2] und [2,20]', messe(B, multi) == [(-20.0, -2.0), (2.0, 20.0)], messe(B, multi))
# 5 Konkave Flaeche (U): beginnt und endet innen, Bucht y -4..4 von rechts
u = {1: [[(-50, -50), (50, -50), (50, -4), (-10, -4), (-10, 4), (50, 4), (50, 50), (-50, 50), (-50, -50)]]}
pruefe('konkave Flaeche: Bucht ausgespart', messe(B, u, P=(0.0, 0.0)) == [(-20.0, -4.0), (4.0, 20.0)], messe(B, u))
# 6 Ungerade Schnittzahl (Profil beginnt in der Flaeche): wie V9.1
halb_innen = {1: [rechteck(-50, -50, 50, 5)]}
pruefe('Profil beginnt innen: [-20, 5] = V9.1', messe(B, halb_innen) == [(-20.0, 5.0)] == messe(B91, halb_innen, umschl=False), messe(B, halb_innen))

# 7 Kurze Engstelle: robust 4, einzeln 2 (Befund 2)
w = np.array([4, 4, 2, 4, 4], float); g = np.ones(5, bool)
pruefe('robustes_minimum [4,4,2,4,4] = 4 (unveraendert)', B['robustes_minimum'](w, g)[0] == 4.0)
pruefe('einzel_minimum [4,4,2,4,4] = 2 an Index 2', B['einzel_minimum'](w, g) == (2.0, 2))
pruefe('einzel_minimum ohne gueltige Profile = (nan, -1)', np.isnan(B['einzel_minimum'](w, np.zeros(5, bool))[0]))

# 8 Profilpruefung: nur Herabstufung, nie Freigabe, nie Sperre
pp = B['profilpruefung']
basis = {'a_reserve_profil_m': 0.3, 'a_reserve_profil_station_m': 5.0, 'a_reserve_einzel_m': 0.1, 'a_reserve_einzel_station_m': 5.0,
         'a_durchgang_reserve_m': None, 'a_durchgang_station_m': None}
pruefe('Profilpruefung: alles reicht -> AUSREICHEND bleibt', pp('AUSREICHEND', 'x', basis, 'a')[0] == 'AUSREICHEND')
m = dict(basis, a_reserve_einzel_m=-0.4)
e, gr = pp('AUSREICHEND', 'x', m, 'a')
pruefe('kurze Engstelle -> NICHT_ENTSCHEIDBAR mit Hinweis', e == 'NICHT_ENTSCHEIDBAR' and 'kurze Engstelle' in gr, gr)
pruefe('kurze Engstelle sperrt nie (UNZUREICHEND/NE bleiben)', pp('NICHT_ENTSCHEIDBAR', 'x', m, 'a')[0] == 'NICHT_ENTSCHEIDBAR'
       and pp('UNZUREICHEND', 'x', m, 'a')[0] == 'UNZUREICHEND')
pruefe('oertlicher Bedarf verfehlt -> NICHT_ENTSCHEIDBAR', pp('AUSREICHEND', 'x', dict(basis, a_reserve_profil_m=-0.2), 'a')[0] == 'NICHT_ENTSCHEIDBAR')
pruefe('fehlende Profilwerte -> keine Freigabe', pp('AUSREICHEND', 'x', dict(basis, a_reserve_profil_m=None), 'a')[0] == 'NICHT_ENTSCHEIDBAR')
pruefe('alte Breitendatei ohne V9.3-Felder -> unveraendert', pp('AUSREICHEND', 'x', {'untere_schranke_m': 3.0}, 'a') == ('AUSREICHEND', 'x'))
pruefe('Seitenwechsel mit zu schmalem verbundenem Teil -> NE', pp('AUSREICHEND', 'x', dict(basis, a_durchgang_reserve_m=-0.5, a_durchgang_station_m=7.0), 'a')[0] == 'NICHT_ENTSCHEIDBAR')

# 9 Spiegel je Profil (Befund 3): Klasse D, Karosserie 2.56, Spiegel 3.06
bl = B['bedarf_lokal']
pruefe('bedarf_lokal D: 0/1/2 Trottoir = 3.26/3.06/3.06', (bl(2.56, 3.06, 'D', 0), bl(2.56, 3.06, 'D', 1), bl(2.56, 3.06, 'D', 2)) == (3.26, 3.06, 3.06))
# Profil 1: 3.10 m zwischen Trottoirs (reicht dort, Bedarf 3.06), Profil 2..4: 3.20 m zwischen Mauern (Bedarf 3.26 -> fehlt)
lo = np.array([3.10, 3.20, 3.20, 3.20, 3.10]); tief = np.array([2, 0, 0, 0, 2])
bed = np.array([bl(2.56, 3.06, 'D', t) for t in (0, 1, 2)])[tief]
alt = B['robustes_minimum'](lo, np.ones(5, bool))[0] - bl(2.56, 3.06, 'D', 2)     # V9.2g: Minimum + Rand an der Engstelle
neu = B['robustes_minimum'](lo - bed, np.ones(5, bool))[0]
pruefe('V9.2g-Fehler reproduziert: Mischung -> Reserve >= 0', alt >= 0, alt)
pruefe('profilweise: Mauerabschnitt fehlt 0.06 m', abs(neu + 0.06) < 1e-9, neu)

# 10 Durchgaengigkeit (Befund 4)
dg = B['durchgang']
c1 = np.ones(3)
gerade = [[(-3.0, 3.0)], [(-3.0, 3.0)], [(-3.0, 3.0)]]
pruefe('durchgang: normale Strasse ohne Befund', dg(gerade, c1, np.ones(3, bool)) == [])
mittel = [[(-4.0, -0.5), (0.5, 4.0)], [(-4.0, -0.5), (0.5, 4.01)], [(-4.01, -0.5), (0.5, 4.0)]]
pruefe('durchgang: Mittelmauer, gleich breite Haelften -> kein Fehlalarm', dg(mittel, c1, np.ones(3, bool)) == [], dg(mittel, c1, np.ones(3, bool)))
sprung = [[(-4.0, 0.0), (1.0, 2.0)], [(-4.0, -3.5), (0.5, 4.5)]]      # breites Stueck links, danach rechts, ohne Ueberlappung
r = dg(sprung, np.ones(2), np.ones(2, bool))
pruefe('durchgang: Sprung hinter Hindernis -> verbunden 1.0 statt 4.0', len(r) == 1 and r[0][1] == 4.0 and r[0][2] == 1.0, r)
wechsel = [[(0.99, 5.49)], [(-5.53, -0.99)]]                             # Achse auf Mittelinsel: Messung wechselt die Fahrbahn
pruefe('durchgang: Fahrbahnwechsel bei versetzter Achse -> kein Befund', dg(wechsel, np.ones(2), np.ones(2, bool), [(0.99, 5.49), (-5.53, -0.99)]) == [])
pruefe('durchgang: Sprung innerhalb derselben Fahrbahn bleibt Befund', len(dg(sprung, np.ones(2), np.ones(2, bool), [(-4.0, 2.0), (-4.0, 4.5)])) == 1)
e, gr = pp('AUSREICHEND', 'x', dict(basis, a_reserve_einzel_m=-0.4, a_reserve_einzel_status='VERSETZT'), 'a')
pruefe('kurze Engstelle bei versetzter Achse: NE mit eigenem Grund', e == 'NICHT_ENTSCHEIDBAR' and 'versetzter Achse' in gr, gr)
pruefe('durchgang: ungueltiges Nachbarprofil wird nicht verbunden', dg(sprung, np.ones(2), np.array([True, False])) == [])
pruefe('abziehen_alle: Pfeiler in der Mitte -> zwei Stuecke', B['abziehen_alle'](-3.0, 3.0, [(-0.2, 0.2)]) == [(-3.0, -0.2), (0.2, 3.0)])

print('{} PASS / {} FAIL'.format(sum(ERG), len(ERG) - sum(ERG)))
sys.exit(0 if all(ERG) else 1)
