# -*- coding: utf-8 -*-
"""BORS Bern - Schleppkurven-Pruefung (Abbiegen/Kurven) fuer ein konkretes Fahrzeug. Nur numpy (laeuft in QGIS).

MODELL (stationaere Kreisfahrt, wie Schleppkurven-Schablonen nach VSS/FGSV, vereinfacht):
  Hinterachsmitte faehrt Gerade -> Kreisbogen Radius R -> Gerade. Fahrzeug: Karosseriebreite W, Radstand L,
  Ueberhang vorne Of / hinten Or, Wendekreis (aussen, Rad) -> kleinster moeglicher R.
    innerer Rand der ueberstrichenen Flaeche:  R_i = R - W/2              (Hinterrad innen)
    aeusserer Rand:                             R_a = sqrt((R + W/2)^2 + (L + Of)^2)   (Fahrzeugecke vorne aussen)
    Heckausschwenk:                             R_h = sqrt((R + W/2)^2 + Or^2)         (bei langem Hecküberhang, z.B. Drehleiter)
  Das Fahrzeug darf die ganze befestigte Fahrbahnflaeche nutzen (Einsatzfahrt: Gegenfahrbahn), seitlich versetzt
  anfahren (a) und wegfahren (b). Gesucht: gibt es R, a, b, so dass die ueberstrichene Flaeche vollstaendig auf der
  Strassenflaeche (amtliche Vermessung, Bodenbedeckung Strasse/Weg) liegt?
  Ergebnis: OK (mit 0.25 m Reserve je Seite) | ENG (nur ohne Reserve) | NUR_MIT_NEBENFLAECHE (nur wenn
  befestigte Nebenflaechen wie Vorplaetze mitbenutzt werden) | UNMOEGLICH.
  Parkierte Fahrzeuge an der Ecke sind NICHT beruecksichtigt (unbekannt) -> Ergebnis ist eine Obergrenze.
  Trottoirs fehlen im AV-Auszug: Luecken bis ca. 2.5 m zwischen Strasse und Zufahrt (Trottoir-Ueberfahrt) werden durch
  morphologisches Schliessen (Radius 1.5 m) als befahrbar behandelt. Kreisel werden nicht geprueft (Status KREISEL).
"""
import math
import numpy as np

PIX = 0.25
FENSTER = 40.0
RESERVE = 0.25
SCHLIESSEN_M = 1.5


def maske(cx, cy, polys, halb=FENSTER, pix=PIX, schliessen=True):
    """Strassenflaeche als Raster (nur numpy, Scanline mit gerade-ungerade-Regel ueber alle Ringe).
    polys: Liste von Polygonen (Liste von Ringen). -> (bool-Array [zeile=y, spalte=x], x0, y0)."""
    n = int(2 * halb / pix)
    x0, y0 = cx - halb, cy - halb
    ys = y0 + (np.arange(n) + 0.5) * pix
    E = []
    for rings in polys:
        for r in rings:
            r = np.asarray(r, float)
            if len(r) < 3:
                continue
            E.append(np.column_stack([r, np.roll(r, -1, axis=0)]))
    m = np.zeros((n, n), dtype=bool)
    if not E:
        return m, x0, y0
    E = np.vstack(E)
    lo = np.minimum(E[:, 1], E[:, 3]); hi = np.maximum(E[:, 1], E[:, 3])
    E = E[(hi >= y0) & (lo <= y0 + 2 * halb) & (hi > lo)]
    if len(E):
        X1, Y1, X2, Y2 = E.T
        for i, yc in enumerate(ys):
            sel = ((Y1 <= yc) & (yc < Y2)) | ((Y2 <= yc) & (yc < Y1))
            if not sel.any():
                continue
            xs = np.sort(X1[sel] + (yc - Y1[sel]) * (X2[sel] - X1[sel]) / (Y2[sel] - Y1[sel]))
            for k in range(0, len(xs) - 1, 2):
                j0 = int(np.ceil((xs[k] - x0) / pix - 0.5)); j1 = int(np.floor((xs[k + 1] - x0) / pix - 0.5))
                if j1 >= 0 and j0 < n and j1 >= j0:
                    m[i, max(j0, 0):min(j1, n - 1) + 1] = True
    if schliessen:
        r = int(round(SCHLIESSEN_M / pix))
        m = _erodiere(_dilatiere(m, r), r)
    return m, x0, y0


def _scheibe(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return [(int(dy), int(dx)) for dy, dx in zip(yy.ravel(), xx.ravel()) if dy * dy + dx * dx <= r * r]


def _dilatiere(m, r):
    n0, n1 = m.shape
    p = np.pad(m, r)
    out = np.zeros_like(m)
    for dy, dx in _scheibe(r):
        out |= p[r + dy:r + dy + n0, r + dx:r + dx + n1]
    return out


def _erodiere(m, r):
    n0, n1 = m.shape
    p = np.pad(m, r, constant_values=True)
    out = np.ones_like(m)
    for dy, dx in _scheibe(r):
        out &= p[r + dy:r + dy + n0, r + dx:r + dx + n1]
    return out


def r_min(fz):
    rw = fz['wendekreis_m'] / 2.0
    L = fz['radstand_m']
    return max(1.0, math.sqrt(max(rw * rw - L * L, 1.0)) - fz['breite_karosserie_m'] / 2.0)


def _drin(m, x0, y0, xs, ys, pix=PIX):
    i = ((ys - y0) / pix).astype(int); j = ((xs - x0) / pix).astype(int)
    n = m.shape[0]
    ok = (i >= 0) & (i < n) & (j >= 0) & (j < n)
    res = np.zeros(xs.shape, dtype=bool)
    res[ok] = m[i[ok], j[ok]]
    return res


def pruefe(N, u1, u2, fz, m, x0, y0, reserve=RESERVE, anlauf=12.0, quote=0.99):
    """N: Knoten; u1: Fahrtrichtung beim Ankommen; u2: beim Wegfahren (Einheitsvektoren).
    Vektorisiert: fuer festes R ist die ueberstrichene Flaeche starr, die seitlichen Versaetze a/b verschieben sie nur.
    -> (True/False, R, a, b)."""
    u1 = np.asarray(u1, float); u2 = np.asarray(u2, float); N = np.asarray(N, float)
    cr = u1[0] * u2[1] - u1[1] * u2[0]
    delta = math.atan2(cr, max(-1.0, min(1.0, float(u1 @ u2))))
    sig = 1.0 if delta >= 0 else -1.0
    nT1 = sig * np.array([-u1[1], u1[0]]); nT2 = sig * np.array([-u2[1], u2[0]])
    W = fz['breite_karosserie_m'] + 2 * reserve
    L, Of, Or = fz['radstand_m'], fz['ueberhang_vorne_m'], fz['ueberhang_hinten_m']
    A = np.column_stack([u1, -u2])
    if abs(np.linalg.det(A)) < 1e-6:
        return True, None, 0.0, 0.0
    Ainv = np.linalg.inv(A)
    offs = np.arange(-4.0, 4.01, 0.5)
    AA, BB = np.meshgrid(offs, offs, indexing='ij')
    AA = AA.ravel(); BB = BB.ravel()
    Rmin = r_min(fz)
    for R in [Rmin + k for k in (0, 0.5, 1, 2, 3, 4.5, 6, 8, 11, 15, 20)]:
        rhs = np.outer(BB + R, nT2) - np.outer(AA + R, nT1)          # (n, 2)
        ts = rhs @ Ainv.T                                             # (n, 2): t, s
        gueltig = (ts[:, 0] <= 2.0) & (ts[:, 1] >= -2.0) & (ts[:, 0] >= -25.0) & (ts[:, 1] <= 25.0)
        if not gueltig.any():
            continue
        C = N + (AA + R)[:, None] * nT1 + ts[:, 0:1] * u1              # (n, 2)
        # starre Abtastpunkte relativ zu C
        Ri, Ra = R - W / 2.0, math.sqrt((R + W / 2.0) ** 2 + (L + Of) ** 2)
        phi = math.atan2(L + Of, R + W / 2.0)
        th1 = math.atan2(-nT1[1], -nT1[0]); th2 = th1 + delta
        k = max(8, int(abs(delta) * Ra / 0.5))
        th = np.linspace(th1, th2, k); tha = np.linspace(th1, th2 + sig * phi, k + 4)
        rel = [np.column_stack([Ri * np.cos(th), Ri * np.sin(th)]), np.column_stack([Ra * np.cos(tha), Ra * np.sin(tha)]),
               np.column_stack([(Ri + Ra) / 2 * np.cos(th), (Ri + Ra) / 2 * np.sin(th)])]
        if Or > 1.5:
            Rh = math.sqrt((R + W / 2.0) ** 2 + Or ** 2)
            thh = np.linspace(th1, th1 + 0.5 * delta, 8)
            rel.append(np.column_stack([Rh * np.cos(thh), Rh * np.sin(thh)]))
        T1r = -R * nT1; T2r = -R * nT2
        ss = np.linspace(-anlauf, 0, 13); ee = np.linspace(0, anlauf + L + Of, 17)
        for side in (-W / 2.0, 0.0, W / 2.0):
            rel.append(T1r + ss[:, None] * u1 + side * nT1)
            rel.append(T2r + ee[:, None] * u2 + side * nT2)
        rel = np.vstack(rel)                                          # (k, 2)
        X = C[:, 0:1] + rel[None, :, 0]; Y = C[:, 1:2] + rel[None, :, 1]
        inside = _drin(m, x0, y0, X.ravel(), Y.ravel()).reshape(X.shape).mean(axis=1)
        inside[~gueltig] = 0
        i = int(np.argmax(inside))
        if inside[i] >= quote:
            return True, R, float(AA[i]), float(BB[i])
    return False, None, None, None


def abdeckung(N, u1, u2, m, x0, y0, laenge=15.0):
    """Anteil der Achspunkte (15 m vor und nach dem Knoten), die auf der Flaeche liegen."""
    ss = np.linspace(0.5, laenge, 20)
    X = np.concatenate([N[0] - ss * u1[0], N[0] + ss * u2[0]]); Y = np.concatenate([N[1] - ss * u1[1], N[1] + ss * u2[1]])
    return _drin(m, x0, y0, X, Y).mean()


def bewerte_abbiegen(N, u1, u2, fz, m_strasse, m_alle, x0, y0):
    if abdeckung(N, u1, u2, m_alle if m_alle is not None else m_strasse, x0, y0) < 0.6:
        return 'KEINE_DATEN', None
    ok, R, a, b = pruefe(N, u1, u2, fz, m_strasse, x0, y0)
    if ok:
        return 'OK', R
    ok, R, a, b = pruefe(N, u1, u2, fz, m_strasse, x0, y0, reserve=0.0)
    if ok:
        return 'ENG', R
    if m_alle is not None:
        ok, R, a, b = pruefe(N, u1, u2, fz, m_alle, x0, y0, reserve=0.0)
        if ok:
            return 'NUR_MIT_NEBENFLAECHE', R
    return 'UNMOEGLICH', None


# ===================================================================== V8.1: Fahrsimulation entlang der echten Achse
def _resample(pts, step=0.5):
    pts = np.asarray(pts, float)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    if d[-1] <= 0:
        return pts
    s = np.arange(0, d[-1] + 1e-9, step)
    return np.column_stack([np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])])


def _glaetten(P, fenster_m, step=0.5):
    k = int(fenster_m / step)
    if k < 2:
        return P
    pad = k
    a = P[0] - (P[1] - P[0]) * np.arange(pad, 0, -1)[:, None]
    b = P[-1] + (P[-1] - P[-2]) * np.arange(1, pad + 1)[:, None]
    Q = np.vstack([a, P, b])
    ker = np.ones(k) / k
    return np.column_stack([np.convolve(Q[:, 0], ker, 'same'), np.convolve(Q[:, 1], ker, 'same')])[pad:-pad]


def _normalen(P):
    d = np.gradient(P, axis=0)
    n = np.column_stack([-d[:, 1], d[:, 0]])
    return n / np.maximum(np.hypot(n[:, 0], n[:, 1]), 1e-9)[:, None]


def _min_radius(P, basis=4):
    a, b, c = P[:-2 * basis], P[basis:-basis], P[2 * basis:]
    if len(a) == 0:
        return 1e9
    ab = np.hypot(*(b - a).T); bc = np.hypot(*(c - b).T); ca = np.hypot(*(a - c).T)
    cr = np.abs((b - a)[:, 0] * (c - a)[:, 1] - (b - a)[:, 1] * (c - a)[:, 0])
    r = ab * bc * ca / np.maximum(2 * cr, 1e-9)
    return float(r.min())


def _kandidaten(achse_in, achse_out):
    """Vorderachs-Bahnen: Achse geglaettet (Kurve weiter ausfahren) und seitlich versetzt, mit Spurwechsel um den Knoten.
    -> Array (n_kand, n_schritte, 2) und Liste der Parameter."""
    P = _resample(np.vstack([np.asarray(achse_in, float), np.asarray(achse_out, float)[1:]]))
    Pin = _resample(np.asarray(achse_in, float))
    sk = np.arange(len(P)) * 0.5
    blend = np.clip((sk - ((len(Pin) - 1) * 0.5 - 8.0)) / 16.0, 0.0, 1.0)
    ab = [(0.0, 0.0)] + [(x, y) for x in (-2.0, -1.0, 0.0, 1.0, 2.0) for y in (-2.0, -1.0, 0.0, 1.0, 2.0) if (x, y) != (0.0, 0.0)]
    F, par = [], []
    for glatt in (0, 6, 12, 20, 30):
        G = _glaetten(P, glatt)
        ng = _normalen(G)
        for oa, ob in ab:
            F.append(G + (oa + (ob - oa) * blend)[:, None] * ng)
            par.append((glatt, oa, ob))
    return np.asarray(F), par


def _krumm_ok(F, rv_min, basis=4):
    a, b, c = F[:, :-2 * basis], F[:, basis:-basis], F[:, 2 * basis:]
    ab = np.hypot(*(b - a).transpose(2, 0, 1)); bc = np.hypot(*(c - b).transpose(2, 0, 1)); ca = np.hypot(*(a - c).transpose(2, 0, 1))
    cr = np.abs((b - a)[..., 0] * (c - a)[..., 1] - (b - a)[..., 1] * (c - a)[..., 0])
    r = ab * bc * ca / np.maximum(2 * cr, 1e-9)
    return r.min(axis=1) >= rv_min * 0.95


def pruefe_sim(achse_in, achse_out, fz, m, x0, y0, reserve=RESERVE, quote=0.985, kand=None):
    """Vorderachse folgt der Kandidatenbahn, Hinterachse kinematisch (Traktrix); Karosserie in jedem Schritt geprueft.
    Vektorisiert ueber alle Kandidaten. -> (True/False, Parameter oder bester Anteil)."""
    F, par = kand if kand is not None else _kandidaten(achse_in, achse_out)
    if F.shape[1] < 12:
        return True, None
    W = fz['breite_karosserie_m'] + 2 * reserve
    L, Of, Or = fz['radstand_m'], fz['ueberhang_vorne_m'], fz['ueberhang_hinten_m']
    ok = _krumm_ok(F, math.hypot(r_min(fz), L))
    if not ok.any():
        return False, 0.0
    F = F[ok]; par = [p for p, k in zip(par, ok) if k]
    h0 = F[:, 1] - F[:, 0]; h0 /= np.maximum(np.hypot(h0[:, 0], h0[:, 1]), 1e-9)[:, None]
    Rr = F[:, 0] - L * h0
    pts = []
    for i in range(1, F.shape[1]):
        v = F[:, i] - Rr
        v /= np.maximum(np.hypot(v[:, 0], v[:, 1]), 1e-9)[:, None]
        Rr = F[:, i] - L * v
        if i % 2:
            continue
        n = np.column_stack([-v[:, 1], v[:, 0]])
        for lang in (-Or, 0.0, L, L + Of):
            for q in (-W / 2, W / 2):
                pts.append(Rr + lang * v + q * n)
    pts = np.stack(pts, axis=1)                      # (n_kand, n_pkt, 2)
    frac = _drin(m, x0, y0, pts[..., 0].ravel(), pts[..., 1].ravel()).reshape(pts.shape[:2]).mean(axis=1)
    i = int(np.argmax(frac))
    if frac[i] >= quote:
        return True, par[i]
    return False, round(float(frac[i]), 3)


def bewerte_fahrt(achse_in, achse_out, fz, m_strasse, m_alle, x0, y0):
    """-> OK | ENG | NUR_MIT_NEBENFLAECHE | UNMOEGLICH | KEINE_DATEN"""
    P = _resample(np.vstack([np.asarray(achse_in, float), np.asarray(achse_out, float)[1:]]))
    mm = m_alle if m_alle is not None else m_strasse
    if _drin(mm, x0, y0, P[:, 0], P[:, 1]).mean() < 0.6:
        return 'KEINE_DATEN', None
    kand = _kandidaten(achse_in, achse_out)
    ok, info = pruefe_sim(achse_in, achse_out, fz, m_strasse, x0, y0, kand=kand)
    if ok:
        return 'OK', info
    ok, info2 = pruefe_sim(achse_in, achse_out, fz, m_strasse, x0, y0, reserve=0.0, kand=kand)
    if ok:
        return 'ENG', info2
    if m_alle is not None:
        ok, info3 = pruefe_sim(achse_in, achse_out, fz, m_alle, x0, y0, reserve=0.0, kand=kand)
        if ok:
            return 'NUR_MIT_NEBENFLAECHE', info3
    return 'UNMOEGLICH', info
