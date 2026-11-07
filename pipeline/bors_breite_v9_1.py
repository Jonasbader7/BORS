# -*- coding: utf-8 -*-
"""BORS V9 - geometrische Messung der freien Durchfahrtsbreite (reines Python + numpy, ohne GDAL/QGIS).

Wird von 25_Breite_V9.py per exec() geladen. Methode und Begruendung: siehe METHODE_V9 unten und BORS_V9_Methode.md.
"""
import math
from collections import defaultdict

import numpy as np

# ------------------------------------------------------------------ Parameter (alle im Bericht ausgewiesen)
PROFIL_ABSTAND_M = 1.0          # Querprofil je Meter (V5: 2 m)
HALB_M = 20.0                   # halbe Profillaenge; Fahrbahn bis an diese Grenze = "Suchgrenze" (sehr breit / Platz)
NAHT_M = 0.05                   # aneinanderstossende AV-Flaechen gelten als eine Flaeche
ACHSE_TOL_M = 1.5               # OSM-Achse darf so weit neben der AV-Fahrbahn liegen ("Achse versetzt")
VERSETZT_MIN_M = 1.94           # ... aber nur, wenn daneben mind. eine Fahrzeugbreite (Karosserie Profil A) Flaeche liegt
GLAETTEN_M = 3.0                # Achsrichtung aus Sehne +-3 m
WINKEL_GRAD = (-20.0, -10.0, 0.0, 10.0, 20.0)   # gedrehte Profile: kleinste Breite = senkrecht zur Fahrbahn
NACHBAR_M = 0.15                # Abstand, in dem die Nachbarflaeche ausserhalb des Fahrbahnrands gesucht wird
K_VERTRAUEN = 1.645             # V9.1: einseitige 95-%-Schranke (Normalverteilung) auf die Standardabweichung der Breite
FENSTER = 3                     # robuste Engstelle: zweitkleinster Wert in 3 aufeinanderfolgenden Profilen
LUECKE_INNEN_MAX_M = 3.0        # groesste tolerierte Messluecke im Inneren eines Abschnitts
RAND_M = 8.0                    # Luecken bis 8 m an den Abschnittsenden (Kreuzungsbereich) werden separat gezaehlt

# V9.1: Lagegenauigkeit exakt definierter Punkte nach den geltenden Erfassungsgrundsaetzen BB/EO (cadastre-manual, Tab. 1,
# Stand 2024; VAV-VBS Art. 4 delegiert die Werte an die Weisungen): TS1 <= 0.10, TS2 0.10, TS3 0.20, TS4 0.50, TS5 1.00 m.
# Fuer nicht exakt definierte Raender (unbefestigt/naturnah) gibt es keinen aktuellen Wert -> hilfsweise TVAV Art. 31 Abs. 2 (aufgehoben).
# Breite = Differenz zweier Randpositionen; Raender als unabhaengig angenommen (konservativ; gleiche Aufnahme waere positiv korreliert).
# Lagegenauigkeit (Standardabweichung, m) nach TVAV (SR 211.432.21)
#  Art. 29: exakt definierte Punkte Bodenbedeckung/Einzelobjekte: TS1 <= 0.10, TS2 0.10, TS3 0.20, TS4 0.50, TS5 1.00
#  Art. 31 Abs. 2: nicht exakt definierte Punkte (z. B. entlang Strassenraendern): TS2 0.20, TS3 0.35, TS4 0.75, TS5 1.50
SIGMA_EXAKT = {1: 0.10, 2: 0.10, 3: 0.20, 4: 0.50, 5: 1.00}
SIGMA_UNSCHARF = {1: 0.20, 2: 0.20, 3: 0.35, 4: 0.75, 5: 1.50}
# Rand gegen diese Nachbarflaechen = exakt definiert (Randstein, Fassade, Mauerfuss, Belagsrand)
# V9.1: Rand eines befestigten Belags gegen gepflegte Gruenflaechen (Garten, Rabatte) = Belagsrand/Randabschluss = exakt definiert.
#       Ist die Strasse laut OSM befestigt (asphalt, paved, ...), gilt der Belagsrand unabhaengig von der Nachbarflaeche als exakt.
NATURNAH = {'Acker, Wiese, Weide', 'geschlossener Wald', 'übrige bestockte', 'Fels', 'Geröll, Sand', 'fliessendes Gewässer',
            'stehendes Gewässer', 'Schilfgürtel', 'übrige vegetationslose', 'Abbau, Deponie', 'keine AV-Flaeche'}
BEFESTIGT_OSM = {'asphalt', 'paved', 'concrete', 'concrete:plates', 'concrete:lanes', 'paving_stones', 'sett', 'cobblestone', 'unhewn_cobblestone', 'metal'}
EXAKT = {'Gartenanlage', 'übrige humusierte', 'übrige Intensivkultur', 'Reben', 'Gebäude', 'Trottoir', 'Verkehrsinsel', 'Bahn', 'übrige befestigte', 'Wasserbecken', 'Strasse, Weg',
         'Flugplatz', 'EO:Mauer', 'EO:Pfeiler', 'EO:Treppe', 'EO:Unterstand', 'EO:Brunnen', 'EO:Sockel', 'EO:Mast'}
# fester, nicht ueberfahrbarer Rand (fuer den Nachweis "zu eng"): Gruenflaechen gehoeren NICHT dazu
HART = EXAKT - {'Gartenanlage', 'übrige humusierte', 'übrige Intensivkultur', 'Reben'}
# Einzelobjekte, die am Boden die Fahrbahn einengen (Flaechen und Linien). Nicht dazu: Vordaecher/Arkaden
# ("uebriger Gebaeudeteil"), unterirdische Bauten, Bruecken, Tunnel, eingedolte Gewaesser, Freileitungen, Bahngeleise.
EO_HINDERNIS = {'Mauer': 'EO:Mauer', 'Pfeiler': 'EO:Pfeiler', 'wichtige Treppe': 'EO:Treppe',
                'Brunnen': 'EO:Brunnen', 'massiver Sockel': 'EO:Sockel', 'Mast Antenne': 'EO:Mast', 'Denkmal': 'EO:Denkmal',
                'Silo Turm Gasometer': 'EO:Bauwerk', 'Hochkamin': 'EO:Bauwerk', 'Aussichtsturm': 'EO:Bauwerk',
                'einzelner Fels': 'EO:Fels'}
# Nicht als Bodenhindernis: Unterstand (Dach, Hoehenthema), Bahnsteig, Uferverbauung (liegen neben/unter der Fahrbahn).
UEBERLAGERT_ANTEIL = 0.5        # Objekt deckt >= 50 % der Fahrbahnbreite ab -> liegt unter/ueber der Fahrbahn, kein Bodenhindernis
PARK_STREIFEN_MAX_M = 2.0       # ungenau verortete Parkfelder: Streifen am naeheren Fahrbahnrand, hoechstens 2.0 m (Laengsparkfeld)


class Kantenindex:
    """Kanten aller Flaechen (oder Linien) in einem Rasterindex."""

    def __init__(self, zelle=40.0):
        self.zelle = zelle
        self.k, self.f = [], []
        self.grid = defaultdict(list)
        self.info = {}
        self.rng = {}

    def add(self, fid, ringe, geschlossen=True, **info):
        self.info[fid] = info
        start = len(self.k)
        flach = []
        for r in ringe:                                   # [Polygon[Ring[(x,y)]]] oder [Ring]
            if r and isinstance(r[0], (list, tuple)) and r[0] and isinstance(r[0][0], (list, tuple)):
                flach.extend(r)
            else:
                flach.append(r)
        for r in flach:
            r = [tuple(q[:2]) for q in r]
            if len(r) < 2:
                continue
            paare = list(zip(r, r[1:]))
            if geschlossen and r[0] != r[-1]:
                paare.append((r[-1], r[0]))
            for (x0, y0), (x1, y1) in paare:
                if x0 == x1 and y0 == y1:
                    continue
                i = len(self.k)
                self.k.append((x0, y0, x1, y1)); self.f.append(fid)
                z = self.zelle
                for gx in range(int(math.floor(min(x0, x1) / z)), int(math.floor(max(x0, x1) / z)) + 1):
                    for gy in range(int(math.floor(min(y0, y1) / z)), int(math.floor(max(y0, y1) / z)) + 1):
                        self.grid[(gx, gy)].append(i)
        self.rng[fid] = (start, len(self.k))

    def innen(self, fid, x, y):
        """Punkt-in-Flaeche (Gerade-Ungerade, alle Ringe der Flaeche)."""
        a, b = self.rng[fid]
        K = self._K[a:b]
        y0, y1 = K[:, 1], K[:, 3]
        m = (y0 > y) != (y1 > y)
        if not m.any():
            return False
        K = K[m]
        xs = K[:, 0] + (y - K[:, 1]) * (K[:, 2] - K[:, 0]) / (K[:, 3] - K[:, 1])
        return bool((xs > x).sum() % 2)

    def fertig(self):
        self._K = np.array(self.k, dtype=float).reshape(-1, 4)
        self._F = np.array(self.f, dtype=np.int64)
        self.grid = {k: np.array(v, dtype=np.int64) for k, v in self.grid.items()}
        self.k = self.f = None
        return self

    def nahe(self, x0, y0, x1, y1):
        z = self.zelle
        ids = [self.grid[(gx, gy)] for gx in range(int(math.floor(x0 / z)), int(math.floor(x1 / z)) + 1)
               for gy in range(int(math.floor(y0 / z)), int(math.floor(y1 / z)) + 1) if (gx, gy) in self.grid]
        if not ids:
            return np.zeros((0, 4)), np.zeros(0, dtype=np.int64)
        u = np.unique(np.concatenate(ids))
        return self._K[u], self._F[u]


def profile(pts, abstand=PROFIL_ABSTAND_M):
    """Polylinie -> Stationen s, Punkte P (n,2), Normalen N (n,2) (links positiv)."""
    p = np.asarray(pts, dtype=float)[:, :2]
    d = np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1]))
    p = p[np.concatenate([[True], d > 1e-6])]
    if len(p) < 2:
        return np.zeros(0), np.zeros((0, 2)), np.zeros((0, 2))
    cum = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1])))])
    L = cum[-1]
    s = np.array([L / 2.0]) if L < abstand else np.arange(abstand / 2.0, L, abstand)

    def at(ss):
        ss = np.clip(ss, 0, L)
        return np.column_stack([np.interp(ss, cum, p[:, 0]), np.interp(ss, cum, p[:, 1])])
    P = at(s)
    T = at(s + GLAETTEN_M) - at(s - GLAETTEN_M)
    n = np.hypot(T[:, 0], T[:, 1]); n[n == 0] = 1
    T = T / n[:, None]
    return s, P, np.column_stack([-T[:, 1], T[:, 0]])


def drehen(N, grad):
    a = math.radians(grad); c, s = math.cos(a), math.sin(a)
    return np.column_stack([c * N[:, 0] - s * N[:, 1], s * N[:, 0] + c * N[:, 1]])


def schnitte(P, N, K, halb=HALB_M):
    """t der Schnitte Profil i (P_i + t N_i) mit Kante j -> (n,m), nan = kein Schnitt."""
    if len(K) == 0 or len(P) == 0:
        return np.full((len(P), len(K)), np.nan)
    ax, ay = K[:, 0][None, :], K[:, 1][None, :]
    ex, ey = (K[:, 2] - K[:, 0])[None, :], (K[:, 3] - K[:, 1])[None, :]
    px, py = P[:, 0][:, None], P[:, 1][:, None]
    nx, ny = N[:, 0][:, None], N[:, 1][:, None]
    den = nx * ey - ny * ex
    with np.errstate(divide='ignore', invalid='ignore'):
        t = ((ax - px) * ey - (ay - py) * ex) / den
        u = ((ax - px) * ny - (ay - py) * nx) / den
    ok = (np.abs(den) > 1e-12) & (u >= 0) & (u < 1) & (np.abs(t) <= halb)
    return np.where(ok, t, np.nan)


def intervalle(T, F, halb=HALB_M, P=None, N=None, idx=None):
    """Gerade-Ungerade-Regel je Flaeche -> je Profil [(lo, hi, fid)].
    Ungerade Schnittzahl (Profil beginnt/endet in der Flaeche): Punkt-in-Flaeche-Test am Profilanfang (idx noetig)."""
    out = [[] for _ in range(T.shape[0])]
    if T.shape[1] == 0:
        return out
    for fid in np.unique(F):
        sp = T[:, F == fid]
        for i in np.nonzero(np.any(~np.isnan(sp), axis=1))[0]:
            v = np.sort(sp[i][~np.isnan(sp[i])])
            if len(v) % 2 == 1:
                if idx is not None:
                    x0, y0 = P[i] - halb * N[i]
                    anfang_innen = idx.innen(int(fid), x0, y0)
                else:
                    anfang_innen = False
                v = np.insert(v, 0, -halb) if anfang_innen else np.append(v, halb)
            for a, b in zip(v[0::2], v[1::2]):
                if b - a > 1e-6:
                    out[i].append((a, b, int(fid)))
    return out


def linienpunkte(T, F):
    """Linien-Einzelobjekte: Schnittpunkte je Profil [(t, fid)]"""
    out = [[] for _ in range(T.shape[0])]
    ii, jj = np.nonzero(~np.isnan(T))
    for i, j in zip(ii, jj):
        out[i].append((float(T[i, j]), int(F[j])))
    return out


def vereinigen(iv, naht=NAHT_M):
    """-> [(lo, hi, fid_lo, fid_hi)]"""
    if not iv:
        return []
    iv = sorted(iv)
    res = [[iv[0][0], iv[0][1], iv[0][2], iv[0][2]]]
    for a, b, f in iv[1:]:
        if a <= res[-1][1] + naht:
            if b > res[-1][1]:
                res[-1][1] = b; res[-1][3] = f
        else:
            res.append([a, b, f, f])
    return [tuple(r) for r in res]


def hauptintervall(u):
    for a, b, fa, fb in u:
        if a <= 0 <= b:
            return (a, b, fa, fb), False
    if u:
        q = min(u, key=lambda q: min(abs(q[0]), abs(q[1])))
        if min(abs(q[0]), abs(q[1])) <= ACHSE_TOL_M:
            return q, True
    return None, False


def abziehen(lo, hi, stuecke):
    """Groesstes freies Teilstueck von [lo,hi] ohne 'stuecke' [(a,b)]. -> (breite, a, b)"""
    frei = [(lo, hi)]
    for a, b in stuecke:
        neu = []
        for x, y in frei:
            if b <= x or a >= y:
                neu.append((x, y)); continue
            if a > x:
                neu.append((x, a))
            if b < y:
                neu.append((b, y))
        frei = neu
    if not frei:
        return 0.0, lo, lo
    x, y = max(frei, key=lambda q: q[1] - q[0])
    return y - x, x, y


def robustes_minimum(w, gueltig, fenster=FENSTER):
    """Engste zusammenhaengende Stelle: kleinster 'zweitkleinster Wert' ueber alle Fenster aus 'fenster'
    gueltigen aufeinanderfolgenden Profilen (eine einzelne Messung bestimmt die Engstelle nie allein).
    -> (wert, index des massgebenden Profils) oder (nan, -1). Abschnitte mit < fenster Profilen: Minimum aller gueltigen."""
    n = len(w)
    if n < fenster:
        if gueltig.any():
            i = int(np.nanargmin(np.where(gueltig, w, np.nan)))
            return float(w[i]), i
        return float('nan'), -1
    best, bi = float('nan'), -1
    for i in range(n - fenster + 1):
        if not gueltig[i:i + fenster].all():
            continue
        o = np.argsort(w[i:i + fenster])
        v = w[i + o[1]]
        if math.isnan(best) or v < best:
            best, bi = float(v), i + int(o[1])
    return best, bi


def luecken(gueltig, abstand=PROFIL_ABSTAND_M, rand_m=RAND_M):
    """-> (groesste zusammenhaengende Luecke m, groesste Luecke im Inneren m, Anzahl Luecken)"""
    n = len(gueltig)
    runs, i = [], 0
    while i < n:
        if not gueltig[i]:
            j = i
            while j < n and not gueltig[j]:
                j += 1
            runs.append((i, j)); i = j
        else:
            i += 1
    if not runs:
        return 0.0, 0.0, 0
    ges = max((j - i) * abstand for i, j in runs)
    r = int(round(rand_m / abstand))
    innen = [(max(i, r), min(j, n - r)) for i, j in runs]
    innen = [(j - i) * abstand for i, j in innen if j > i]
    return ges, (max(innen) if innen else 0.0), len(runs)


def entscheide(bedarf, w_lo, w_lo_fest, w_hi_fest, messbar, luecke_innen, grund_nicht_messbar=None, minimum=None):
    """Drei fachliche Ergebnisse je Profil (asymmetrisch, beide Richtungen mit der jeweils guenstigsten Annahme fuer die Gegenseite):
    AUSREICHEND   untere Schranke (Parkfelder belegt, minus k*sigma) >= Bedarf (Spiegel + Reserve innerhalb der Fahrbahn)
    UNZUREICHEND  obere Schranke der festen Breite (ohne Parkierung, plus k*sigma) < 'minimum' = Karosseriebreite ohne Reserve
                  (Spiegel eingeklappt bzw. ueber Trottoir/Insel, keine Fahrreserve): physikalisch nicht passierbar
    sonst         NICHT_ENTSCHEIDBAR mit Grund. -> (ergebnis, grund)"""
    if not messbar:
        return 'NICHT_ENTSCHEIDBAR', grund_nicht_messbar or 'keine ausreichende Messung'
    grenze = bedarf if minimum is None else minimum
    if w_hi_fest < grenze:
        return 'UNZUREICHEND', 'auch ohne Parkierung, mit Messtoleranz und ohne Reserve zu schmal: hoechstens {:.2f} m < Karosserie {:.2f} m'.format(w_hi_fest, grenze)
    if w_lo >= bedarf:
        if luecke_innen > LUECKE_INNEN_MAX_M:
            return 'NICHT_ENTSCHEIDBAR', 'gemessene Teile reichen (mind. {:.2f} m), aber Messluecke von {:.0f} m im Abschnitt'.format(w_lo, luecke_innen)
        return 'AUSREICHEND', 'mindestens {:.2f} m >= Bedarf {:.2f} m (Parkfelder belegt, Messtoleranz abgezogen)'.format(w_lo, bedarf)
    if w_lo_fest >= bedarf:
        return 'NICHT_ENTSCHEIDBAR', 'feste Breite reicht (mind. {:.2f} m), bei belegten Parkfeldern nur {:.2f} m < Bedarf {:.2f} m'.format(
            w_lo_fest, w_lo, bedarf)
    if w_hi_fest < bedarf:
        return 'NICHT_ENTSCHEIDBAR', 'nur mit Spiegel ueber Trottoir/Insel oder ohne Fahrreserve passierbar (hoechstens {:.2f} m < Bedarf {:.2f} m, >= Karosserie)'.format(
            w_hi_fest, bedarf)
    return 'NICHT_ENTSCHEIDBAR', 'Bedarf {:.2f} m liegt innerhalb der Messtoleranz ({:.2f} .. {:.2f} m)'.format(bedarf, w_lo_fest, w_hi_fest)
