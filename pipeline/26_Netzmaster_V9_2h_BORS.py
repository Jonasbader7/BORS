# -*- coding: utf-8 -*-
"""BORS 26 (V9.2h_BORS, 10.11.2026): wie V9.2g_BORS, dazu Profilpruefung Breite (Modul bors_breite_v9_3.py):
  Stammt die Breitendatei aus 25_Breite_V9_3_BORS (Felder <p>_reserve_profil_m ...), wird ein AUSREICHEND nur behalten, wenn
  (1) an jedem Profil die untere Schranke den OERTLICHEN Bedarf erfuellt (Spiegel nur dort ueber Trottoir/Insel, wo das
  Profil daran grenzt; V9.2g nahm den Rand des engsten Profils fuer den ganzen Abschnitt), (2) kein einzelnes Profil
  darunter liegt (kurze Engstelle -> NICHT_ENTSCHEIDBAR, nie GESPERRT) und (3) der freie Raum nicht hinter einem
  Hindernis die Seite wechselt. Die Pruefung stuft nur herab. Mit einer alten Breitendatei (V9.1) ist das Ergebnis
  gleich wie V9.2g. Bedarfsparameter (Reserve je Klasse, Spiegel) kommen aus dem Modul; weicht die Breitendatei ab: Abbruch.
STARTEN (QGIS-Python-Konsole, Ablage BORS; laeuft auch in normalem Python, nur sqlite3 + numpy):
    from pathlib import Path
    p = Path.home() / 'OneDrive' / 'Desktop' / 'BORS' / '01_Skripte' / 'Aktuell' / '26_Netzmaster_V9_2h_BORS.py'
    exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'))
V9.2g_BORS (5.11.2026): wie V9.2f_BORS, zusaetzlich Angaben Tiefbau Stadt Bern (Antwort 4.11.2026):
  - Signale Fachstelle (02_Daten/2_Aktuell_V9/BORS_Signale_Fachstelle.csv: seg_id;name;hoehe_m;gewicht_t;quelle;zuordnung;
    datum;geprueft_von): wirken wie signalisierte Werte der Hinderniskartei (Fahrzeug schwerer/hoeher -> GESPERRT, Hoehe
    knapp -> UNVALIDIERT). Inhalt: Plan Hoechstgewicht der Stadt (10/16/28/34 t, Stand 04.05.2026, georeferenziert und den
    Abschnitten zugeordnet, Bericht 05_Berichte/Abgleich_Tiefbauamt_20261105) und Lehnenviadukt 3.2 m. Laut Tiefbau gelten
    Gewichtsgrenzen fuer alle, auch fuer Einsatzfahrzeuge (statisch begruendet).
  - Hoehenregel (VRV, bestaetigt vom Tiefbau): Wo keine lichte Hoehe signalisiert ist, betraegt sie mindestens 4.00 m.
    "Ueberbauung ohne Hoehenangabe" wird deshalb auf oeffentlichen Strassen (OSM highway nicht service, access nicht
    private/no) nicht mehr als ungeklaert gewertet, sondern als Hinweis "abgeleitet >= 4.00 m". Auf service-Wegen
    (Hofdurchfahrten, Garagen, meist privat) bleibt sie ungeklaert. Hat der Abschnitt eine signalisierte Hoehe
    (Hinderniskartei oder Fachstelle), entscheidet dieser Wert statt "ungeklaert".
  - Kirchenfeldbruecke: Hinweis auf Nutzungsvereinbarung fuer Notfalldienste (Inhalt offen, Sperre bleibt bis SRB bestaetigt).
  Ohne BORS_Signale_Fachstelle.csv und mit HOEHENREGEL_4M = False ist das Ergebnis gleich wie V9.2f.
BORS 26 (V9.2f_BORS, 1.11.2026): wie V9.2d_BORS, zusaetzlich geprueft Befunde aus 02_Daten/2_Aktuell_V9/BORS_Befunde.csv.
Ohne Datei oder mit leerer Datei ist das Ergebnis Feld fuer Feld gleich wie V9.2d (neue Spalten <p>_v9_befund leer).
BORS_Befunde.csv (Semikolon, UTF-8), eine Zeile je Abschnitt und Kriterium:
  seg_id      z.B. w296489152
  klassen     Fahrzeugklassen, fuer die der Befund gilt, z.B. ABCD oder CD
  kriterium   BREITE | HOEHE | GEWICHT | HINDERNIS
  befund      PASSIERBAR | NICHT_PASSIERBAR
  messwert    BREITE: engste freie Breite Randstein-Randstein in m; HOEHE: lichte Hoehe in m (beide Pflicht bei PASSIERBAR);
              GEWICHT: belegte Tragfaehigkeit in t (freiwillig); HINDERNIS: leer
  methode     FELD (vor Ort gemessen) | ORTHOFOTO (am Bildschirm gemessen) | FACHSTELLE (schriftliche Auskunft)
  beleg       Foto, Dokument oder Quelle;  geprueft_von;  datum (JJJJ-MM-TT);  bemerkung (frei)
Regeln:
  - PASSIERBAR hebt nur die Gruende "ungeklaert/nicht entscheidbar" dieses Kriteriums auf. VALIDIERT wird ein Abschnitt
    erst, wenn alle Gruende aufgehoben sind. Eine Sperre (GESPERRT) hebt ein Befund nie auf, der Widerspruch steht im Protokoll.
  - BREITE: Messwert >= Bedarf der Klasse (wie Breitenentscheid V9.2). Bei ORTHOFOTO zusaetzlich + ORTHO_MARGE_M (Annahme
    0.50 m: Lage der beiden Raender je ca. +-0.25 m auf SWISSIMAGE 10 cm). Sonst wird der Befund fuer diese Klasse abgelehnt.
  - HOEHE: Messwert >= Fahrzeughoehe + HOEHE_RESERVE (0.10 m). GEWICHT mit Messwert: Messwert >= Fahrzeuggewicht.
  - NICHT_PASSIERBAR sperrt den Abschnitt fuer die genannten Klassen.
  - Ungueltige Zeilen (Pflichtfeld leer, unbekannter Wert, unbekannte seg_id) werden nicht angewendet und im Bericht gemeldet.
  - Herkunft bleibt sichtbar: <p>_breite_v9_beleg = FELD | ORTHOFOTO | FACHSTELLE, Text in <p>_v9_grund und <p>_v9_befund.
Ausgabe zusaetzlich: <Netzmaster>_Befunde_Protokoll.csv (je Befund und Klasse: uebernommen / abgelehnt / ohne Wirkung).
BORS 26 (V9.2d_BORS, 29.10.2026): Logik identisch mit 26_Netzmaster_V9_2d.py, nur die Pfade kommen aus der Ablage BORS
  (Quelle/Ausgabe 02_Daten/2_Aktuell_V9, Hinderniskartei 02_Daten/1_Rohdaten/Kanton_Bern, Hilfsmodule 01_Skripte/Aktuell).
BORS 26 (V9.2d): zusaetzlich zu V9.2b
  - Amtliche Hinderniskartei des Kantons Bern (SVSA, Datei Documents/BORS_V9/HINDKAT_*.gpkg): signalisierte Hoehe (hoehesig)
    und signalisiertes Gewicht (tonnsig) an Bruecken/Unterfuehrungen. Zuordnung zum Abschnitt mit gleichem Strassennamen
    (<= 40 m), sonst Bruecke -> Brueckenabschnitt bzw. Unterfuehrung -> Nicht-Brueckenabschnitt (<= 15 m). Temporaere
    Eintraege nur innerhalb datumvon/datumbis. Zuordnungsliste: <Netzmaster>_HINDKAT_Zuordnung.csv.
    Fahrzeug schwerer bzw. hoeher als Signal -> GESPERRT; Hoehe knapp (< 0.10 m Reserve, wie V8) -> UNVALIDIERT.
  - OSM maxheight=below_default (niedriger als Standard, Wert unbekannt): fuer Fahrzeuge ueber 2.0 m Hoehe UNVALIDIERT
    (wie Ueberbauung ohne Hoehenangabe in V8), ausser die Hinderniskartei nennt eine signalisierte Hoehe.
BORS 26 (V9.2b): Fehlerbehebung - Spiegeltext nur wenn entscheidend; Hauszufahrt-Ableitung nicht, wenn gemessen schmaler als Karosserie.
BORS 26 (V9.2): zusaetzlich zu V9.1 (Entscheid neu aus den gespeicherten Schranken der Breitenmessung):
  - Spiegel ueber Trottoir/Verkehrsinsel erlaubt (Entscheid Projektleitung 28.10.2026): je Seite mit Trottoir/Insel am
    massgebenden Querprofil darf der halbe Spiegelueberstand (Spiegel - Karosserie)/2 ueber den Rand ragen.
  - Reserve Profil A (Personenwagen) 0.15 m je Seite statt 0.25 m (Entscheid Projektleitung).
  - Messluecken unter Bruecken/in Tunneln: AV-Bauwerksbreite minus 3.0 m (Trottoir/Gelaender, Annahme) als abgeleitete Schranke.
  - Profil A: Hauszufahrt/Parkplatzgasse (OSM service=driveway/parking_aisle) gilt als fuer Personenwagen gebaut (abgeleitet).
BORS 26 (V9.1): Korrekturen gegenueber V9:
  - Gewicht: FKS-18-t ist eine Bemessungsgrundlage fuer ausgewiesene Feuerwehrzufahrten, KEIN Gewichtslimit. V9 hatte sie auf
    ALLE service-Wege angewendet (Modellfehler). Neu: Signal/KSVB -> Grenze; oeffentlich befahrbare Wege -> gesetzlich 40 t
    (abgeleitet, wie bei allen Strassen); private Zufahrten (access=private/no) und Wege ueber unterirdischen Bauten (AV)
    -> Tragfaehigkeit nicht belegt fuer > 18 t.
  - Steigung: keine Steigfaehigkeit im Fahrzeugdatensatz -> nur Hinweis, kein Validierungskriterium (Liste im Bericht).
V9: Netzmaster V9 = Netzmaster V8 + geometrische Breitenmessung V9 + getrennte Routingentscheidung A-D.

Je Profil A-D (Felder a_..., b_..., c_..., d_...):
  <p>_breite_v9        AUSREICHEND | NICHT_ENTSCHEIDBAR | UNZUREICHEND     (fachliches Ergebnis Breite)
  <p>_breite_v9_beleg  GEOMETRISCH | ABGELEITET | GESCHAETZT | NICHT_UEBERPRUEFBAR   (Qualitaet des Nachweises)
  <p>_breite_v9_grund  Begruendung mit Messwerten
  <p>_v9_status        VALIDIERT | UNVALIDIERT | GESPERRT            (Routingentscheidung, alle Kriterien)
  <p>_v9_grund         alle Gruende, die nicht "validiert" sind
Kriterien neben der Breite (aus V8, Tabelle bewertung_v8): Hoehe, Gewicht, Hindernis, Freigaben; Steigung neu mit
Plausibilitaetspruefung je Strassenklasse. "Kein Hinweis" bei Hoehe/Gewicht ist kein Nachweis im strengen Sinn,
sondern: keine Ueberbauung in AV/OSM bzw. gesetzliches Hoechstgewicht 40 t ohne abweichende Signalisation.
Schreibt eine NEUE Datei BORS_Netzmaster_V9_<zeit>.gpkg; die V8-Datei bleibt unveraendert.
"""
import csv
import shutil
import sqlite3
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
# BORS-Ablage: zentrale Pfade aus 01_Skripte/Aktuell/bors_pfade.py (BORS_ROOT ueberschreibbar)
_BR = Path(globals().get('BORS_ROOT', Path.home() / 'OneDrive' / 'Desktop' / 'BORS'))
exec(compile((_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py').read_text(encoding='utf-8'), str(_BR / '01_Skripte' / 'Aktuell' / 'bors_pfade.py'), 'exec'))

NMDIR = P_AKTUELL          # Netzmaster V8 (Quelle) und V9 (Ausgabe)
V9 = P_AKTUELL             # Breitenmessung V9
AKT = P_SKRIPTE
for _m in ('bors_geo.py', 'bors_bewertung_v8.py', 'bors_breite_v9_3.py'):
    exec(compile((AKT / _m).read_text(encoding='utf-8'), str(AKT / _m), 'exec'))
_FZ = lade_fahrzeuge(AKT / 'BORS_Fahrzeuge_V1.csv')
MASSE = {k: huelle(_FZ, k) for k in 'ABCD'}
RESERVE = RESERVE_KOERPER_KLASSE          # V9.2h: aus bors_breite_v9_3 (Werte wie V9.2g: A 0.15, B-D 0.25)
RES_SPIEGEL = RES_SPIEGEL_M               # 0.10
NIEDRIG = SPIEGEL_UEBER                   # Trottoir, Verkehrsinsel
PW_ZUFAHRT = {'driveway', 'parking_aisle'}
STAMP = datetime.now().strftime('%Y%m%d_%H%M')
T0 = time.time()
REP = []
STEIGUNG_PCT, STEIGUNG_T = 15.0, 7.5
STEIGUNG_PLAUSIBEL = {'motorway': 10.0, 'trunk': 12.0, 'primary': 15.0, 'secondary': 15.0, 'tertiary': 22.0}
NORMPROFIL = {'motorway', 'motorway_link', 'trunk', 'trunk_link'}
GEWICHT = {'A': 3.1, 'B': 5.5, 'C': 17.0, 'D': 28.4}
HK_GLEICHER_NAME_M, HK_ANDERER_NAME_M = 40.0, 15.0     # V9.2d: Zuordnung Hinderniskartei -> Abschnitt
ORTHO_MARGE_M = 0.50                                    # V9.2f: Zuschlag Breite bei Messung auf dem Orthofoto (Annahme)
BEFUND_KRIT = ('BREITE', 'HOEHE', 'GEWICHT', 'HINDERNIS')
BEFUND_ART = ('PASSIERBAR', 'NICHT_PASSIERBAR')
BEFUND_METHODE = ('FELD', 'ORTHOFOTO', 'FACHSTELLE')
HOEHENREGEL_4M = globals().get('BORS_HOEHENREGEL_4M', True)     # V9.2g: ohne Signal >= 4.00 m (oeffentliche Strassen)
HOEHE_OHNE_SIGNAL_M = 4.00
OEFFENTLICH_HW = {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link',
                  'tertiary', 'tertiary_link', 'unclassified', 'residential', 'living_street', 'road'}
HINWEIS_SEG = {'w312022667': 'Hinweis Kirchenfeldbruecke: laut Tiefbau Stadt Bern (4.11.2026) Nutzungsvereinbarung fuer Notfalldienste, '
                             'Inhalt offen (Rueckfrage SRB) - Sperre bleibt'}


def log(m):
    print('BORS V9 NETZ:', m); REP.append(str(m))


def neueste(ordner, muster):
    l = sorted(ordner.glob(muster), key=lambda p: p.stat().st_mtime)
    if not l:
        raise FileNotFoundError('{} fehlt in {}'.format(muster, ordner))
    return l[-1]


SRC = neueste(NMDIR, 'BORS_Netzmaster_V8_*.gpkg')
BR = sorted((p for p in V9.glob('BORS_Breite_V9_*.gpkg') if not p.stem.endswith('_profile')), key=lambda p: p.stat().st_mtime)[-1]
HKD = neueste(P_HINDKAT, 'HINDKAT_*.gpkg')
OUT = NMDIR / 'BORS_Netzmaster_V9_{}.gpkg'.format(STAMP)
BEF = P_AKTUELL / 'BORS_Befunde.csv'
log('Quelle {} + {} + {} -> {}'.format(SRC.name, BR.name, HKD.name, OUT.name))
shutil.copyfile(str(SRC), str(OUT))

b = sqlite3.connect('file:{}?mode=ro'.format(BR.as_posix()), uri=True)
bc = [r[1] for r in b.execute('pragma table_info(breite_v9)')]
BREITE = {r[bc.index('seg_id')]: dict(zip(bc, r)) for r in b.execute('select * from breite_v9')}
_bmeta = dict(b.execute('select schluessel, wert from bors_meta').fetchall())
b.close()
PROFILPRUEFUNG = 'a_reserve_profil_m' in bc                       # V9.2h: nur mit Breitendatei V9.3
if PROFILPRUEFUNG and _bmeta.get('bedarf_profil') != BEDARF_REGEL:
    raise RuntimeError('Breitendatei {} rechnet mit anderem Bedarf ({}) als bors_breite_v9_3 ({}) - 25_Breite neu rechnen'.format(
        BR.name, _bmeta.get('bedarf_profil'), BEDARF_REGEL))
if PROFILPRUEFUNG and 'Stichprobe' in (_bmeta.get('auswahl') or ''):
    raise RuntimeError('Breitendatei {} ist eine Stichprobe ({}) - nicht fuer den Netzmaster'.format(BR.name, _bmeta.get('auswahl')))
profil_wirkung = Counter()
log('Breitenmessung V9: {} Abschnitte'.format(len(BREITE)))

db = sqlite3.connect(str(OUT))
for fn, n in (('ST_IsEmpty', 1), ('ST_MinX', 1), ('ST_MaxX', 1), ('ST_MinY', 1), ('ST_MaxY', 1)):
    db.create_function(fn, n, (lambda g: 0) if fn == 'ST_IsEmpty' else (lambda g: 0.0), deterministic=True)

# V9.2d: Hinderniskartei (nur Eintraege mit signalisiertem Wert; temporaere nur im Gueltigkeitszeitraum)
heute = datetime.now().date().isoformat()
h = sqlite3.connect('file:{}?mode=ro'.format(HKD.as_posix()), uri=True)
HKP, hk_n = [], Counter()
for nr, art, typ, strn, hs, ts, dv, dbis, g in h.execute(
        'select hindnr, hindart, hindt_bez_de, strname, hoehesig, tonnsig, datumvon, datumbis, geometry from "geodb.hindkat_hindrnis_vw"'):
    hk_n['gesamt'] += 1
    if hs is None and ts is None:
        continue
    if (dv and str(dv)[:10] > heute) or (dbis and str(dbis)[:10] < heute):
        hk_n['temporaer ausserhalb Gueltigkeit'] += 1
        continue
    HKP.append(dict(nr=nr, art=art or '', typ=typ or '', strn=strn or '', h=hs, t=ts, p=punkt(g)))
h.close()
RAS, SEGL = Raster(100.0), {}
for sid, name, btl, g in db.execute('select seg_id, name, bruecke_tunnel_layer, geom from netz_v5 where ist_routingtyp = 1'):
    ls = linien(g)
    if not ls:
        continue
    xs = [p[0] for l in ls for p in l]; ys = [p[1] for l in ls for p in l]
    SEGL[sid] = (name or '', 'bridge' in (btl or ''), ls)
    RAS.add(sid, min(xs), min(ys), max(xs), max(ys))
HK = defaultdict(list)
zuo = []
for o in HKP:
    x, y = o['p']
    kand = []
    for sid in RAS.nahe(x - HK_GLEICHER_NAME_M, y - HK_GLEICHER_NAME_M, x + HK_GLEICHER_NAME_M, y + HK_GLEICHER_NAME_M):
        name, ist_bruecke, ls = SEGL[sid]
        d = min(projiziere(l, x, y)[0] for l in ls)
        kand.append((d, sid, name, ist_bruecke))
    gleich = sorted(k for k in kand if k[2] == o['strn'] and k[0] <= HK_GLEICHER_NAME_M)
    if gleich:
        wahl, regel = gleich[0], 'gleicher Strassenname'
    else:
        typ_ok = sorted(k for k in kand if k[0] <= HK_ANDERER_NAME_M and k[3] == (o['typ'] == 'Brücke'))
        wahl, regel = (typ_ok[0], 'naechster {}abschnitt'.format('Bruecken' if o['typ'] == 'Brücke' else 'Strassen')) if typ_ok else (None, 'nicht zugeordnet')
    if wahl:
        HK[wahl[1]].append(o)
        hk_n['zugeordnet'] += 1
    else:
        hk_n['nicht zugeordnet (kein Abschnitt in Reichweite)'] += 1
    zuo.append([o['nr'], o['art'], o['typ'], o['strn'], o['h'], o['t'], wahl[1] if wahl else '', wahl[2] if wahl else '',
                '{:.1f}'.format(wahl[0]) if wahl else '', regel])
log('Hinderniskartei {}: {}'.format(HKD.name, dict(hk_n)))

# V9.2g: Signale Fachstelle (Tiefbau Stadt Bern), wirken wie Hinderniskartei-Eintraege mit eigener Quelle
SIGF = P_AKTUELL / 'BORS_Signale_Fachstelle.csv'
sf_n = Counter()
if SIGF.exists():
    _sids = set(SEGL)
    with open(str(SIGF), encoding='utf-8-sig', newline='') as fh:
        for nr, z in enumerate(csv.DictReader(fh, delimiter=';'), 2):
            z = {k.strip().lower(): (v or '').strip() for k, v in z.items() if k}
            if not any(z.values()):
                continue
            try:
                hs = float(z['hoehe_m'].replace(',', '.')) if z.get('hoehe_m') else None
                ts = float(z['gewicht_t'].replace(',', '.')) if z.get('gewicht_t') else None
            except ValueError:
                log('  Signal Fachstelle Zeile {} NICHT ANGEWENDET: Wert keine Zahl'.format(nr)); sf_n['ungueltig'] += 1
                continue
            if z.get('seg_id') not in _sids or (hs is None and ts is None) or not z.get('quelle'):
                log('  Signal Fachstelle Zeile {} NICHT ANGEWENDET: seg_id unbekannt, kein Wert oder keine Quelle'.format(nr)); sf_n['ungueltig'] += 1
                continue
            HK[z['seg_id']].append(dict(nr='F{}'.format(nr), art='', typ='', strn=z.get('name', ''), h=hs, t=ts, p=None,
                                        quelle=z['quelle'][:70]))
            sf_n['hoehe' if hs is not None else 'gewicht'] += 1
log('Signale Fachstelle {}: {}'.format(SIGF.name if SIGF.exists() else '(keine Datei)', dict(sf_n)))
with open(str(NMDIR / (OUT.stem + '_HINDKAT_Zuordnung.csv')), 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh, delimiter=';')
    w.writerow(['hindnr', 'hindart', 'typ', 'strname', 'hoehesig_m', 'tonnsig_t', 'seg_id', 'name_abschnitt', 'abstand_m', 'regel'])
    w.writerows(zuo)

# V9.2f: gepruefte Befunde einlesen und auf Vollstaendigkeit pruefen
BEFUNDE = defaultdict(list)
bef_fehler = []
_alle_sid = {r[0] for r in db.execute('select seg_id from netz_v5 where ist_routingtyp = 1')}
if BEF.exists():
    with open(str(BEF), encoding='utf-8-sig', newline='') as fh:
        for nr, z in enumerate(csv.DictReader(fh, delimiter=';'), 2):
            z = {k.strip().lower(): (v or '').strip() for k, v in z.items() if k}
            if not any(z.values()):
                continue
            sid, kl, kr_, bf, mw, me = (z.get(k, '') for k in ('seg_id', 'klassen', 'kriterium', 'befund', 'messwert', 'methode'))
            kl, kr_, bf, me = kl.upper().replace(' ', '').replace(',', ''), kr_.upper(), bf.upper(), me.upper()
            try:
                mwf = float(mw.replace(',', '.')) if mw else None
            except ValueError:
                mwf = 'x'
            fehler = []
            if sid not in _alle_sid:
                fehler.append('seg_id unbekannt')
            if not kl or set(kl) - set('ABCD'):
                fehler.append('klassen nicht aus ABCD')
            if kr_ not in BEFUND_KRIT:
                fehler.append('kriterium nicht ' + '/'.join(BEFUND_KRIT))
            if bf not in BEFUND_ART:
                fehler.append('befund nicht ' + '/'.join(BEFUND_ART))
            if me not in BEFUND_METHODE:
                fehler.append('methode nicht ' + '/'.join(BEFUND_METHODE))
            if mwf == 'x':
                fehler.append('messwert keine Zahl')
            elif bf == 'PASSIERBAR' and kr_ in ('BREITE', 'HOEHE') and mwf is None:
                fehler.append('messwert fehlt (Pflicht bei {} PASSIERBAR)'.format(kr_))
            if not z.get('geprueft_von'):
                fehler.append('geprueft_von fehlt')
            try:
                datetime.strptime(z.get('datum', ''), '%Y-%m-%d')
            except ValueError:
                fehler.append('datum nicht JJJJ-MM-TT')
            if fehler:
                bef_fehler.append('Zeile {} ({}): {}'.format(nr, sid or '-', ', '.join(fehler)))
                continue
            BEFUNDE[sid].append(dict(klassen=kl, krit=kr_, befund=bf, wert=mwf, methode=me, beleg=z.get('beleg', ''),
                                     von=z['geprueft_von'], datum=z['datum'], bem=z.get('bemerkung', '')))
log('Befunde {}: {} gueltig, {} ungueltig'.format(BEF.name if BEF.exists() else '(keine Datei)', sum(len(v) for v in BEFUNDE.values()), len(bef_fehler)))
for t in bef_fehler:
    log('  NICHT ANGEWENDET ' + t)


def kriterium_von(grund):
    """V9.2f: Kriterium und Stufe eines Grundes (Texte wie oben erzeugt)."""
    for pref, kr_, stufe in (('Breite nicht entscheidbar', 'BREITE', 1), ('Breite:', 'BREITE', 2),
                             ('Gewicht ungeklaert', 'GEWICHT', 1), ('Gewicht:', 'GEWICHT', 2),
                             ('Hoehe ungeklaert', 'HOEHE', 1), ('Hoehe knapp', 'HOEHE', 1), ('Hoehe:', 'HOEHE', 2),
                             ('Hindernis ungeklaert', 'HINDERNIS', 1), ('Hindernis:', 'HINDERNIS', 2),
                             ('Freigabe/Sperre R2', 'SPERRE', 2), ('Befund ', 'BEFUND', 2)):
        if grund.startswith(pref):
            return kr_, stufe
    raise ValueError('Grund ohne Kriterium: ' + grund[:60])


STUFE = ('VALIDIERT', 'UNVALIDIERT', 'GESPERRT')
bef_prot, bef_wechsel, bef_wechsel_liste = [], Counter(), []

V8K = defaultdict(dict)
for sid, fz, kr, kat, gr in db.execute("select seg_id, fahrzeug, kriterium, kategorie, grund from bewertung_v8 where fahrzeug like 'KAT_%'"):
    V8K[(sid, fz[-1])][kr] = (kat, gr or '')
cols = [r[1] for r in db.execute('pragma table_info(netz_v5)')]
neu = ['v9_fahrbahn_median_m REAL', 'v9_frei_fest_min_m REAL', 'v9_untere_schranke_m REAL', 'v9_obere_schranke_m REAL',
       'v9_sigma_m REAL', 'v9_abdeckung REAL', 'v9_luecke_innen_m REAL', 'v9_engstelle_pos_m REAL', 'v9_rand TEXT', 'v9_hindernisse TEXT']
for p in 'abcd':
    neu += ['{}_breite_v9 TEXT'.format(p), '{}_breite_v9_beleg TEXT'.format(p), '{}_breite_v9_grund TEXT'.format(p),
            '{}_v9_status TEXT'.format(p), '{}_v9_grund TEXT'.format(p), '{}_v9_befund TEXT'.format(p)]
for d in neu:
    if d.split()[0] not in cols:
        db.execute('ALTER TABLE netz_v5 ADD COLUMN ' + d)

RANG = {'VALIDIERT': 0, 'UNVALIDIERT': 1, 'GESPERRT': 2}
stat = Counter(); km = Counter(); wirkung = Counter(); wirkung_liste = []
regel4m, regel4m_liste = Counter(), []
import re as _re
_ACC = _re.compile(r'"access"=>"([^"]*)"')
rows = list(db.execute('select fid, seg_id, highway_type, laenge_m, zone, steigung_max_pct, maxwidth, other_tags, access_type, v8_g_limit, v8_g_quelle, service_type, {}, maxheight, name from netz_v5 where ist_routingtyp = 1'.format(
    ', '.join('{}_kat_v7_grund'.format(p) for p in 'abcd'))))
upd = []
for fid, sid, hw, L, zone, st, mw, ot, at, glim, gq, svc, ga, gb, gc, gd, mh, nm in rows:
    _m = _ACC.search(ot or '')
    acc = (_m.group(1) if _m else (at or '')).lower()
    privat = acc in ('private', 'no')
    unter = (BREITE.get(sid, {}).get('ueber_unterirdisch_anteil') or 0) >= 0.2
    m = BREITE.get(sid, {})
    rec = dict(v9_fahrbahn_median_m=m.get('fahrbahn_median_m'), v9_frei_fest_min_m=m.get('frei_fest_min_rel_m'),
               v9_untere_schranke_m=m.get('untere_schranke_m'), v9_obere_schranke_m=m.get('obere_schranke_fest_m'),
               v9_sigma_m=m.get('sigma_breite_m'), v9_abdeckung=m.get('abdeckung'), v9_luecke_innen_m=m.get('luecke_innen_m'),
               v9_engstelle_pos_m=m.get('engstelle_pos_m'), v9_rand='{} / {}'.format(m.get('rand_links', ''), m.get('rand_rechts', '')),
               v9_hindernisse=(m.get('hindernisse') or '')[:200])
    for p, g7 in zip('abcd', (ga, gb, gc, gd)):
        P = p.upper()
        e = m.get(p + '_breite') or 'NICHT_ENTSCHEIDBAR'
        gr = m.get(p + '_breite_grund') or 'keine Messung'
        beleg = 'GEOMETRISCH' if m.get('untere_schranke_m') is not None else 'NICHT_UEBERPRUEFBAR'   # Messung vorhanden (Ergebnis kann trotzdem 'nicht entscheidbar' sein)
        bed = m.get(p + '_bedarf_m')
        if m:
            # V9.2: Entscheid neu (Reserve je Profil, Spiegel ueber Trottoir/Insel, Bauwerksbreite in Messluecken)
            K_, S_ = MASSE[P]['breite_karosserie_m'], MASSE[P]['breite_spiegel_m']
            n_tief = (m.get('rand_links') in NIEDRIG) + (m.get('rand_rechts') in NIEDRIG)
            ueber = n_tief * (S_ - K_) / 2.0
            bed = round(max(K_ + 2 * RESERVE[P], S_ + 2 * RES_SPIEGEL - ueber), 3)
            wlo, wlof, whif = m.get('untere_schranke_m'), m.get('untere_schranke_fest_m'), m.get('obere_schranke_fest_m')
            li = m.get('luecke_innen_m') or 0.0
            zusatz = ''
            if li > LUECKE_INNEN_MAX_M and (m.get('bauwerk_anteil_luecke') or 0) >= 0.999 and m.get('bauwerk_untere_schranke_m') is not None:
                zusatz = '; Messluecke unter {} mit Bauwerksbreite {:.1f} m - 3.0 m ueberbrueckt (abgeleitet)'.format(m.get('bauwerk_art'), m['bauwerk_breite_min_m'])
                wlo = min(wlo, m['bauwerk_untere_schranke_m']) if wlo is not None else m['bauwerk_untere_schranke_m']
                li = 0.0
            if wlo is not None:
                e, gr = entscheide(bed, wlo, wlof if wlof is not None else wlo, whif if whif is not None else wlo, True, li, minimum=K_)
                if e == 'UNZUREICHEND' and m.get('rand_hart') == 0:
                    e = 'NICHT_ENTSCHEIDBAR'; gr = 'AV-Fahrbahn zu schmal, Rand weich (Bankett evtl. befahrbar): ' + gr[:120]
                bed_ohne = round(max(K_ + 2 * RESERVE[P], S_ + 2 * RES_SPIEGEL), 3)
                if ueber and e == 'AUSREICHEND' and wlo < bed_ohne:          # V9.2b: nur nennen, wenn die Regel entscheidet
                    gr += '; Spiegel ueber {} Trottoir/Insel ({:.2f} m je Seite)'.format(n_tief, (S_ - K_) / 2)
                if PROFILPRUEFUNG:                                         # V9.2h: Profilpruefung, stuft nur herab
                    e_vor = e
                    e, gr = profilpruefung(e, gr, m, p, abgeleitet=bool(zusatz))
                    if e != e_vor:
                        profil_wirkung[(P, gr[:15], zone)] += (L or 0) / 1000
                gr += zusatz
                if zusatz and e == 'AUSREICHEND':
                    beleg_bw = True
            zu_schmal = whif is not None and whif < K_                  # V9.2b: gemessen schmaler als die Karosserie -> keine Ableitung
            if p == 'a' and e == 'NICHT_ENTSCHEIDBAR' and (svc or '').lower() in PW_ZUFAHRT and not zu_schmal:
                e = 'AUSREICHEND'; gr = 'Hauszufahrt/Parkplatzgasse (service={}) - fuer Personenwagen gebaut (abgeleitet); Messung: {}'.format(svc, gr[:100])
        try:
            mwf = float(str(mw).replace(',', '.').split()[0]) if mw not in (None, '') else None
        except ValueError:
            mwf = None
        if mwf is not None and bed and mwf < MASSE[P]['breite_karosserie_m']:
            e, beleg, gr = 'UNZUREICHEND', 'ABGELEITET', 'Signal Hoechstbreite {:.2f} m < Karosserie {:.2f} m'.format(mwf, MASSE[P]['breite_karosserie_m'])
        if e == 'AUSREICHEND' and ('abgeleitet' in gr):
            beleg = 'ABGELEITET'
        if e == 'NICHT_ENTSCHEIDBAR' and hw in NORMPROFIL:
            e, beleg = 'AUSREICHEND', 'ABGELEITET'
            gr = 'Normalprofil Nationalstrasse/Autostrasse (Fahrstreifen >= 3.50 m); AV-Messung: ' + gr[:120]
        elif e == 'NICHT_ENTSCHEIDBAR' and g7 and g7.startswith(('R4', 'R5', 'R6')):
            beleg = 'GESCHAETZT'
            gr = gr[:150] + ' | Schaetzung V7.6: ' + g7[:80]
        kr = V8K.get((sid, P), {})
        status, gruende, hinweise = 'VALIDIERT', [], []
        if e == 'UNZUREICHEND':
            status = 'GESPERRT'; gruende.append('Breite: ' + gr[:110])
        elif e == 'NICHT_ENTSCHEIDBAR':
            status = 'UNVALIDIERT'; gruende.append('Breite nicht entscheidbar: ' + gr[:110])
        t = GEWICHT[P]
        if glim is not None and t > glim + 1e-9:
            status = 'GESPERRT'; gruende.append('Gewicht: Hoechstgewicht {:.1f} t < {:.1f} t ({})'.format(glim, t, gq))
        elif t > 18.0 and hw == 'service' and privat:
            status = 'UNVALIDIERT' if RANG[status] < 1 else status
            gruende.append('Gewicht ungeklaert: private Zufahrt (access={}), Tragfaehigkeit fuer {:.1f} t nicht belegt'.format(acc, t))
        elif t > 18.0 and unter and (hw == 'service' or privat):
            status = 'UNVALIDIERT' if RANG[status] < 1 else status
            gruende.append('Gewicht ungeklaert: ueber unterirdischem Bauwerk (AV), Tragfaehigkeit fuer {:.1f} t nicht belegt'.format(t))
        sig_h = any(o['h'] is not None for o in HK.get(sid, ()))
        for k in ('hoehe', 'hindernis'):
            kat, g = kr.get(k, ('KEIN_HINWEIS', ''))
            if k == 'hoehe' and kat == 'UNGEKLAERT' and g.startswith('Ueberbauung ohne Hoehenangabe') and HOEHENREGEL_4M:
                # V9.2g: signalisierte Hoehe (Hinderniskartei/Fachstelle) entscheidet weiter unten; sonst auf oeffentlichen
                # Strassen gilt ohne Signal mind. 4.00 m (VRV, Tiefbau Stadt Bern 4.11.2026)
                if sig_h:
                    regel4m[(P, 'signal')] += 1
                    continue
                if hw in OEFFENTLICH_HW and not privat and MASSE[P]['hoehe_m'] + HOEHE_RESERVE <= HOEHE_OHNE_SIGNAL_M:
                    hinweise.append('Hoehe abgeleitet: {}, kein Hoehensignal -> mind. {:.2f} m (VRV; Tiefbau Stadt Bern 4.11.2026)'.format(
                        g[:60], HOEHE_OHNE_SIGNAL_M))
                    regel4m[(P, 'regel')] += 1
                    regel4m_liste.append('{} {} {} ({:.0f} m, {})'.format(P, sid, nm or '', L or 0, hw))
                    continue
            if kat == 'BESCHRAENKUNG_BESTAETIGT':
                status = 'GESPERRT'; gruende.append('{}: {}'.format(k.capitalize(), g[:100]))
            elif kat in ('VERDACHT_GRENZFALL', 'UNGEKLAERT'):
                if RANG[status] < 1:
                    status = 'UNVALIDIERT'
                gruende.append('{} ungeklaert: {}'.format(k.capitalize(), g[:100]))
        # V9.2d: signalisierte Werte der Hinderniskartei (amtlich) und OSM maxheight=below_default
        vor = status
        hz = MASSE[P]['hoehe_m']
        for o in HK.get(sid, ()):
            quelle = o.get('quelle') or 'Hinderniskartei SVSA Nr. {}, {}'.format(o['nr'], o['art'][:40])
            if o['t'] is not None and t > o['t'] + 1e-9:
                status = 'GESPERRT'; gruende.append('Gewicht: Signal {:.1f} t < {:.1f} t ({})'.format(o['t'], t, quelle))
            if o['h'] is not None:
                if hz > o['h'] + 1e-9:
                    status = 'GESPERRT'; gruende.append('Hoehe: Signal {:.2f} m < {:.2f} m ({})'.format(o['h'], hz, quelle))
                elif hz > o['h'] - HOEHE_RESERVE:
                    status = 'UNVALIDIERT' if RANG[status] < 1 else status
                    gruende.append('Hoehe knapp: Signal {:.2f} m, Fahrzeug {:.2f} m ({})'.format(o['h'], hz, quelle))
        hk_hoehe = any(o['h'] is not None for o in HK.get(sid, ()))
        if str(mh or '').strip().lower() == 'below_default' and hz > GEBAEUDE_DURCHFAHRT_OK_BIS_M and not hk_hoehe:
            status = 'UNVALIDIERT' if RANG[status] < 1 else status
            gruende.append('Hoehe ungeklaert: OSM maxheight=below_default (niedriger als Standard, Wert unbekannt)')
        if RANG[status] > RANG[vor]:
            wirkung[(P, vor, status)] += 1
            if zone == 'BEWERTUNG':
                km[(P, 'v9_2d', status)] += (L or 0) / 1000
            wirkung_liste.append('{} {} {} ({:.0f} m): {} -> {}'.format(P, sid, nm or '', L or 0, vor, status))
        if (g7 or '').startswith('R2'):
            status = 'GESPERRT'; gruende.append('Freigabe/Sperre R2: ' + g7[:100])
        if sid in HINWEIS_SEG and status == 'GESPERRT':
            hinweise.append(HINWEIS_SEG[sid])
        # V9.2f: gepruefte Befunde. Selbstkontrolle: Status = hoechste Stufe der Gruende (muss vor den Befunden stimmen)
        stufen = [kriterium_von(x) for x in gruende]
        assert STUFE[max([s for _, s in stufen] or [0])] == status, (sid, P, status, gruende)
        bef_txt, vor_bef = [], status
        bedarf = (bed if bed else max(MASSE[P]['breite_karosserie_m'] + 2 * RESERVE[P], MASSE[P]['breite_spiegel_m'] + 2 * RES_SPIEGEL))
        for b in BEFUNDE.get(sid, ()):
            if P not in b['klassen']:
                continue
            kurz = '{} {} ({}, {}, {}{})'.format(b['krit'].capitalize(), b['befund'].lower().replace('_', ' '), b['methode'].lower(), b['datum'], b['von'],
                                                 ', ' + b['beleg'][:40] if b['beleg'] else '')
            ergebnis = ''
            if b['befund'] == 'NICHT_PASSIERBAR':
                gruende = [x for x in gruende if kriterium_von(x) != (b['krit'], 1)]     # "ungeklaert" ist jetzt geklaert
                gruende.append('Befund ' + kurz + (': ' + b['bem'][:60] if b['bem'] else ''))
                if b['krit'] == 'BREITE':
                    e, beleg = 'UNZUREICHEND', b['methode']
                    gr = 'Befund {} {}: nicht passierbar{}; vorher: {}'.format(b['methode'].lower(), b['datum'],
                                                                          ', {:.2f} m'.format(b['wert']) if b['wert'] is not None else '', gr[:150])
                ergebnis = 'uebernommen (gesperrt)'
            else:
                if b['krit'] == 'BREITE':
                    noetig = bedarf + (ORTHO_MARGE_M if b['methode'] == 'ORTHOFOTO' else 0.0)
                    if b['wert'] < noetig - 1e-9:
                        ergebnis = 'abgelehnt: {:.2f} m < noetig {:.2f} m (Bedarf {:.2f} m{})'.format(
                            b['wert'], noetig, bedarf, ' + Orthofoto-Zuschlag {:.2f} m'.format(ORTHO_MARGE_M) if b['methode'] == 'ORTHOFOTO' else '')
                elif b['krit'] == 'HOEHE' and b['wert'] < MASSE[P]['hoehe_m'] + HOEHE_RESERVE - 1e-9:
                    ergebnis = 'abgelehnt: {:.2f} m < Fahrzeughoehe {:.2f} m + Reserve {:.2f} m'.format(b['wert'], MASSE[P]['hoehe_m'], HOEHE_RESERVE)
                elif b['krit'] == 'GEWICHT' and b['wert'] is not None and b['wert'] < t - 1e-9:
                    ergebnis = 'abgelehnt: {:.1f} t < Fahrzeuggewicht {:.1f} t'.format(b['wert'], t)
                if not ergebnis:
                    offen = [x for x in gruende if kriterium_von(x) == (b['krit'], 1)]
                    hart = [x for x in gruende if kriterium_von(x) == (b['krit'], 2)]
                    gruende = [x for x in gruende if x not in offen]
                    if b['krit'] == 'BREITE' and not hart:
                        e, beleg = 'AUSREICHEND', b['methode']
                        gr = 'Befund {} {}: {:.2f} m >= Bedarf {:.2f} m; vorher: {}'.format(b['methode'].lower(), b['datum'], b['wert'], bedarf, gr[:150])
                    if hart:
                        ergebnis = 'Widerspruch: Modell sperrt ({}), bleibt gesperrt'.format(hart[0][:80])
                    elif offen:
                        ergebnis = 'uebernommen ({} Grund aufgehoben)'.format(len(offen))
                    else:
                        ergebnis = 'ohne Wirkung (kein offener Grund fuer dieses Kriterium)'
                    if offen or not hart:
                        bef_txt.append(kurz)
            bef_prot.append([sid, nm or '', P, b['krit'], b['befund'], b['wert'] if b['wert'] is not None else '', b['methode'], b['datum'], b['von'], ergebnis])
        if bef_txt or any(kriterium_von(x)[0] == 'BEFUND' for x in gruende):
            status = STUFE[max([kriterium_von(x)[1] for x in gruende] or [0])]
            if status != vor_bef:
                bef_wechsel[(P, vor_bef, status)] += 1
                bef_wechsel_liste.append('{} {} {} ({:.0f} m): {} -> {}'.format(P, sid, nm or '', L or 0, vor_bef, status))
                if zone == 'BEWERTUNG':
                    km[(P, 'befund', status)] += (L or 0) / 1000
        rec[p + '_v9_befund'] = ' | '.join(bef_txt)[:300] or None
        if bef_txt:
            hinweise.insert(0, 'nach Befund: ' + ' | '.join(bef_txt))
        if st is not None and GEWICHT[P] > STEIGUNG_T:
            pmax = STEIGUNG_PLAUSIBEL.get((hw or '').replace('_link', ''), 30.0)
            if STEIGUNG_PCT < st <= pmax:
                hinweise.append('Hinweis Steigung ca. {:.0f} % (Steigfaehigkeit nicht im Datensatz)'.format(st))
        rec[p + '_breite_v9'] = e; rec[p + '_breite_v9_beleg'] = beleg; rec[p + '_breite_v9_grund'] = gr[:250]
        rec[p + '_v9_status'] = status
        rec[p + '_v9_grund'] = (('validiert ' if status == 'VALIDIERT' and not gruende and (bef_txt or any(x.startswith('Hoehe abgeleitet') for x in hinweise)) else '')
                                + ' | '.join(gruende + hinweise)
                                or 'validiert (Breite nachgewiesen, keine Hinweise auf Hoehe/Gewicht/Hindernis)')[:300]
        if zone == 'BEWERTUNG':
            km[(P, 'breite', e)] += (L or 0) / 1000
            km[(P, 'beleg', beleg)] += (L or 0) / 1000
            km[(P, 'status', status)] += (L or 0) / 1000
    upd.append((rec, fid))
felder = list(upd[0][0])
db.executemany('update netz_v5 set {} where fid = ?'.format(', '.join('"{}" = ?'.format(f) for f in felder)),
               [[r[f] for f in felder] + [fid] for r, fid in upd])
db.execute("INSERT INTO bors_meta (schluessel, wert) VALUES ('v9_2d', ?)", ('{} aus {} + {} + {}'.format(STAMP, SRC.name, BR.name, HKD.name),))
db.execute("INSERT INTO bors_meta (schluessel, wert) VALUES ('v9_2f', ?)", ('{} Befunde aus {}: {} gueltig, {} ungueltig'.format(
    STAMP, BEF.name if BEF.exists() else '(keine Datei)', sum(len(v) for v in BEFUNDE.values()), len(bef_fehler)),))
db.execute("INSERT INTO bors_meta (schluessel, wert) VALUES ('v9_2g', ?)", ('{} Signale Fachstelle aus {}: {}; Hoehenregel 4 m: {}'.format(
    STAMP, SIGF.name if SIGF.exists() else '(keine Datei)', dict(sf_n), 'ein' if HOEHENREGEL_4M else 'aus'),))
db.execute("INSERT INTO bors_meta (schluessel, wert) VALUES ('v9_2h', ?)", ('{} Profilpruefung Breite: {} ({})'.format(
    STAMP, 'ein' if PROFILPRUEFUNG else 'aus (Breitendatei ohne V9.3-Felder)', BEDARF_REGEL),))
db.commit(); db.close()
log('')
log('V9.2h Profilpruefung Breite: {}'.format('ein, ' + BR.name if PROFILPRUEFUNG else 'aus (Breitendatei {} ohne V9.3-Felder, Ergebnis wie V9.2g)'.format(BR.name)))
for (P, art, zone), km_ in sorted(profil_wirkung.items()):
    log('  {} {} [{}]: {:.2f} km AUSREICHEND -> NICHT_ENTSCHEIDBAR'.format(P, art, zone, km_))
log('V9.2g Hoehenregel (ohne Signal >= {:.2f} m, oeffentliche Strassen): {}'.format(HOEHE_OHNE_SIGNAL_M, ', '.join(
    '{} {}: {}'.format(P, a, n) for (P, a), n in sorted(regel4m.items())) or 'keine'))
for z in regel4m_liste:
    log('  ' + z)
log('')
log('V9.2d/g Statuswechsel durch Hinderniskartei/Signale Fachstelle/below_default (Abschnitte): {}'.format(
    ', '.join('{} {}->{}: {}'.format(P, a, z, n) for (P, a, z), n in sorted(wirkung.items())) or 'keine'))
for z in wirkung_liste:
    log('  ' + z)
log('')
log('V9.2f Statuswechsel durch Befunde (Abschnitte): {}'.format(
    ', '.join('{} {}->{}: {}'.format(P, a, z, n) for (P, a, z), n in sorted(bef_wechsel.items())) or 'keine'))
for z in bef_wechsel_liste:
    log('  ' + z)
with open(str(NMDIR / (OUT.stem + '_Befunde_Protokoll.csv')), 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh, delimiter=';')
    w.writerow(['seg_id', 'name', 'klasse', 'kriterium', 'befund', 'messwert', 'methode', 'datum', 'geprueft_von', 'ergebnis'])
    w.writerows(bef_prot)
for r in bef_prot:
    if not r[-1].startswith('uebernommen'):
        log('  Befund {} {} {}: {}'.format(r[0], r[2], r[3], r[-1]))
log('')
log('Ergebnis Zielgebiet (km):')
for P in 'ABCD':
    log('  {} Breite: ausreichend {:.0f} | nicht entscheidbar {:.0f} | unzureichend {:.0f}   Beleg: geometrisch {:.0f} | abgeleitet {:.0f} | geschaetzt {:.0f} | nicht ueberpruefbar {:.0f}'.format(
        P, km[(P, 'breite', 'AUSREICHEND')], km[(P, 'breite', 'NICHT_ENTSCHEIDBAR')], km[(P, 'breite', 'UNZUREICHEND')],
        km[(P, 'beleg', 'GEOMETRISCH')], km[(P, 'beleg', 'ABGELEITET')], km[(P, 'beleg', 'GESCHAETZT')], km[(P, 'beleg', 'NICHT_UEBERPRUEFBAR')]))
    log('  {} Routing: validiert {:.0f} | unvalidiert {:.0f} | gesperrt {:.0f}   (davon durch V9.2d: unvalidiert {:.2f} | gesperrt {:.2f})'.format(
        P, km[(P, 'status', 'VALIDIERT')], km[(P, 'status', 'UNVALIDIERT')], km[(P, 'status', 'GESPERRT')],
        km[(P, 'v9_2d', 'UNVALIDIERT')], km[(P, 'v9_2d', 'GESPERRT')]))
    log('  {} durch Befunde (V9.2f): jetzt validiert {:.2f} | unvalidiert {:.2f} | gesperrt {:.2f}'.format(
        P, km[(P, 'befund', 'VALIDIERT')], km[(P, 'befund', 'UNVALIDIERT')], km[(P, 'befund', 'GESPERRT')]))
log('Fertig in {:.0f} s: {}'.format(time.time() - T0, OUT))
(NMDIR / (OUT.stem + '_BERICHT.txt')).write_text('\n'.join(REP), encoding='utf-8')
