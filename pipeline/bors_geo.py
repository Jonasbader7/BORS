# -*- coding: utf-8 -*-
"""BORS Bern - kleine Geometrie-Hilfen ohne GDAL/QGIS (GeoPackage-WKB lesen, Punkt-auf-Linie, Raster-Index).
Wird von 21_Netzmaster_V8.py und dem Router V8 per exec() geladen. Reines Python + numpy."""
import math
import struct


def gp_wkb(blob):
    """GeoPackage-Blob -> WKB-Bytes (Header entfernen)."""
    b = bytes(blob)
    if b[:2] != b'GP':
        return b
    o = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(b[3] >> 1) & 7]
    return b[o:]


def _read(b, o):
    bo = '<' if b[o] == 1 else '>'
    t = struct.unpack(bo + 'I', b[o + 1:o + 5])[0]
    o += 5
    flag_z = bool(t & 0x80000000) or (1000 <= (t & 0xffff) < 2000) or (3000 <= (t & 0xffff) < 4000)
    flag_m = bool(t & 0x40000000) or (2000 <= (t & 0xffff) < 4000)
    base = (t & 0xffff) % 1000
    dim = 2 + (1 if flag_z else 0) + (1 if flag_m else 0)
    if base == 1:
        x, y = struct.unpack(bo + 'dd', b[o:o + 16])
        return ('P', [(x, y)]), o + 8 * dim
    if base in (2, 8):                       # LineString, CircularString
        n = struct.unpack(bo + 'I', b[o:o + 4])[0]; o += 4
        pts = [struct.unpack(bo + 'dd', b[o + 8 * dim * i:o + 8 * dim * i + 16]) for i in range(n)]
        return ('L', pts), o + 8 * dim * n
    if base == 3:
        n = struct.unpack(bo + 'I', b[o:o + 4])[0]; o += 4
        rings = []
        for _ in range(n):
            m = struct.unpack(bo + 'I', b[o:o + 4])[0]; o += 4
            rings.append([struct.unpack(bo + 'dd', b[o + 8 * dim * i:o + 8 * dim * i + 16]) for i in range(m)])
            o += 8 * dim * m
        return ('A', rings), o
    if base in (4, 5, 6, 7, 9, 10, 11, 12):   # Multi*, Collection, CompoundCurve, CurvePolygon, MultiCurve, MultiSurface
        n = struct.unpack(bo + 'I', b[o:o + 4])[0]; o += 4
        parts = []
        for _ in range(n):
            g, o = _read(b, o)
            parts.append(g)
        if base == 9:      # CompoundCurve -> eine Linie
            pts = []
            for k, p in parts:
                pts += p if not pts else p[1:]
            return ('L', pts), o
        if base == 10:     # CurvePolygon -> Ringe
            return ('A', [p for k, p in parts]), o
        return ('M', parts), o
    raise ValueError('WKB-Typ {} nicht unterstuetzt'.format(t))


def geom(blob):
    g, _ = _read(gp_wkb(blob), 0)
    return g


def linien(blob):
    """-> Liste von Punktlisten (Linien-Teile)."""
    out = []
    def walk(g):
        k, v = g
        if k == 'L':
            out.append(v)
        elif k == 'M':
            for p in v:
                walk(p)
    walk(geom(blob))
    return [p for p in out if len(p) >= 2]


def ringe(blob):
    """-> Liste von Polygonen, je Polygon Liste von Ringen."""
    out = []
    def walk(g):
        k, v = g
        if k == 'A':
            out.append(v)
        elif k == 'M':
            for p in v:
                walk(p)
    walk(geom(blob))
    return out


def punkt(blob):
    """Punkt bzw. Schwerpunkt (Mittel der Aussenring-Stuetzpunkte) einer Flaeche."""
    g = geom(blob)
    k, v = g
    if k == 'P':
        return v[0]
    pts = []
    for poly in ringe(blob):
        pts += poly[0]
    if not pts:
        for l in linien(blob):
            pts += l
    if not pts:
        return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def projiziere(pts, x, y):
    """Lotfusspunkt auf Polylinie -> (abstand, position_entlang, px, py)."""
    best = None; cum = 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay; l2 = dx * dx + dy * dy; L = math.sqrt(l2)
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / l2))
        px, py = ax + t * dx, ay + t * dy
        d = math.hypot(x - px, y - py)
        if best is None or d < best[0]:
            best = (d, cum + t * L, px, py)
        cum += L
    return best


def laenge(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def punkt_bei(pts, s):
    """Punkt und Richtung (Einheitsvektor) bei Laufmeter s."""
    cum = 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, by - ay)
        if L > 0 and cum + L >= s:
            t = (s - cum) / L
            return (ax + t * (bx - ax), ay + t * (by - ay)), ((bx - ax) / L, (by - ay) / L)
        cum += L
    (ax, ay), (bx, by) = pts[-2], pts[-1]
    L = math.hypot(bx - ax, by - ay) or 1.0
    return (bx, by), ((bx - ax) / L, (by - ay) / L)


class Raster:
    """Einfacher Gitter-Index fuer Objekte mit Bounding Box."""
    def __init__(self, g=100.0):
        self.g = g; self.z = {}

    def add(self, key, x0, y0, x1, y1):
        g = self.g
        for i in range(int(x0 // g), int(x1 // g) + 1):
            for j in range(int(y0 // g), int(y1 // g) + 1):
                self.z.setdefault((i, j), []).append(key)

    def nahe(self, x0, y0, x1, y1):
        g = self.g; out = set()
        for i in range(int(x0 // g), int(x1 // g) + 1):
            for j in range(int(y0 // g), int(y1 // g) + 1):
                out.update(self.z.get((i, j), ()))
        return out
