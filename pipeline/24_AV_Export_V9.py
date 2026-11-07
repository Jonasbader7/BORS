# -*- coding: utf-8 -*-
"""BORS 24 (V9): Export amtliche Vermessung (MOPUBE) fuer die Breitenmessung V9.
Liest Downloads\\mopube.gpkg\\MOPUBE.gpkg (nur lesen) und schreibt NUR Objekte bis 25 m neben dem Strassennetz in
Documents\\BORS_V9\\av_export_<zeit>.gpkg:
  bb   = Bodenbedeckung, ALLE Arten (Strasse/Weg, Trottoir, Verkehrsinsel, Gebaeude, Gewaesser, Gruen, ...)
  eof  = Einzelobjekte Flaeche (Mauer, Treppe, Brunnen, Unterstand, Pfeiler, ...)
  eol  = Einzelobjekte Linie (Mauer schmal, Zaun?, Rinnsal, ...)
  eop  = Einzelobjekte Punkt (Mast, Antenne, Einzelbaum, ...)
Jeweils mit Art, Bezeichnung, Qualitaetsstandard (Genauigkeit) und Gueltigkeit. Nichts wird ueberschrieben.
Dauer: ca. 3-10 Minuten. Am Ende steht die Dateigroesse und die Anzahl je Art in der Konsole.
"""
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from osgeo import ogr, osr
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import QgsGeometry, QgsSpatialIndex, QgsVectorLayer, QgsFeature

HOME = Path.home()
MOPUBE = next((p for p in [HOME / 'Downloads' / 'mopube.gpkg' / 'MOPUBE.gpkg', HOME / 'OneDrive' / 'Desktop' / 'MOPUBE.gpkg'] if p.is_file()), None)
NMDIR = HOME / 'Documents' / 'BORS_V7_QA' / 'netzmaster'
OUT_DIR = HOME / 'Documents' / 'BORS_V9'
ABSTAND_M = 25.0
T0 = time.time()


def log(m):
    print('BORS AV-EXPORT:', m)
    QApplication.processEvents()


if MOPUBE is None:
    raise FileNotFoundError('MOPUBE.gpkg nicht gefunden (Downloads\\mopube.gpkg\\MOPUBE.gpkg)')
nm = sorted(NMDIR.glob('BORS_Netzmaster_V8_*.gpkg'), key=lambda p: p.stat().st_mtime)
if not nm:
    raise FileNotFoundError('Kein Netzmaster V8 gefunden - zuerst 21_Netzmaster_V8 ausfuehren.')
net = QgsVectorLayer('{}|layername=netz_v5'.format(nm[-1]), 'netz', 'ogr')
if not net.isValid():
    raise RuntimeError('Netz nicht lesbar: ' + str(nm[-1]))
idx = QgsSpatialIndex()
geoms = {}
for f in net.getFeatures():
    g = f.geometry()
    if g is None or g.isEmpty():
        continue
    geoms[f.id()] = QgsGeometry(g)
    nf = QgsFeature(f.id()); nf.setGeometry(g); idx.addFeature(nf)
ext = net.extent(); ext.grow(ABSTAND_M + 5)
log('Netz {}: {} Abschnitte'.format(nm[-1].name, len(geoms)))


def nahe(g):
    bb = g.boundingBox(); bb.grow(ABSTAND_M)
    for fid in idx.intersects(bb):
        if geoms[fid].distance(g) <= ABSTAND_M:
            return True
    return False


OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'av_export_{}.gpkg'.format(datetime.now().strftime('%Y%m%d_%H%M'))
tmp = OUT.with_name(OUT.stem + '_IN_ARBEIT.gpkg')
src = ogr.Open(str(MOPUBE), 0)
namen = [src.GetLayerByIndex(i).GetName() for i in range(src.GetLayerCount())]
log('Ebenen in MOPUBE: {}'.format(', '.join(namen)))
srs = osr.SpatialReference(); srs.ImportFromEPSG(2056)
dst = ogr.GetDriverByName('GPKG').CreateDataSource(str(tmp))
bericht = []
for kurz, suffix, typ in (('bb', 'mopube_bbf', ogr.wkbMultiPolygon), ('eof', 'mopube_eof', ogr.wkbMultiPolygon),
                          ('eol', 'mopube_eol', ogr.wkbMultiLineString), ('eop', 'mopube_eop', ogr.wkbPoint)):
    kand = [n for n in namen if n.lower().endswith(suffix) or n.lower().endswith(suffix + '_vw')]
    if not kand:
        log('WARNUNG: Ebene {} nicht gefunden'.format(suffix)); bericht.append('{}: fehlt'.format(kurz)); continue
    sl = src.GetLayerByName(kand[0])
    sl.SetSpatialFilterRect(ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum())
    dfn = sl.GetLayerDefn()
    felder = [dfn.GetFieldDefn(i) for i in range(dfn.GetFieldCount())]
    behalten = [fd for fd in felder if any(k in fd.GetName().lower() for k in ('art', 'bez_de', 'qualit', 'qs', 'gueltig', 'gultig', 'gültig', 'bfsnr', 'egid', 'orient', 'rot'))]
    dl = dst.CreateLayer(kurz, srs, typ)
    for fd in behalten:
        dl.CreateField(ogr.FieldDefn(fd.GetName().lower(), fd.GetType()))
    dst.StartTransaction()
    cnt = Counter(); n = 0
    for f in sl:
        n += 1
        og = f.GetGeometryRef()
        if og is None:
            continue
        g = QgsGeometry.fromWkt(og.ExportToWkt())
        if g is None or g.isEmpty() or not nahe(g):
            continue
        of = ogr.Feature(dl.GetLayerDefn())
        for fd in behalten:
            of.SetField(fd.GetName().lower(), f.GetField(fd.GetName()))
        gg = og.Clone()
        if typ == ogr.wkbMultiPolygon:
            gg = ogr.ForceToMultiPolygon(gg)
        elif typ == ogr.wkbMultiLineString:
            gg = ogr.ForceToMultiLineString(gg)
        of.SetGeometry(gg)
        dl.CreateFeature(of)
        bez = [fd.GetName() for fd in behalten if 'bez_de' in fd.GetName().lower()]
        cnt[str(f.GetField(bez[0])) if bez else str(f.GetField('art'))] += 1
        if n % 20000 == 0:
            log('  {}: {} gelesen, {:.0f} s'.format(kurz, n, time.time() - T0))
    dst.CommitTransaction()
    log('{} ({}): {} Objekte nahe Netz von {} gelesen | {}'.format(kurz, kand[0], sum(cnt.values()), n, dict(cnt.most_common(25))))
    bericht.append('{} ({}): {} | {}'.format(kurz, kand[0], sum(cnt.values()), dict(cnt.most_common())))
dst = None; src = None
tmp.rename(OUT)
OUT.with_suffix('.txt').write_text('\n'.join(bericht), encoding='utf-8')
log('Fertig in {:.0f} s: {} ({:.1f} MB). Bitte Claude Bescheid geben.'.format(time.time() - T0, OUT, OUT.stat().st_size / 1e6))
