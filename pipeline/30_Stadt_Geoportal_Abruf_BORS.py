# -*- coding: utf-8 -*-
r"""BORS 30 (5.11.2026): offene Ebenen des Geoportals der Stadt Bern (map.bern.ch, ArcGIS REST) als GeoJSON sichern.
Laeuft in normalem Python (kein QGIS), z. B.:
    python 01_Skripte/Aktuell/30_Stadt_Geoportal_Abruf_BORS.py
oder in der QGIS-Python-Konsole wie die anderen Skripte (exec).

Was es tut:
- Holt die unten in EBENEN aufgefuehrten Ebenen vollstaendig (Seiten zu 1000 Objekten), Koordinaten in EPSG:2056.
- Uebernimmt NUR die aufgefuehrten Felder. Personendaten (Bauherrschaft, Bauleitung, Telefon, Bearbeiter
  "Erstellt_von"/"Editiert_von") werden nie abgefragt (Regel: keine Personendaten aus den Baustellendaten).
- Schreibt in einen NEUEN Ordner 02_Daten/1_Rohdaten/Stadt_Bern/Geoportal_<JJJJMMTT_HHMM> (bricht ab, wenn er existiert):
  <ebene>.geojson je Ebene, quellen.csv (URL, Felder, Anzahl, Abrufzeit) und Abruf_Protokoll.txt.
- Prueft je Ebene, dass die Anzahl der Objekte der Zaehlung des Dienstes entspricht.
Nicht enthalten: das Signalinventar (Dienst WKDispo_Signalnachfuehrung) - dort ist die Abfrage gesperrt; es wird nicht
ueber die Kartenansicht ausgelesen, sondern beim Tiefbau angefragt.
Quelle und Nutzung: "Geodaten Stadt Bern" (Copyright-Vermerk der Dienste), map.bern.ch.
"""
import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

_BR = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
exec(compile((_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py').read_text(encoding='utf-8'), str(_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py'), 'exec'))

BASIS = 'https://map.bern.ch/arcgis/rest/services/'
UA = 'BORS Studienprojekt BFH (Modul BCS HS26)'
SEITE = 1000

# name: (Dienstpfad/Ebene, Felder, Zweck)
EBENEN = {
    'polleranlagen': ('Geoportal/Polleranlagen_Schranken/MapServer/0', 'Name,Typ,Typ_beschrieb,Bemerkung,Ausnahmen_vom_Fahrverbot,Letzte_Aenderung', 'gesteuerte Poller/Schranken'),
    'baustellen': ('Geoportal/Baustellen_2/MapServer/2', 'Id,Locality,Project,Startdate,Enddate,Displaynumber,Year,Number,Statustxt,Status,Bauphase_name,Bauphase_key,Discriminator,Typecharacter,Lastmodification_timestamp', 'Baustellen (ohne Personendaten)'),
    'installationsplaetze': ('Geoportal/Baustellen_2/MapServer/1', 'Id,Produktid,Locality,Project,Startdate,Enddate,Displaynumber,Year,Number,Statustxt,Status,Discriminator,Typecharacter', 'Installationsplaetze (ohne Personendaten)'),
    'steigungen': ('Geoportal/Strassensteigungen/MapServer/0', 'Sas_id,Sas_objekt,Strassenname,Von,Bis,Steig,Steigung', 'Steigung je Strassenabschnitt'),
    'hoechstgeschwindigkeit': ('Geoportal/Signalisierte_Hoechstgeschwindigkeit/MapServer/0', 'Sas_id,Sas_objekt,Strassenname,Von,Bis,V_sig,V_afu', 'signalisierte Hoechstgeschwindigkeit'),
    'strassentypen': ('Geoportal/Strassentypen/MapServer/0', 'Sas_id,Sas_objekt,Strassenname,Von,Bis,Strassentyp,Beschreibung', 'Strassentyp'),
    'strassenhierarchie': ('Geoportal/Strassenhierarchie/MapServer/0', 'Sas_id,Sas_objekt,Strassenname,Von,Bis,Strassenhierarchie', 'Strassenhierarchie'),
    'strassenbelaege': ('Geoportal/Strassenbelaege/MapServer/0', 'SAS_ID,Strassenname,Belag', 'Strassenbelag'),
    'strassennetz': ('Geoportal/Strassennetz/MapServer/0', 'Sas_id,Sas_objekt,Strassenname,K_nummer,Von,Bis', 'Strassennetz der Stadt'),
    'oev_linien': ('Geoportal/OeV_Linien/MapServer/0', 'Linienname,Nummer_linie,Haltestelle_start,Haltestelle_ende,Rubrik,Verkehrsmittel_typ,Betreiber', 'OeV-Linien (Bus, Trolleybus, Tram, Bahn)'),
    'freihalterouten_oev': ('WMS_TAB/MapServer/1', 'VERKEHRSMITTEL,BETREIBER,LINIE_NR', 'Freihalterouten OeV (Tiefbau)'),
}
PARKFELD_EBENEN = range(11, 20)   # Parkplaetze_oeffentlich: Flaechen nach Art (11-19)
PARKFELD_FELDER = 'Parkplatz_nummer,Parkplatz_name,Gruppe,Gruppe_beschrieb,Subgruppe,Subgruppe_beschrieb,Art,Art_beschrieb,Anzahl_parkfelder,Ueberdeckung_beschrieb,Status,Status_beschrieb,Lage_beschrieb,Letzte_Aenderung'
VERBOTEN = ('bauherr', 'bauleitung', 'telefon', 'vorname', 'nachname', '_von', '_user')

STEMPEL = datetime.now().strftime('%Y%m%d_%H%M')
ZIEL = Path(globals().get('BORS_GEOPORTAL_ZIEL', P_STADT / ('Geoportal_' + STEMPEL)))
if ZIEL.exists():
    raise FileExistsError('Zielordner existiert schon (nichts ueberschreiben): {}'.format(ZIEL))
ZIEL.mkdir(parents=True)
PROT = []


def log(t):
    print(t)
    PROT.append(t)


def hole(pfad, params):
    url = BASIS + pfad + '/query?' + urllib.parse.urlencode(params)
    for versuch in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:  # Netzfehler: kurz warten, zweimal wiederholen
            if versuch == 2:
                raise
            time.sleep(3)


def ebene(name, pfad, felder, zweck):
    for f in felder.split(','):
        if any(v in f.lower() for v in VERBOTEN):
            raise ValueError('Feld {} in {} ist als Personendaten gesperrt'.format(f, name))
    # nur Felder abfragen, die die Ebene wirklich hat (die Parkfeld-Ebenen unterscheiden sich)
    url = BASIS + pfad + '?f=json'
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
        vorhanden = {f['name'].lower(): f['name'] for f in json.loads(r.read().decode('utf-8')).get('fields', [])}
    fehlend = [f for f in felder.split(',') if f.lower() not in vorhanden]
    felder = ','.join(vorhanden[f.lower()] for f in felder.split(',') if f.lower() in vorhanden)
    if fehlend:
        log('  ({}: Felder nicht vorhanden: {})'.format(name, ', '.join(fehlend)))
    soll = hole(pfad, {'where': '1=1', 'returnCountOnly': 'true', 'f': 'json'}).get('count')
    feats, off, seite = [], 0, SEITE
    while True:
        j = hole(pfad, {'where': '1=1', 'outFields': felder, 'outSR': 2056, 'returnGeometry': 'true', 'orderByFields': 'OBJECTID',
                        'resultOffset': off, 'resultRecordCount': seite, 'f': 'geojson'})
        if 'error' in j:
            if seite > 50:   # manche Ebenen scheitern an grossen Seiten: kleiner wiederholen
                seite = max(50, seite // 4)
                continue
            log('  {:<24} FEHLER: {}'.format(name, j['error']))
            return dict(ebene=name, url=BASIS + pfad, felder=felder, anzahl=0, anzahl_dienst=None, pruefung='FEHLER',
                        abruf=datetime.now().isoformat(timespec='seconds'), zweck=zweck)
        feats += j.get('features', [])
        if not j.get('exceededTransferLimit') or not j.get('features'):
            break
        off += len(j.get('features', []))
    for ft in feats:   # nur die verlangten Felder behalten (Schutz, falls der Dienst mehr liefert)
        erlaubt = set(felder.split(','))
        ft['properties'] = {k: v for k, v in (ft.get('properties') or {}).items() if k in erlaubt}
    fc = {'type': 'FeatureCollection', 'name': name, 'crs': {'type': 'name', 'properties': {'name': 'EPSG:2056'}},
          'bors_quelle': {'url': BASIS + pfad, 'abruf': datetime.now().isoformat(timespec='seconds'), 'copyright': 'Geodaten Stadt Bern', 'zweck': zweck}, 'features': feats}
    (ZIEL / (name + '.geojson')).write_text(json.dumps(fc, ensure_ascii=False), encoding='utf-8')
    ok = soll is None or soll == len(feats)
    log('  {:<24} {:>6} Objekte (Dienst: {}) {}'.format(name, len(feats), soll, 'ok' if ok else 'ABWEICHUNG'))
    return dict(ebene=name, url=BASIS + pfad, felder=felder, anzahl=len(feats), anzahl_dienst=soll, pruefung='ok' if ok else 'ABWEICHUNG',
                abruf=datetime.now().isoformat(timespec='seconds'), zweck=zweck)


log('BORS 30: Abruf Geoportal Stadt Bern -> {}'.format(ZIEL))
zeilen = [ebene(n, *v) for n, v in EBENEN.items()]
for lid in PARKFELD_EBENEN:
    zeilen.append(ebene('parkfelder_{}'.format(lid), 'Geoportal/Parkplaetze_oeffentlich/MapServer/{}'.format(lid), PARKFELD_FELDER, 'Parkfeld-Flaechen (Ebene {})'.format(lid)))
with open(ZIEL / 'quellen.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=list(zeilen[0].keys()), delimiter=';')
    w.writeheader()
    w.writerows(zeilen)
fehl = [z['ebene'] for z in zeilen if z['pruefung'] != 'ok']
log('Fertig: {} Ebenen, {} Objekte. Pruefung: {}'.format(len(zeilen), sum(z['anzahl'] for z in zeilen), 'ok' if not fehl else 'ABWEICHUNG bei ' + ', '.join(fehl)))
(ZIEL / 'Abruf_Protokoll.txt').write_text('\n'.join(PROT) + '\n', encoding='utf-8')
