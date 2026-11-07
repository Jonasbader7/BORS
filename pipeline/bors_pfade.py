# -*- coding: utf-8 -*-
r"""BORS - zentrale Pfade der Projektablage OneDrive\Desktop\BORS (ab 29.10.2026).
Wird von den *_BORS.py-Skripten per exec() geladen. Andere Ablage: vor dem Start in der QGIS-Konsole
    BORS_ROOT = Path(r'D:\...\BORS')
setzen. Die alten Skripte (Downloads\BORS_AKTUELL, Documents\BORS_*) bleiben unveraendert.
"""
from pathlib import Path

BORS_ROOT = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
if not (BORS_ROOT / '01_Skripte' / 'Aktuell').is_dir():
    raise FileNotFoundError('BORS-Ablage nicht gefunden: {} (BORS_ROOT setzen)'.format(BORS_ROOT))

P_SKRIPTE = BORS_ROOT / '01_Skripte' / 'Aktuell'                 # Skripte, Hilfsmodule, Fahrzeuge/Wachen-CSV
P_ROH = BORS_ROOT / '02_Daten' / '1_Rohdaten'
P_AKTUELL = BORS_ROOT / '02_Daten' / '2_Aktuell_V9'              # Netzmaster V8 (Basis) + V9, Abbiegen V8, Breite V9, AV-Export
P_VORSTUFEN = P_AKTUELL / 'Vorstufen'                             # Netz V2, Netz V5, Breiten-/Parkierungsscan V5
P_BAUSTELLEN = P_ROH / 'Baustellen_Verkehrsmeldungen'             # baustellen_*.gpkg (inkl. Stadt-Poller)
P_STADT = P_ROH / 'Stadt_Bern'                                    # Baumkataster, Parkplaetze, Poller
P_KSVB = P_ROH / 'Kanton_Bern' / 'KSVB'
P_HINDKAT = P_ROH / 'Kanton_Bern'                                 # HINDKAT_*.gpkg (Hinderniskartei SVSA)
P_PROJEKTE = BORS_ROOT / '03_QGIS_Projekte' / 'Aktuell'           # neue .qgz aus 6_Projekt
P_ROUTEN = BORS_ROOT / '02_Daten' / '5_Routen_Ausgaben'           # Routen-GeoPackages/CSV des Routers
P_TESTS = BORS_ROOT / '05_Berichte' / 'QA_Tests' / 'tests'        # Protokolle 27_QGIS_Test
