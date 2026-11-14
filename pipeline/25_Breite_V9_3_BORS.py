# -*- coding: utf-8 -*-
"""BORS 25 (V9.3_BORS, 10.11.2026): wie V9.1, Pfade aus bors_pfade.py, Modul bors_breite_v9_3.py. Neu:
  - Querprofile ganz in einer Fahrflaeche (Platz) und Profile mit Loch/Mehrfachflaeche werden richtig gemessen (intervalle V9.3).
  - Je Klasse und Profil: Reserve = untere Schranke - oertlicher Bedarf (Spiegel nur an diesem Profil ueber Trottoir/Insel)
    -> <p>_reserve_profil_m (robust, 3 Profile) und <p>_reserve_einzel_m (ein Profil = Kandidat kurze Engstelle) mit Station.
  - Durchgaengigkeit: springt der freie Raum hinter einem Hindernis die Seite, <p>_durchgang_reserve_m (verbundener Teil).
  - Messluecken unter Bruecken/Tunnels: bauwerk_* wie der V9.2-Zusatzlauf (Bauwerksbreite - 3.0 m - k*sigma), hier eingebaut.
  - toleranzstufe_herkunft: die Toleranzstufe ist GESCHAETZT (Gebaeudedichte), nicht aus dem Toleranzstufenplan.
  Die Entscheide a_breite..d_breite bleiben nach V9.1 (massgebend ist der Netzmaster 26_V9_2h, er wertet die neuen Felder aus).
  Identitaetstest: BORS_BREITE_V91_KOMPATIBEL = True -> intervalle wie V9.1 (alle V9.1-Felder gleich wie die alte Datei).
STARTEN (QGIS-Python-Konsole oder normales Python mit numpy):
    from pathlib import Path
    p = Path.home() / 'OneDrive' / 'Desktop' / 'BORS' / '01_Skripte' / 'Aktuell' / '25_Breite_V9_3_BORS.py'
    exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'))
  Stichprobe: vorher BORS_V9_MAX_SEG = 300 und BORS_BREITE_AUSGABE = Path(...) (nie P_AKTUELL, sonst Abbruch).

V9.1: Belagsrand exakt (OSM surface / Gruenflaechen), k = 1.645, unterirdische Bauten erfasst.
V9: Geometrische Messung der freien Durchfahrtsbreite je Strassenabschnitt + Entscheid A-D.

Eingaben (nur lesen, Ablage BORS):
  02_Daten/2_Aktuell_V9/av_export_*.gpkg         (24_AV_Export_V9: Bodenbedeckung alle Arten, Einzelobjekte)
  02_Daten/2_Aktuell_V9/BORS_Netzmaster_V8_*.gpkg (Netzgeometrie, Strassenklasse, Bruecke/Tunnel)
  02_Daten/2_Aktuell_V9/Vorstufen/parkierung_v5_*.gpkg (Parkfelder Stadt Bern + OSM, mit Lagegenauigkeit)
  02_Daten/1_Rohdaten/Stadt_Bern/baumkataster.gpkg
  01_Skripte/Aktuell/BORS_Fahrzeuge_V1.csv (Fahrzeugdaten Kim -> Profile A-D als Huelle)
Ausgabe (neu): 02_Daten/2_Aktuell_V9/BORS_Breite_V9_3_<zeit>.gpkg
  breite_v9      Linien je Abschnitt mit allen Messgroessen und Ergebnis A-D
  engstellen_v9  Punkt an der massgebenden Engstelle je Abschnitt
  profile_v9     alle Querprofile von Abschnitten mit Ergebnis UNZUREICHEND / NICHT_ENTSCHEIDBAR (Nachvollzug)
Reines Python + numpy (kein GDAL). Dauer Container ca. 5 min, PC ca. 10-30 min.
"""
import csv
import math
import re
import sqlite3
import struct
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

# BORS-Ablage: zentrale Pfade aus 01_Skripte/Aktuell/bors_pfade.py (BORS_ROOT ueberschreibbar)
_BR = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
exec(compile((_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py').read_text(encoding='utf-8'), str(_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py'), 'exec'))
AKT = P_SKRIPTE
V9 = Path(globals().get('BORS_BREITE_AUSGABE', P_AKTUELL))
STAMP = datetime.now().strftime('%Y%m%d_%H%M')
MAXS = int(globals().get('BORS_V9_MAX_SEG', 0))
SEG_AUSWAHL = globals().get('BORS_V9_SEG_IDS')          # optional: Liste seg_id (Test)
if (MAXS or SEG_AUSWAHL) and V9.resolve() == P_AKTUELL.resolve():
    raise RuntimeError('Stichprobe nie nach {} schreiben (der Netzmaster nimmt die neueste Breitendatei): BORS_BREITE_AUSGABE setzen'.format(P_AKTUELL))
for _m in ('bors_geo.py', 'bors_bewertung_v8.py', 'bors_breite_v9_3.py'):
    exec(compile((AKT / _m).read_text(encoding='utf-8'), str(AKT / _m), 'exec'))
try:
    from qgis.PyQt.QtWidgets import QApplication
except Exception:
    QApplication = None
REP = []
T0 = time.time()

# Fahrbewegungsreserve je Seite (ANNAHME, im Bericht mit Sensitivitaet): Karosserie 0.25 m, Spiegel 0.10 m.
# Spiegel muessen INNERHALB der gemessenen Fahrbahn Platz haben (kein Trottoir als Spiegelraum angenommen).
RES_KOERPER, RES_SPIEGEL = 0.25, 0.10
BAUM_SPERR_M = 1.5    # Annahme: Stammradius <= 0.5 m + Lageunsicherheit Luftbild 1.0 m


def log(m):
    print('BORS V9 BREITE:', m); REP.append(str(m))
    if QApplication:
        try:
            QApplication.processEvents()
        except Exception:
            pass


def neueste(ordner, muster):
    l = sorted(ordner.glob(muster), key=lambda p: p.stat().st_mtime)
    if not l:
        raise FileNotFoundError('{} fehlt in {}'.format(muster, ordner))
    return l[-1]


AV = neueste(P_AKTUELL, 'av_export_*.gpkg')
NM = neueste(P_AKTUELL, 'BORS_Netzmaster_V8_*.gpkg')
PARK = neueste(P_VORSTUFEN, 'parkierung_v5_*.gpkg')
BAUM = P_STADT / 'baumkataster.gpkg'
FZ = lade_fahrzeuge(AKT / 'BORS_Fahrzeuge_V1.csv')
OUT = V9 / 'BORS_Breite_V9_3_{}{}.gpkg'.format(STAMP, '_STICHPROBE' if (MAXS or SEG_AUSWAHL) else '')
if OUT.exists():
    raise FileExistsError('{} existiert schon - eine Minute warten'.format(OUT))
log('Modus intervalle: {}'.format('V9.1 (Identitaetstest)' if V91_KOMPATIBEL else 'V9.3'))
PROFILE_ABCD = {}
for k in 'ABCD':
    h = huelle(FZ, k)
    bedarf = max(h['breite_karosserie_m'] + 2 * RES_KOERPER, h['breite_spiegel_m'] + 2 * RES_SPIEGEL)
    PROFILE_ABCD[k] = dict(h, bedarf=round(bedarf, 3))
    log('Profil {}: Karosserie {:.2f} m, Spiegel {:.2f} m -> Bedarf {:.2f} m (max(Karosserie+2x{:.2f}, Spiegel+2x{:.2f}))'.format(
        k, h['breite_karosserie_m'], h['breite_spiegel_m'], bedarf, RES_KOERPER, RES_SPIEGEL))
log('Eingaben: {} | {} | {}'.format(AV.name, NM.name, PARK.name))


def ro(p):
    return sqlite3.connect('file:{}?mode=ro'.format(p.as_posix()), uri=True)


# ------------------------------------------------------------------ AV laden
c = ro(AV)
UNTER = Kantenindex(); FAHR = Kantenindex(); NACHB = Kantenindex(); HIND = Kantenindex(); HINDL = Kantenindex(); BAUW = Kantenindex()
GEB = Raster(100.0); n_geb = 0
cnt = Counter()
for fid, g, art, q in c.execute('select fid, geom, bbartt_bez_de, qualit_bez_de from bb'):
    r = ringe(g)
    if art in ('Strasse, Weg', 'übrige befestigte'):
        FAHR.add(fid, r, art=art, q=q)
    NACHB.add(fid, r, art=art, q=q)
    if art == 'Gebäude':
        x, y = punkt(g)
        GEB.add(n_geb, x, y, x, y); n_geb += 1
    cnt['bb:' + art] += 1
for fid, g, art, q, gl in c.execute('select fid, geom, eoartt_bez_de, qualit_bez_de, gueltig from eof'):
    if gl == 0:
        continue
    if art in EO_HINDERNIS:
        HIND.add(fid, ringe(g), art=EO_HINDERNIS[art], q=q)
        NACHB.add(1000000000 + fid, ringe(g), art=EO_HINDERNIS[art], q=q)
    elif art in ('Brücke Passerelle', 'Tunnel Unterführung Galerie'):
        BAUW.add(fid, ringe(g), art=art, q=q)
    elif art == 'unterirdisches Gebäude':
        UNTER.add(fid, ringe(g), art=art)
for fid, g, art, q, gl in c.execute('select fid, geom, eoartt_bez_de, qualit_bez_de, gueltig from eol'):
    if gl == 0 or art not in EO_HINDERNIS:
        continue
    HINDL.add(fid, linien(g), geschlossen=False, art=EO_HINDERNIS[art], q=q)
c.close()
for x in (FAHR, NACHB, HIND, HINDL, BAUW, UNTER):
    x.fertig()
log('AV: Fahrflaechen {} | Nachbarflaechen {} | Hindernis-Flaechen {} | Hindernis-Linien {} | Bruecken/Tunnel {} | Gebaeude {}'.format(
    len(FAHR.info), len(NACHB.info), len(HIND.info), len(HINDL.info), len(BAUW.info), n_geb))

PK = Kantenindex()
c = ro(PARK)
for fid, g, q, art, lage in c.execute('select fid, geom, quelle, art, lage from parkierung'):
    if art and ('Velo' in art or 'Motorrad' in art or 'PaVerbot' in art):
        continue
    PK.add(fid, ringe(g), quelle=q, art=art, genau=(q == 'STADT_BERN' and not lage))
c.close(); PK.fertig()
BAEUME = Raster(50.0); BAUM_XY = []
if BAUM.is_file():
    c = ro(BAUM)
    t = [r[0] for r in c.execute("select table_name from gpkg_contents")][0]
    for x, y, lg in c.execute('select HKOORD, VKOORD, LAGEGENAUIGKEIT from "{}"'.format(t)):
        if x and y:
            BAEUME.add(len(BAUM_XY), x, y, x, y); BAUM_XY.append((x, y, lg))
    c.close()
log('Parkfelder (ohne Velo/Motorrad) {} | Baeume {}'.format(len(PK.info), len(BAUM_XY)))

# ------------------------------------------------------------------ Netz
c = ro(NM)
SRS = c.execute('select srs_name, srs_id, organization, organization_coordsys_id, definition, description from gpkg_spatial_ref_sys').fetchall()
SEGS = list(c.execute('select seg_id, geom, highway_type, laenge_m, zone, gemeinde, name, bruecke_tunnel_layer, other_tags from netz_v5 where ist_routingtyp = 1'))
c.close()
if SEG_AUSWAHL:
    _w = set(SEG_AUSWAHL); SEGS = [r for r in SEGS if r[0] in _w]
if MAXS:
    import random
    random.Random(5).shuffle(SEGS); SEGS = SEGS[:MAXS]
log('Abschnitte: {}'.format(len(SEGS)))


def ts_des_orts(xs, ys):
    """Toleranzstufe nach TVAV Art. 3: ueberbaute Gebiete/Bauzonen TS2 (Stadt TS1 hat dieselbe Genauigkeit 0.10 m),
    sonst Landwirtschaft/Wald TS3. Ersatzkriterium 'ueberbaut': >= 3 Gebaeude im Umkreis von 60 m (AV-Gebaeude).
    Der Toleranzstufenplan selbst ist in MOPUBE nicht enthalten."""
    x0, x1, y0, y1 = xs.min() - 60, xs.max() + 60, ys.min() - 60, ys.max() + 60
    return 2 if len(GEB.nahe(x0, y0, x1, y1)) >= 3 else 3


BLOCK = 40


def iv_bloecke(idx, P, N, filt=None, linie=False, umschl=False):
    """Schnitte in Bloecken zu BLOCK Profilen (Speicherbedarf ~ Block x Kanten statt Abschnitt x Kanten).
    V9.3 umschl: auch Flaechen ohne Kante im Block pruefen (Profil ganz innerhalb, z. B. grosser Platz)."""
    out = []
    for a in range(0, len(P), BLOCK):
        Pc, Nc = P[a:a + BLOCK], N[a:a + BLOCK]
        bb = (Pc[:, 0].min() - HALB_M - 1, Pc[:, 1].min() - HALB_M - 1, Pc[:, 0].max() + HALB_M + 1, Pc[:, 1].max() + HALB_M + 1)
        K, F = idx.nahe(*bb)
        if filt is not None and len(F):
            m = np.array([filt(int(f)) for f in F], dtype=bool)
            K, F = K[m], F[m]
        kand = None
        if umschl and not linie and not V91_KOMPATIBEL:
            kand = [int(f) for f in idx.umschliessend(*bb) if filt is None or filt(int(f))]
        T = schnitte(Pc, Nc, K)
        out += linienpunkte(T, F) if linie else intervalle(T, F, HALB_M, Pc, Nc, idx, kand)
    return out


def messen(pts, hw, brueckeTunnel, belag=''):
    s, P, N0 = profile(pts)
    n = len(s)
    if n == 0:
        return None
    xs, ys = P[:, 0], P[:, 1]
    bb = (xs.min() - HALB_M - 1, ys.min() - HALB_M - 1, xs.max() + HALB_M + 1, ys.max() + HALB_M + 1)
    filt = (lambda f: True) if hw == 'service' else (lambda f: FAHR.info[f]['art'] == 'Strasse, Weg')
    best_w = np.full(n, np.inf); best = [None] * n; Nsel = N0.copy(); versetzt = np.zeros(n, bool)
    cosw = np.ones(n)                         # V9.3: cos(Profilwinkel) -> Querlage senkrecht zur Achse (Durchgaengigkeit)
    for grad in WINKEL_GRAD:
        N = drehen(N0, grad)
        ivs = iv_bloecke(FAHR, P, N, filt, umschl=True)
        for i in range(n):
            h, vs = hauptintervall(vereinigen(ivs[i]))
            if h is None:
                continue
            w = h[1] - h[0]
            if vs and w < VERSETZT_MIN_M:
                continue                      # schmaler Flaechenzipfel neben der Achse (Flaeche endet) -> keine Messung
            if w < best_w[i]:
                best_w[i], best[i], Nsel[i], versetzt[i] = w, h, N[i], vs
                cosw[i] = math.cos(math.radians(grad))
    # Achse auf befestigter Flaeche ohne Strassen-Klassierung (z. B. Strasse geht in Hof/Platz ueber): zweiter Durchgang
    befestigt = np.zeros(n, bool)
    fehlt = [i for i in range(n) if best[i] is None]
    if fehlt and hw != 'service':
        for grad in WINKEL_GRAD:
            N = drehen(N0, grad)
            ivs = iv_bloecke(FAHR, P[fehlt], N[fehlt], umschl=True)
            for j, i in enumerate(fehlt):
                h, vs = hauptintervall(vereinigen(ivs[j]))
                if h is None or vs:
                    continue
                w = h[1] - h[0]
                if w < best_w[i]:
                    best_w[i], best[i], Nsel[i], befestigt[i] = w, h, N[i], True
                    cosw[i] = math.cos(math.radians(grad))
    # Abzuege und Nachbarn auf dem gewaehlten Profil (blockweise, damit der Speicher klein bleibt)
    ivh = iv_bloecke(HIND, P, Nsel)
    lph = iv_bloecke(HINDL, P, Nsel, linie=True)
    ivp = iv_bloecke(PK, P, Nsel)
    ivn = iv_bloecke(NACHB, P, Nsel)
    ts = ts_des_orts(xs, ys)
    R = dict(s=s, P=P, n=n, ts=ts, status=np.zeros(n, dtype='U12'), w_fb=np.full(n, np.nan), w_fest=np.full(n, np.nan),
             w_pg=np.full(n, np.nan), w_pa=np.full(n, np.nan), sig=np.full(n, np.nan), rand_l=['']*n, rand_r=['']*n,
             hind=Counter(), baum_in=0, pn=0, hart=np.zeros(n, bool), unter=0, cosw=cosw, pa_st=[[] for _ in range(n)], haupt=[None] * n)
    for i in range(n):
        x_, y_ = P[i]
        K_, F_ = UNTER.nahe(x_ - 1, y_ - 1, x_ + 1, y_ + 1)
        if len(F_) and any(UNTER.innen(int(f), x_, y_) for f in set(F_.tolist())):
            R['unter'] += 1
    for i in range(n):
        if best[i] is None:
            R['status'][i] = 'AUSSERHALB'; continue
        lo, hi, flo, fhi = best[i]
        such = lo <= -HALB_M + 1e-6 or hi >= HALB_M - 1e-6
        q_pn = FAHR.info[flo]['q'] == 'PN' or FAHR.info[fhi]['q'] == 'PN'
        R['pn'] += int(q_pn)
        R['status'][i] = 'PN' if q_pn else ('SUCHGRENZE' if such else ('VERSETZT' if versetzt[i] else ('BEFESTIGT' if befestigt[i] else 'OK')))
        R['w_fb'][i] = hi - lo
        fest = []
        for a, b, f in ivh[i]:
            if b > lo and a < hi:
                if min(b, hi) - max(a, lo) >= UEBERLAGERT_ANTEIL * (hi - lo):
                    R['hind'][HIND.info[f]['art'] + ' ueberlagert (nicht abgezogen)'] += 1
                    continue
                fest.append((a, b)); R['hind'][HIND.info[f]['art']] += 1
        for t, f in lph[i]:
            if lo < t < hi:
                fest.append((t, t)); R['hind'][HINDL.info[f]['art'] + ' (Linie)'] += 1
        # V9.1 Baeume: Stammposition innerhalb der Fahrbahn (Lage meist "ab Luftbild ohne Gewaehr"). Fuer die UNTERE Schranke wird
        # ein Sperrstreifen von +-BAUM_SPERR_M (Stamm + Lageunsicherheit, Annahme) abgezogen, fuer die obere Schranke nicht.
        baum_iv = []
        px, py = P[i]; nx, ny = Nsel[i]
        for j in BAEUME.nahe(px - HALB_M, py - HALB_M, px + HALB_M, py + HALB_M):
            bx, by, lg = BAUM_XY[j]
            dx, dy = bx - px, by - py
            t = dx * nx + dy * ny
            if abs(-dx * ny + dy * nx) <= 0.5 and lo + 0.3 < t < hi - 0.3:
                R['baum_in'] += 1
                baum_iv.append((t - BAUM_SPERR_M, t + BAUM_SPERR_M))
        wf, a0, b0 = abziehen(lo, hi, fest)
        R['w_fest'][i] = wf
        gen, alle = [], []
        for a, b, f in ivp[i]:
            if b <= lo or a >= hi:
                continue
            quer = min(b, hi) - max(a, lo)
            if PK.info[f]['genau'] and not (a < 0 < b) and quer < UEBERLAGERT_ANTEIL * (hi - lo):
                gen.append((a, b)); alle.append((a, b))
            else:
                # Lage ungenau (oder Flaeche quer ueber die Fahrbahn): Streifen am naeheren Rand, max. 2.0 m
                bw = min(quer, PARK_STREIFEN_MAX_M)
                alle.append((lo, lo + bw) if (a + b) / 2 < (lo + hi) / 2 else (hi - bw, hi))
        R['w_pg'][i] = abziehen(lo, hi, fest + gen)[0]
        R['w_pa'][i] = abziehen(lo, hi, fest + alle + baum_iv)[0]
        R['pa_st'][i] = abziehen_alle(lo, hi, fest + alle + baum_iv)      # V9.3: alle freien Teilstuecke (Durchgaengigkeit)
        R['haupt'][i] = (lo, hi)                                          # V9.3: gemessene Fahrbahn dieses Profils
        # Nachbarflaeche je Rand -> Lagegenauigkeit
        sig = []
        for seite, tt in (('l', lo - NACHBAR_M), ('r', hi + NACHBAR_M)):
            nb = [NACHB.info[f]['art'] for a, b, f in ivn[i] if a <= tt <= b and NACHB.info[f]['art'] not in ('Strasse, Weg',)]
            art = nb[0] if nb else ('Suchgrenze' if such else 'keine AV-Flaeche')
            R['rand_' + seite][i] = art
            if such and ((seite == 'l' and lo <= -HALB_M + 1e-6) or (seite == 'r' and hi >= HALB_M - 1e-6)):
                sig.append(0.0)
            else:
                exakt = belag in BEFESTIGT_OSM or art in EXAKT or (not belag and art not in NATURNAH)
                sig.append((SIGMA_EXAKT if exakt else SIGMA_UNSCHARF)[ts])
        R['sig'][i] = math.hypot(sig[0], sig[1])
        # hart = beide Raender fest (Randstein, Fassade, Mauer, Bahn, Wasser) oder durch Bodenhindernis begrenzt
        hl = R['rand_l'][i] in HART or (fest and a0 > lo + 1e-6)
        hr = R['rand_r'][i] in HART or (fest and b0 < hi - 1e-6)
        R['hart'][i] = bool(hl and hr)
    # Bruecken/Tunnel ohne Fahrflaeche: Bauwerksbreite als obere Schranke
    R['bauwerk'] = None
    R['bauwerk_luecke'] = None
    gueltig = np.isin(R['status'], ['OK', 'VERSETZT', 'SUCHGRENZE', 'BEFESTIGT'])
    # V9.3: Messluecken (AUSSERHALB) unter Bruecke/Tunnel - wie der V9.2-Zusatzlauf der Datei 20261028_1829 (Skript nicht
    # in der Ablage, Formel aus den Daten rekonstruiert und im Identitaetstest geprueft): Bauwerksbreite = kleinste der
    # 5 Winkel, einfaches Minimum ueber die Lueckenprofile mit Bauwerk; Anteil = Lueckenprofile mit Bauwerk / Lueckenprofile.
    gap = np.nonzero(R['status'] == 'AUSSERHALB')[0]
    if len(gap):
        wg, arten_g = [], Counter()
        for grad in WINKEL_GRAD:
            ivb = iv_bloecke(BAUW, P[gap], drehen(N0[gap], grad), umschl=True)
            zeile = []
            for iv in ivb:
                h = next((h for h in vereinigen(iv) if h[0] <= 0 <= h[1]), None)
                zeile.append(np.nan if h is None else h[1] - h[0])
                if h is not None:
                    arten_g[BAUW.info[h[2]]['art']] += 1
            wg.append(zeile)
        wg = np.array(wg, dtype=float)
        okg = ~np.isnan(wg).all(axis=0)
        if okg.any():
            wg = np.where(okg, np.nanmin(np.where(np.isnan(wg), np.inf, wg), axis=0), np.nan)
            R['bauwerk_luecke'] = (float(okg.mean()), float(np.nanmin(wg)), arten_g.most_common(1)[0][0], int(okg.sum()))
    if brueckeTunnel and gueltig.mean() < 0.5:
        wb, arten = [], Counter()
        for grad in WINKEL_GRAD:
            Nb = drehen(N0, grad)
            ivb = iv_bloecke(BAUW, P, Nb, umschl=True)
            zeile = []
            for iv in ivb:
                h = next((h for h in vereinigen(iv) if h[0] <= 0 <= h[1]), None)
                zeile.append(np.nan if h is None else h[1] - h[0])
                if h is not None:
                    arten[BAUW.info[h[2]]['art']] += 1
            wb.append(zeile)
        with np.errstate(all='ignore'):
            wb = np.array(wb, dtype=float)
            wb = np.where(np.isnan(wb).all(axis=0), np.nan, np.nanmin(np.where(np.isnan(wb), np.inf, wb), axis=0))
        ok = ~np.isnan(wb)
        if ok.sum() >= 3:
            R['bauwerk'] = (robustes_minimum(wb, ok)[0], arten.most_common(1)[0][0])
    return R


# ------------------------------------------------------------------ Messung
ERG = []
PROF_ROWS = []
stat = Counter()
import re as _re
_SURF = _re.compile(r'"surface"=>"([^"]*)"')
for k, (sid, g, hw, L, zone, gem, name, bt, ot) in enumerate(SEGS):
    _m = _SURF.search(ot or '')
    belag = _m.group(1) if _m else ''
    ls = linien(g)
    if not ls:
        continue
    pts = max(ls, key=len)
    bt = bt or ''
    kunst = ('bridge' in bt or 'tunnel' in bt or 'covered=yes' in bt)
    R = messen(pts, hw, kunst, belag)
    if R is None:
        continue
    n = R['n']
    st = R['status']
    gueltig = np.isin(st, ['OK', 'VERSETZT', 'SUCHGRENZE', 'BEFESTIGT'])
    kS = K_VERTRAUEN * R['sig']
    lo_all = R['w_pa'] - kS
    lo_fest = R['w_fest'] - kS
    hi_fest = R['w_fest'] + kS
    w_lo, i_lo = robustes_minimum(lo_all, gueltig)
    w_lof, _ = robustes_minimum(lo_fest, gueltig)
    w_hif, i_hi = robustes_minimum(hi_fest, gueltig)
    w_fb_rel, i_fb = robustes_minimum(R['w_fb'], gueltig)
    w_fest_rel, i_fe = robustes_minimum(R['w_fest'], gueltig)
    w_pa_rel, _ = robustes_minimum(R['w_pa'], gueltig)
    lg, li, nl = luecken(gueltig)
    abdeck = float(gueltig.mean())
    messbar = not math.isnan(w_lo) and gueltig.sum() >= min(FENSTER, n)
    grund_nm = None
    if not messbar:
        if (st == 'PN').sum() > 0:
            grund_nm = 'AV-Qualitaet PN (provisorische Numerisierung): Lagegenauigkeit nicht nach TVAV belegt'
        elif kunst:
            grund_nm = 'Bruecke/Tunnel: keine Fahrbahnflaeche in der AV'
        else:
            grund_nm = 'Achse ausserhalb der AV-Strassenflaeche (keine Fahrbahn erfasst)'
    # Engstelle: Profil mit der kleinsten unteren Schranke; Laenge = zusammenhaengende Profile <= Wert + 0.10 m
    i_e = i_lo if i_lo >= 0 else i_fb
    pos = float(R['s'][i_e]) if i_e >= 0 else None
    elen = 0.0
    if i_e >= 0:
        ref = lo_all[i_e] + 0.10
        a = i_e
        while a - 1 >= 0 and gueltig[a - 1] and lo_all[a - 1] <= ref:
            a -= 1
        b = i_e
        while b + 1 < n and gueltig[b + 1] and lo_all[b + 1] <= ref:
            b += 1
        elen = (b - a + 1) * PROFIL_ABSTAND_M
    sig_e = float(R['sig'][i_e]) if i_e >= 0 else None
    rec = dict(seg_id=sid, name=name or '', highway=hw, zone=zone, gemeinde=gem, laenge_m=round(L, 1), kunstbaute=bt,
               n_profile=n, profil_abstand_m=PROFIL_ABSTAND_M, abdeckung=round(abdeck, 3), luecke_max_m=lg, luecke_innen_m=li,
               n_luecken=nl, n_achse_versetzt=int((st == 'VERSETZT').sum()), n_suchgrenze=int((st == 'SUCHGRENZE').sum()),
               n_ausserhalb=int((st == 'AUSSERHALB').sum()), n_pn=int((st == 'PN').sum()), n_befestigt=int((st == 'BEFESTIGT').sum()), belag_osm=belag, ueber_unterirdisch_anteil=round(R['unter'] / n, 3),
               fahrbahn_median_m=round(float(np.nanmedian(np.where(gueltig, R['w_fb'], np.nan))), 2) if gueltig.any() else None,
               fahrbahn_min_rel_m=None if math.isnan(w_fb_rel) else round(w_fb_rel, 2),
               frei_fest_min_rel_m=None if math.isnan(w_fest_rel) else round(w_fest_rel, 2),
               frei_parkiert_min_rel_m=None if math.isnan(w_pa_rel) else round(w_pa_rel, 2),
               untere_schranke_m=None if math.isnan(w_lo) else round(w_lo, 3),
               untere_schranke_fest_m=None if math.isnan(w_lof) else round(w_lof, 3),
               obere_schranke_fest_m=None if math.isnan(w_hif) else round(w_hif, 3),
               engstelle_pos_m=None if pos is None else round(pos, 1), engstelle_laenge_m=elen,
               sigma_breite_m=None if sig_e is None else round(sig_e, 3), toleranzstufe=R['ts'],
               rand_links=R['rand_l'][i_e] if i_e >= 0 else '', rand_rechts=R['rand_r'][i_e] if i_e >= 0 else '',
               rand_hart=int(R['hart'][i_e]) if i_e >= 0 else 0,
               hindernisse='; '.join('{} x{}'.format(a, b) for a, b in R['hind'].most_common()),
               baeume_in_fahrbahn=R['baum_in'], quelle='AV MOPUBE {} (Bodenbedeckung, Einzelobjekte), Parkfelder Stadt Bern/OSM'.format(AV.stem[-13:]),
               methode='Querprofile 1 m, 5 Winkel (min), Fahrbahn = AV Strasse/Weg{}, robuste Engstelle 3 Profile, k={} x sigma(TVAV TS{})'.format(
                   ' + uebrige befestigte' if hw == 'service' else '', K_VERTRAUEN, R['ts']))
    # ---- V9.3: Profilweise Pruefung (gleiche Station fuer Breite, Rand und Bedarf), kurze Engstelle, Durchgaengigkeit
    rec['toleranzstufe_herkunft'] = 'GESCHAETZT: >= 3 AV-Gebaeude im Umkreis 60 m -> TS2, sonst TS3 (Toleranzstufenplan nicht in MOPUBE)'
    w_lo_e, i_lo_e = einzel_minimum(lo_all, gueltig)
    rec['untere_schranke_einzel_m'] = None if math.isnan(w_lo_e) else round(w_lo_e, 3)
    rec['engstelle_einzel_pos_m'] = None if i_lo_e < 0 else round(float(R['s'][i_lo_e]), 1)
    rec['engstelle_einzel_profil'] = '' if i_lo_e < 0 else 'Fahrbahn {:.2f} m, ohne Hindernisse {:.2f} m, mit Parkfeldern/Baeumen {:.2f} m, Rand {} / {}, {}'.format(
        R['w_fb'][i_lo_e], R['w_fest'][i_lo_e], R['w_pa'][i_lo_e], R['rand_l'][i_lo_e], R['rand_r'][i_lo_e], R['status'][i_lo_e])
    n_tief = np.array([(R['rand_l'][i] in SPIEGEL_UEBER) + (R['rand_r'][i] in SPIEGEL_UEBER) for i in range(n)], dtype=int)
    dg = [] if V91_KOMPATIBEL else durchgang(R['pa_st'], R['cosw'], gueltig, R['haupt'])
    rec['durchgang_n'] = len(dg)
    for kat, pr in PROFILE_ABCD.items():
        p = kat.lower()
        bedj = np.array([bedarf_lokal(pr['breite_karosserie_m'], pr['breite_spiegel_m'], kat, t) for t in (0, 1, 2)])[n_tief]
        rj = lo_all - bedj
        rr, ir = robustes_minimum(rj, gueltig)
        re_, ie = einzel_minimum(rj, gueltig)
        rec[p + '_reserve_profil_m'] = None if math.isnan(rr) else round(rr, 3)
        rec[p + '_reserve_profil_station_m'] = None if ir < 0 else round(float(R['s'][ir]), 1)
        rec[p + '_reserve_einzel_m'] = None if math.isnan(re_) else round(re_, 3)
        rec[p + '_reserve_einzel_station_m'] = None if ie < 0 else round(float(R['s'][ie]), 1)
        rec[p + '_reserve_einzel_status'] = '' if ie < 0 else str(st[ie])
        rd = [(verb - K_VERTRAUEN * max(R['sig'][i], R['sig'][i + 1]) - max(bedj[i], bedj[i + 1]), i) for i, bean, verb in dg]
        rd = min(rd) if rd else None
        rec[p + '_durchgang_reserve_m'] = None if rd is None else round(float(rd[0]), 3)
        rec[p + '_durchgang_station_m'] = None if rd is None else round(float(R['s'][rd[1]]), 1)
    bl = R['bauwerk_luecke']
    rec['bauwerk_anteil_luecke'] = None if bl is None else round(bl[0], 3)
    rec['bauwerk_breite_min_m'] = None if bl is None else round(bl[1], 2)
    rec['bauwerk_untere_schranke_m'] = None if bl is None else round(bl[1] - 3.0 - K_VERTRAUEN * math.hypot(SIGMA_EXAKT[R['ts']], SIGMA_EXAKT[R['ts']]), 3)
    rec['bauwerk_art'] = None if bl is None else bl[2]
    rec['bauwerk_n_profile'] = None if bl is None else bl[3]
    bw = R['bauwerk']
    for kat, pr in PROFILE_ABCD.items():
        if messbar:
            e, gr = entscheide(pr['bedarf'], w_lo, w_lof, w_hif, True, li, minimum=pr['breite_karosserie_m'])
            if e == 'UNZUREICHEND' and i_hi >= 0 and not R['hart'][i_hi]:
                e = 'NICHT_ENTSCHEIDBAR'
                gr = 'AV-Fahrbahn zu schmal ({:.2f} m), Rand aber weich ({} / {}): Bankett/Wiese evtl. mitbefahrbar - nicht nachgewiesen'.format(
                    R['w_fest'][i_hi], R['rand_l'][i_hi], R['rand_r'][i_hi])
            if R['baum_in'] and e == 'AUSREICHEND':
                gr += '; {} Baumstandorte in der Fahrbahn mit je {:.1f} m Sperrstreifen beruecksichtigt'.format(R['baum_in'], 2 * BAUM_SPERR_M)
        elif bw is not None:
            hi = bw[0] + K_VERTRAUEN * math.hypot(SIGMA_EXAKT[R['ts']], SIGMA_EXAKT[R['ts']])
            if hi < pr['bedarf']:
                e, gr = 'UNZUREICHEND', '{}: gesamte Bauwerksbreite hoechstens {:.2f} m < Bedarf {:.2f} m'.format(bw[1], hi, pr['bedarf'])
            else:
                e, gr = 'NICHT_ENTSCHEIDBAR', '{}: nur Bauwerksbreite bekannt ({:.2f} m inkl. Trottoir/Gelaender), Fahrbahn nicht erfasst'.format(bw[1], bw[0])
        else:
            e, gr = entscheide(pr['bedarf'], np.nan, np.nan, np.nan, False, li, grund_nm)
        rec['{}_breite'.format(kat.lower())] = e
        rec['{}_breite_grund'.format(kat.lower())] = gr[:250]
        rec['{}_bedarf_m'.format(kat.lower())] = pr['bedarf']
        rec['{}_reserve_m'.format(kat.lower())] = None if math.isnan(w_lo) else round(w_lo - pr['bedarf'], 3)
        stat[(kat, zone, e)] += L
    rec['_geom'] = g
    rec['_pt'] = tuple(R['P'][i_e]) if i_e >= 0 else None
    ERG.append(rec)
    if any(rec['{}_breite'.format(x)] != 'AUSREICHEND' for x in 'abcd'):
        for i in range(n):
            PROF_ROWS.append((sid, float(R['s'][i]), float(R['P'][i][0]), float(R['P'][i][1]), str(st[i]),
                              None if math.isnan(R['w_fb'][i]) else round(float(R['w_fb'][i]), 3),
                              None if math.isnan(R['w_fest'][i]) else round(float(R['w_fest'][i]), 3),
                              None if math.isnan(R['w_pg'][i]) else round(float(R['w_pg'][i]), 3),
                              None if math.isnan(R['w_pa'][i]) else round(float(R['w_pa'][i]), 3),
                              None if math.isnan(R['sig'][i]) else round(float(R['sig'][i]), 3), R['rand_l'][i], R['rand_r'][i]))
    if k % 1000 == 0:
        log('{}/{} Abschnitte | {:.0f} s'.format(k, len(SEGS), time.time() - T0))

# ------------------------------------------------------------------ Schreiben
V9.mkdir(parents=True, exist_ok=True)
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
felder = [f for f in ERG[0] if not f.startswith('_')]


def typ(f):
    v = next((r[f] for r in ERG if r[f] is not None), None)
    return 'INTEGER' if isinstance(v, (int, np.integer)) and not isinstance(v, bool) else ('REAL' if isinstance(v, (float, np.floating)) else 'TEXT')


o.execute('CREATE TABLE breite_v9 (fid INTEGER PRIMARY KEY AUTOINCREMENT, geom LINESTRING, {})'.format(', '.join('"{}" {}'.format(f, typ(f)) for f in felder)))
o.execute("insert into gpkg_contents (table_name, data_type, identifier, description, srs_id) values ('breite_v9','features','BORS Breite V9','Freie Durchfahrtsbreite je Abschnitt',2056)")
o.execute("insert into gpkg_geometry_columns values ('breite_v9','geom','LINESTRING',2056,0,0)")


def conv(v):
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, np.integer):
        return int(v)
    return v


o.executemany('insert into breite_v9 (geom, {}) values (?, {})'.format(', '.join('"{}"'.format(f) for f in felder), ','.join('?' * len(felder))),
              [[r['_geom']] + [conv(r[f]) for f in felder] for r in ERG])
o.execute('CREATE INDEX i_b9 ON breite_v9 (seg_id)')


def gp_punkt(x, y):
    return b'GP' + bytes([0, 1]) + struct.pack('<i', 2056) + struct.pack('<BIdd', 1, 1, x, y)


o.execute('CREATE TABLE engstellen_v9 (fid INTEGER PRIMARY KEY AUTOINCREMENT, geom POINT, seg_id TEXT, name TEXT, untere_schranke_m REAL, '
          'obere_schranke_fest_m REAL, laenge_m REAL, a_breite TEXT, b_breite TEXT, c_breite TEXT, d_breite TEXT, rand_links TEXT, rand_rechts TEXT, hindernisse TEXT)')
o.execute("insert into gpkg_contents (table_name, data_type, identifier, description, srs_id) values ('engstellen_v9','features','BORS Engstellen V9','massgebende Engstelle je Abschnitt',2056)")
o.execute("insert into gpkg_geometry_columns values ('engstellen_v9','geom','POINT',2056,0,0)")
o.executemany('insert into engstellen_v9 (geom, seg_id, name, untere_schranke_m, obere_schranke_fest_m, laenge_m, a_breite, b_breite, c_breite, d_breite, '
              'rand_links, rand_rechts, hindernisse) values (?,?,?,?,?,?,?,?,?,?,?,?,?)',
              [(gp_punkt(*r['_pt']), r['seg_id'], r['name'], r['untere_schranke_m'], r['obere_schranke_fest_m'], r['engstelle_laenge_m'],
                r['a_breite'], r['b_breite'], r['c_breite'], r['d_breite'], r['rand_links'], r['rand_rechts'], r['hindernisse'])
               for r in ERG if r['_pt'] is not None])
o.execute('CREATE TABLE profile_v9 (fid INTEGER PRIMARY KEY AUTOINCREMENT, geom POINT, seg_id TEXT, station_m REAL, status TEXT, fahrbahn_m REAL, '
          'frei_fest_m REAL, frei_park_genau_m REAL, frei_park_alle_m REAL, sigma_m REAL, rand_links TEXT, rand_rechts TEXT)')
o.execute("insert into gpkg_contents (table_name, data_type, identifier, description, srs_id) values ('profile_v9','features','BORS Querprofile V9','Querprofile nicht nachgewiesener Abschnitte',2056)")
o.execute("insert into gpkg_geometry_columns values ('profile_v9','geom','POINT',2056,0,0)")
o.executemany('insert into profile_v9 (geom, seg_id, station_m, status, fahrbahn_m, frei_fest_m, frei_park_genau_m, frei_park_alle_m, sigma_m, rand_links, rand_rechts) '
              'values (?,?,?,?,?,?,?,?,?,?,?)', [(gp_punkt(r[2], r[3]), r[0], r[1]) + r[4:] for r in PROF_ROWS])
o.execute('CREATE INDEX i_p9 ON profile_v9 (seg_id)')
o.execute('CREATE TABLE bors_meta (schluessel TEXT, wert TEXT)')
meta = [('version', 'V9.3' + (' (intervalle V9.1, Identitaetstest)' if V91_KOMPATIBEL else '')), ('erstellt', STAMP),
        ('bedarf_profil', BEDARF_REGEL),
        ('toleranzstufe', 'GESCHAETZT aus Gebaeudedichte (>= 3 Gebaeude / 60 m -> TS2, sonst TS3); Toleranzstufenplan nicht in MOPUBE'),
        ('sigma_raender', 'Raender als unabhaengig angenommen: bei positiver Korrelation (gleiche Aufnahme) waere sigma der Breite kleiner '
                          '-> Annahme konservativ fuer beide Schranken'),
        ('bauwerk', 'Messluecken unter Bruecke/Tunnel: Bauwerksbreite - 3.0 m (Trottoir/Gelaender, Annahme) - k*sqrt(2)*sigma_exakt(TS)'),
        ('auswahl', 'Stichprobe {} Abschnitte'.format(len(ERG)) if (MAXS or SEG_AUSWAHL) else 'alle Abschnitte'), ('av', AV.name), ('netz', NM.name), ('parkierung', PARK.name),
        ('reserve', 'Karosserie +2x{:.2f} m, Spiegel +2x{:.2f} m (Annahme)'.format(RES_KOERPER, RES_SPIEGEL)),
        ('vertrauen', 'k = {} x Standardabweichung der Breite (sqrt(sl^2+sr^2), TVAV Art. 29 / Art. 31 Abs. 2)'.format(K_VERTRAUEN))]
meta += [('profil_' + k, 'Bedarf {:.3f} m (Karosserie {:.2f}, Spiegel {:.2f})'.format(v['bedarf'], v['breite_karosserie_m'], v['breite_spiegel_m'])) for k, v in PROFILE_ABCD.items()]
o.executemany('insert into bors_meta values (?,?)', meta)
o.commit(); o.close()

log('')
log('Ergebnis Breite (km, Zielgebiet = BEWERTUNG):')
for kat in 'ABCD':
    t = {e: stat[(kat, 'BEWERTUNG', e)] / 1000 for e in ('AUSREICHEND', 'NICHT_ENTSCHEIDBAR', 'UNZUREICHEND')}
    log('  {}: ausreichend {:.0f} | nicht entscheidbar {:.0f} | unzureichend {:.0f}'.format(kat, t['AUSREICHEND'], t['NICHT_ENTSCHEIDBAR'], t['UNZUREICHEND']))
log('Fertig in {:.0f} s: {}'.format(time.time() - T0, OUT))
(V9 / (OUT.stem + '_BERICHT.txt')).write_text('\n'.join(REP), encoding='utf-8')
