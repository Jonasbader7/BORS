# -*- coding: utf-8 -*-
r"""BORS 6 V9.2f (_BORS, 1.11.2026): wie 6_Projekt_V9_BORS, dazu Legende fuer Befunde aus 26_Netzmaster_V9_2f_BORS
  (Nachweisqualitaet Breite: FELD / ORTHOFOTO / FACHSTELLE) und Hinweis auf Router V9.2e.
STARTEN (QGIS-Python-Konsole, Ablage BORS):
    from pathlib import Path
    p = Path.home() / 'OneDrive' / 'Desktop' / 'BORS' / '01_Skripte' / 'Aktuell' / '6_Projekt_V9_2f_BORS.py'
    exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'))
BORS Bern - 6 V9: Projekt auf Basis Netzmaster V9 (Breite geometrisch A-D, Routing validiert/unvalidiert/gesperrt).
Vorher V8: Projekt auf Basis Netzmaster V8 (Fahrzeug-Kategorien a-d_kat_v8, Abbiegen, neue Farben: "kein Hinweis" blau statt gruen).
Schreibt IMMER eine neue Datei Desktop\BORS_Routing_Bern_V8_<zeit>.qgz; offene Projekte werden nie veraendert.
Alt: Projekt auf Basis Netzmaster V7 (Kategorien *_kat_v7 + Belege). Alte Projekte bleiben unveraendert.
Projektdatei: Desktop\BORS_Routing_Bern_V71.qgz ; Routing-Layer heisst "BORS Netz V7 (Routing)".

STARTEN (QGIS-Python-Konsole):
    from pathlib import Path
    p = Path.home() / 'Downloads' / 'BORS_AKTUELL' / '6_Projekt_V7_1.py'
    exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'))

- Ist ein Projekt "BORS_Routing_Bern_V7*.qgz" offen: Quellen auf die neueste Bewertung umstellen + speichern.
- Sonst: neues Projekt Desktop\BORS_Routing_Bern_V7.qgz schreiben (existiert es, mit Zeitstempel).

Ebenenbaum (5 Gruppen statt 13):
  00 ROUTE (aktuell)      <- fuellt der Router V7
  01 ROUTING              Baustellen (live)                       [5_Baustellen legt neue Baustellen hier ab]
  02 FAHRZEUGKARTE        D / C / B / A  (immer nur eine sichtbar)
  03 BELEGE               Breite, Hoehe, Hindernisse, Kurven, Steigung, Querprofile, Parkfelder, Baeume, KSVB ...
  04 GEBIET               Zielgebiet (11 Gemeinden), Routing-Puffer
  99 SYSTEM               BORS Netz V5 (Routing) - wird vom Router gebraucht, nicht loeschen
  Hintergrund: swisstopo Landeskarte grau (OpenStreetMap als Alternative ausgeschaltet)
"""
import re
from datetime import datetime
from pathlib import Path
# BORS-Ablage: zentrale Pfade aus 01_Skripte/Aktuell/bors_pfade.py (BORS_ROOT ueberschreibbar)
_BR = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
exec(compile((_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py').read_text(encoding='utf-8'), str(_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py'), 'exec'))

from qgis.core import (QgsProject, QgsVectorLayer, QgsRasterLayer, QgsCoordinateReferenceSystem, QgsLineSymbol,
                       QgsMarkerSymbol, QgsFillSymbol, QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsRectangle,
                       QgsReferencedRectangle)



def latest(folder, pattern, min_features=None, layer=None):
    for p in sorted(folder.glob(pattern), reverse=True):
        if p.suffix != '.gpkg':
            continue
        if min_features:
            l = QgsVectorLayer('{}|layername={}'.format(p, layer), 'chk', 'ogr')
            if not l.isValid() or l.featureCount() < min_features:
                continue
        return p
    return None


NETZ2 = latest(P_VORSTUFEN, 'BORS_Netz_V2_*.gpkg', 10000, 'netz_v2')
V5 = latest(P_VORSTUFEN, 'BORS_Netz_V5_*.gpkg', 10000, 'netz_v5')
if NETZ2 is None or V5 is None:
    raise FileNotFoundError('Netz V2 oder Netz V5 fehlt.')
SCAN = P_VORSTUFEN / 'breiten_v5_{}.gpkg'.format(NETZ2.stem)
PARK = P_VORSTUFEN / 'parkierung_v5_{}.gpkg'.format(NETZ2.stem)
BAU = latest(P_BAUSTELLEN, 'baustellen_*.gpkg')
NM = latest(P_AKTUELL, 'BORS_Netzmaster_V9_*.gpkg', 10000, 'netz_v5')
if NM is None:
    raise FileNotFoundError('Kein Netzmaster V9 - zuerst 25_Breite_V9.py und 26_Netzmaster_V9.py ausfuehren.')
BR9 = next((p for p in sorted(P_AKTUELL.glob('BORS_Breite_V9_*.gpkg'), reverse=True) if not p.stem.endswith('_profile')), None)
PROF9 = BR9.with_name(BR9.stem + '_profile.gpkg') if BR9 and BR9.with_name(BR9.stem + '_profile.gpkg').is_file() else BR9
ABB = latest(P_AKTUELL, 'BORS_Abbiegen_V8_*.gpkg')

if True:
    # V8-Farben (P1-6): kein Gruen fuer "kein Hinweis" - das ist KEINE Durchfahrtsfreigabe.
    KAT = {'KEIN_HINWEIS': ('#5b84b1', 'kein Hinweis (nicht freigegeben)'),
           'VERDACHT_GRENZFALL': ('#f28e2b', 'Verdacht / Grenzfall'),
           'BESCHRAENKUNG_BESTAETIGT': ('#d62728', 'bestätigte Beschränkung'),
           'UNGEKLAERT': ('#b8b8b8', 'ungeklärt')}
    PROFIL = {'A': 'NEF', 'B': 'RTW', 'C': 'Feuerwehr mittel', 'D': 'Feuerwehr gross'}
    prj = QgsProject()
    prj.setCrs(QgsCoordinateReferenceSystem('EPSG:2056'))
    prj.setTitle('BORS Bern - fahrzeugabhaengiges Routing (Prototyp, keine Einsatzfreigabe)')
    root = prj.layerTreeRoot()
    n_add = []

    def add(group, uri, name, visible=True, subset=None, renderer=None, symbol=None):
        lyr = QgsVectorLayer(uri, name, 'ogr')
        if not lyr.isValid():
            print('  uebersprungen (nicht lesbar):', name)
            return None
        if subset:
            lyr.setSubsetString(subset)
        if renderer is not None:
            lyr.setRenderer(renderer)
        elif symbol is not None:
            lyr.renderer().setSymbol(symbol)
        prj.addMapLayer(lyr, False)
        node = group.addLayer(lyr)
        node.setItemVisibilityChecked(visible)
        node.setExpanded(False)
        n_add.append(name)
        return lyr

    def kat(field, width='0.6'):
        return QgsCategorizedSymbolRenderer(field, [
            QgsRendererCategory(k, QgsLineSymbol.createSimple({'line_color': c, 'line_width': width}), lab)
            for k, (c, lab) in KAT.items()])

    v5 = '{}|layername=netz_v5'.format(NM)
    root.addGroup('00 ROUTE (aktuell)')
    g1 = root.addGroup('01 ROUTING')
    g2 = root.addGroup('02 FAHRZEUGKARTE')
    g3 = root.addGroup('03 BELEGE')
    g4 = root.addGroup('04 GEBIET')
    g9 = root.addGroup('99 SYSTEM (nicht loeschen)')
    if BAU:
        add(g1, '{}|layername=segmente'.format(BAU), 'BORS Baustellen Segmente',
            symbol=QgsLineSymbol.createSimple({'line_color': '#c51b7d', 'line_width': '1.6', 'line_style': 'dash'}))
    def stat9(field, werte, width='0.7'):
        return QgsCategorizedSymbolRenderer(field, [QgsRendererCategory(k, QgsLineSymbol.createSimple({'line_color': c, 'line_width': width}), lab)
                                                    for k, c, lab in werte])
    ROUT = [('VALIDIERT', '#1a9850', 'validiert (Breite nachgewiesen, keine Hinweise)'), ('UNVALIDIERT', '#e6a700', 'unvalidiert (nicht entscheidbar)'),
            ('GESPERRT', '#d62728', 'gesperrt (nachweislich zu eng / Beschränkung)')]
    BREITE = [('AUSREICHEND', '#1a9850', 'Breite ausreichend nachgewiesen'), ('NICHT_ENTSCHEIDBAR', '#e6a700', 'nicht eindeutig entscheidbar'),
              ('UNZUREICHEND', '#d62728', 'Breite nachweislich zu klein')]
    BELEG = [('GEOMETRISCH', '#01665e', 'geometrisch belegt (AV-Messung)'), ('ABGELEITET', '#5ab4ac', 'aus zuverlässigen Angaben abgeleitet'),
             ('GESCHAETZT', '#dfc27d', 'nur geschätzt'), ('NICHT_UEBERPRUEFBAR', '#bdbdbd', 'nicht ausreichend überprüfbar'),
             ('FELD', '#2166ac', 'Befund vor Ort gemessen'), ('ORTHOFOTO', '#67a9cf', 'Befund am Orthofoto gemessen'),
             ('FACHSTELLE', '#762a83', 'Befund Fachstelle')]
    for code in 'DCBA':
        add(g2, v5, 'Routing {} · {}'.format(code, PROFIL[code]), visible=(code == 'D'), subset='"ist_routingtyp" = 1',
            renderer=stat9(code.lower() + '_v9_status', ROUT))
    for code in 'DCBA':
        add(g2, v5, 'Breite {} · {} (fachlich)'.format(code, PROFIL[code]), visible=False, subset='"ist_routingtyp" = 1',
            renderer=stat9(code.lower() + '_breite_v9', BREITE))
    g2.setIsMutuallyExclusive(True)
    gb = root.insertGroup(3, '02b BREITE V9 (Nachweis)')
    add(gb, v5, 'Nachweisqualität Breite D', False, '"ist_routingtyp" = 1', renderer=stat9('d_breite_v9_beleg', BELEG))
    if BR9:
        def pkt(field, werte, size='2.4'):
            return QgsCategorizedSymbolRenderer(field, [QgsRendererCategory(k, QgsMarkerSymbol.createSimple(
                {'name': 'circle', 'color': c, 'size': size, 'outline_color': '#ffffff', 'outline_width': '0.2'}), lab) for k, c, lab in werte])
        add(gb, '{}|layername=engstellen_v9'.format(BR9), 'Engstellen D (massgebendes Querprofil)', True,
            '"d_breite" != \'AUSREICHEND\'', renderer=pkt('d_breite', BREITE))
        add(gb, '{}|layername=profile_v9'.format(PROF9), 'Querprofile (nicht nachgewiesene Abschnitte)', False,
            renderer=pkt('status', [('OK', '#4d4d4d', 'gemessen'), ('VERSETZT', '#984ea3', 'Achse versetzt'),
                                    ('SUCHGRENZE', '#80b1d3', 'sehr breit (Suchgrenze)'), ('AUSSERHALB', '#e41a1c', 'Achse ausserhalb AV-Fahrbahn'),
                                    ('PN', '#ff7f00', 'AV-Qualitaet PN'), ('BEFESTIGT', '#a6761d', 'auf übriger befestigter Fläche')], '1.2'))
    sub = '"ist_routingtyp" = 1'
    def kat2(field, werte, width='0.7'):
        return QgsCategorizedSymbolRenderer(field, [QgsRendererCategory(k, QgsLineSymbol.createSimple({'line_color': c, 'line_width': width}), k)
                                                    for k, c in werte])
    add(g3, v5, 'Belegstufe D (Breite/Höhe/Gewicht)', False, sub, kat2('d_stufe', [('BELEGT', '#542788'), ('ABGELEITET', '#998ec3'),
                                                                                     ('ANNAHME', '#f1a340'), ('FEHLT', '#d9d9d9')]))
    add(g3, v5, 'Breitenstatus (Messung)', False, sub, kat2('breite_status', [('NUMERISCH_GEMESSEN', '#01665e'), ('MINDESTENS_6M_NACHGEWIESEN', '#5ab4ac'),
                                                                                ('DATENLUECKE', '#dfc27d'), ('MESSUNG_UNGUELTIG', '#8c510a'),
                                                                                ('NICHT_GEMESSEN', '#d9d9d9')]))
    add(g3, v5, 'Breite V8: Messstatus', False, sub, kat2('v8_b_status', [('GEMESSEN', '#01665e'), ('TEILGEMESSEN', '#80cdc1'),
                                                                           ('UNTERGRENZE', '#c7eae5'), ('UNGEKLAERT', '#d9d9d9')]))
    if ABB:
        def kat3(field):
            werte = [('UNMOEGLICH', '#d62728', 'Abbiegen unmöglich (Schleppkurve)'), ('NUR_MIT_NEBENFLAECHE', '#f28e2b', 'nur über Nebenfläche'),
                     ('ENG', '#fdd835', 'eng (ohne Reserve)'), ('SPITZKEHRE', '#7b3294', 'Spitzkehre > 120°'),
                     ('NICHT_BELASTBAR', '#9e9e9e', 'nicht belastbar (schon PW scheitert: Datenluecke)')]
            return QgsCategorizedSymbolRenderer(field, [QgsRendererCategory(k, QgsMarkerSymbol.createSimple(
                {'name': 'circle', 'color': c, 'size': '2.2', 'outline_color': '#ffffff', 'outline_width': '0.2'}), t) for k, c, t in werte])
        for fz_, nm_ in (('GTLF16', 'G-TLF 16 (26 t, 10 m)'), ('ADL', 'Autodrehleiter'), ('TLF14', 'TLF 14'), ('RTW', 'RTW')):
            add(g3, '{}|layername=abbiegen_v8'.format(ABB), 'Abbiegen/Kurven: {}'.format(nm_), fz_ == 'GTLF16',
                '"s_{0}" IN (\'UNMOEGLICH\', \'NUR_MIT_NEBENFLAECHE\', \'ENG\', \'SPITZKEHRE\', \'NICHT_BELASTBAR\')'.format(fz_), renderer=kat3('s_' + fz_))
    add(g3, v5, 'Breite (D)', False, sub, kat('d_breite_kat'))
    add(g3, v5, 'Höhe (D)', False, sub, kat('d_hoehe_kat'))
    add(g3, v5, 'Poller / Tore (D)', False, sub, kat('d_hindernis_kat', '1.2'))
    add(g3, v5, 'Enge Kurven (D)', False, sub, kat('d_kurve_kat', '1.2'))
    add(g3, v5, 'Steigung > 15 % (D)', False, sub, kat('d_steigung_kat', '1.2'))
    if SCAN.is_file():
        add(g3, '{}|layername=engstellen_querprofile'.format(SCAN), 'Messung: Querprofile netto < 3.50 m', False,
            '"breite_netto_m" < 3.5', symbol=QgsLineSymbol.createSimple({'line_color': '#d62728', 'line_width': '0.4'}))
    if PARK.is_file():
        add(g3, '{}|layername=parkierung'.format(PARK), 'Parkfelder (von der Breite abgezogen)', False,
            symbol=QgsFillSymbol.createSimple({'color': '30,90,200,90', 'outline_color': '#1e5ac8', 'outline_width': '0.1'}))
    bk = P_STADT / 'baumkataster.gpkg'
    if bk.is_file():
        add(g3, '{}|layername=Geoportal_Baumkataster:Baumkataster'.format(bk), 'Bäume Stadt Bern', False,
            symbol=QgsMarkerSymbol.createSimple({'name': 'circle', 'color': '#2e7d32', 'size': '1.2', 'outline_style': 'no'}))
    ks = P_KSVB / 'KSVB_Kanton_Bern.gpkg'
    if ks.is_file():
        add(g3, '{}|layername=ksvb_ksvbs'.format(ks), 'KSVB amtliche Beschränkungen (Strecken)', False,
            symbol=QgsLineSymbol.createSimple({'line_color': '#6a3d9a', 'line_width': '1.4'}))
        add(g3, '{}|layername=ksvb_ksvbo'.format(ks), 'KSVB amtliche Beschränkungen (Punkte)', False,
            symbol=QgsMarkerSymbol.createSimple({'name': 'square', 'color': '#6a3d9a', 'size': '2.4'}))
    add(g3, '{}|layername=ueberbauungen'.format(V5), 'Brücken/Gebäude über der Strasse', False,
        symbol=QgsMarkerSymbol.createSimple({'name': 'triangle', 'color': '#6a3d9a', 'size': '2.4'}))
    add(g3, '{}|layername=osm_hindernispunkte'.format(NETZ2), 'OSM Poller / Schranken / Tore', False, '"auf_routingnetz" = 1',
        symbol=QgsMarkerSymbol.createSimple({'name': 'cross2', 'color': '#000000', 'size': '2'}))
    if BAU:
        add(g3, '{}|layername=meldungen'.format(BAU), 'Baustellen-Meldungen ASTRA', False,
            symbol=QgsLineSymbol.createSimple({'line_color': '#7a0177', 'line_width': '1.0'}))
    add(g4, '{}|layername=aoi_gemeinden'.format(NETZ2), 'Zielgebiet (11 Gemeinden)',
        symbol=QgsFillSymbol.createSimple({'color': '0,0,0,0', 'outline_color': '#1f4e9c', 'outline_width': '0.6'}))
    add(g4, '{}|layername=aoi_puffer'.format(NETZ2), 'Routing-Puffer 2 km', False,
        symbol=QgsFillSymbol.createSimple({'color': '0,0,0,0', 'outline_color': '#1f4e9c', 'outline_style': 'dash'}))
    add(g9, v5, 'BORS Netz V7 (Routing)', False,
        symbol=QgsLineSymbol.createSimple({'line_color': '#555555', 'line_width': '0.2'}))
    for name, url, vis in (
            ('Hintergrund: swisstopo Landeskarte grau',
             'https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-grau/default/current/3857/%7Bz%7D/%7Bx%7D/%7By%7D.jpeg', True),
            ('Hintergrund: OpenStreetMap', 'https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png', False)):
        r = QgsRasterLayer('type=xyz&url={}&zmax=19&zmin=0'.format(url), name, 'wms')
        if r.isValid():
            prj.addMapLayer(r, False)
            root.addLayer(r).setItemVisibilityChecked(vis)
    for g in (g3, g4, g9):
        g.setExpanded(False)
    try:
        prj.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(
            QgsRectangle(2594000, 1193500, 2607500, 1206500), QgsCoordinateReferenceSystem('EPSG:2056')))
    except Exception:
        pass
    P_PROJEKTE.mkdir(parents=True, exist_ok=True)
    out = P_PROJEKTE / 'BORS_Routing_Bern_V9_{}.qgz'.format(datetime.now().strftime('%Y%m%d_%H%M'))   # immer neue Datei
    if not prj.write(str(out)):
        raise RuntimeError('Projekt konnte nicht gespeichert werden: ' + str(out))
    print('BORS PROJEKT V9: {} Ebenen -> {} (Netzmaster {})'.format(len(n_add), out, NM.name))
    print('BORS PROJEKT V9: Jetzt "Projekt > Oeffnen" -> {} und danach 7_Router_V9_2e_BORS.py starten.'.format(out.name))
