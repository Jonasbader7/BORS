# -*- coding: utf-8 -*-
"""BORS Bern - Bewertung V8: Abschnitt x konkretes Fahrzeug -> Kategorie + Begruendung je Kriterium.
Gemeinsamer Code fuer 21_Netzmaster_V8.py (Karten A-D) und Router V8 (jedes Fahrzeug aus BORS_Fahrzeuge_V1.csv).

BREITE (V8, fachlich):
  Karosserie gegen alles am Boden: netto = Strassenflaeche minus parkierte Autos (Parkflaechen/-felder) minus Baeume
  in der Fahrbahn  >=  Karosseriebreite + 2 x 0.25 m Sicherheitsabstand.
  Spiegel (ca. 2 m ueber Boden) ragen ueber parkierte Personenwagen und ueber den Randstein. Feste Objekte (Mauer,
  Laterne, Signal) stehen bei Trottoir mind. 0.5 m vom Randstein (VSS lichter Raum). Darum zaehlt die Spiegelbreite
  nur dort, wo die Strasse ohne Trottoir an feste Objekte grenzt (OSM sidewalk=no/none, Begegnungszone, Zufahrt):
  brutto (Strassenflaeche ohne Parkabzug, minus Baeume) >= Spiegelbreite + 2 x 0.10 m.
  Ohne Trottoir-Angabe: halber Spiegelueberhang zulaessig (vorsichtige Mitte).
  Grenzfall: weniger als 0.30 m Reserve ueber dem Bedarf.
"""
import csv
from pathlib import Path

RES_KOERPER = 0.25
RES_SPIEGEL = 0.10
GRENZ = 0.30
FKS_ZUFAHRT_T = 18.0
STEIGUNG_T = 7.5
STEIGUNG_PCT = 15.0
HOEHE_RESERVE = 0.10
GEBAEUDE_DURCHFAHRT_OK_BIS_M = 2.0      # Fahrzeuge bis 2.0 m Hoehe passieren Ueberbauungen ohne Hoehenangabe
RANG = {'KEIN_HINWEIS': 0, 'UNGEKLAERT': 1, 'VERDACHT_GRENZFALL': 2, 'BESCHRAENKUNG_BESTAETIGT': 3}


def lade_fahrzeuge(pfad):
    out = {}
    with open(str(pfad), encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter=';'):
            v = dict(r)
            for k in ('breite_karosserie_m', 'breite_spiegel_m', 'hoehe_m', 'laenge_m', 'gewicht_t', 'radstand_m',
                      'ueberhang_vorne_m', 'ueberhang_hinten_m', 'wendekreis_m'):
                v[k] = float(r[k])
            out[r['id']] = v
    return out


def huelle(fz, kat):
    """Massgebendes Fahrzeug einer Kategorie = Maximum je Mass (wie Fahrzeuguebersicht Kap. 6)."""
    m = [v for v in fz.values() if v['kategorie'] == kat]
    h = dict(id='KAT_' + kat, kategorie=kat, bezeichnung='Kategorie ' + kat + ' (Huelle)')
    for k in ('breite_karosserie_m', 'breite_spiegel_m', 'hoehe_m', 'laenge_m', 'gewicht_t', 'radstand_m',
              'ueberhang_vorne_m', 'ueberhang_hinten_m', 'wendekreis_m'):
        h[k] = max(v[k] for v in m)
    return h


def _f(v):
    try:
        return None if v in (None, '') else float(v)
    except (TypeError, ValueError):
        return None


def spiegel_ueberhang(seg):
    sw = (seg.get('sidewalk') or '').lower()
    if seg.get('hw') in ('living_street', 'service', 'pedestrian') or sw in ('no', 'none'):
        return 0.0
    if sw in ('both', 'left', 'right', 'separate', 'yes'):
        return None          # Trottoir: Spiegel ragt frei ueber den Randstein
    return 0.5               # unbekannt: halber Ueberhang erlaubt


def breite(fz, seg):
    wk, ws = fz['breite_karosserie_m'], fz['breite_spiegel_m']
    mw = _f(seg.get('maxwidth'))
    if mw is not None and wk > mw + 1e-9:
        return 'BESCHRAENKUNG_BESTAETIGT', 'Signal Hoechstbreite {:.2f} m < {:.2f} m'.format(mw, wk), 'OSM_SIGNAL', 'BELEGT'
    st = seg.get('v8_b_status')
    bk = wk + 2 * RES_KOERPER
    ueb = spiegel_ueberhang(seg)
    bs = None if ueb is None else ws - ueb * (ws - wk) + 2 * RES_SPIEGEL
    km, fm = _f(seg.get('v8_b_koerper_min')), _f(seg.get('v8_b_fest_min'))
    f3 = _f(seg.get('v8_b_fest_p3'))
    if st in ('GEMESSEN', 'TEILGEMESSEN') and f3 is not None and f3 < 2.0 and seg.get('hw') not in ('service', 'track'):
        return ('UNGEKLAERT', 'Messung unplausibel: oeffentliche Strasse mit < 2.0 m Strassenflaeche (AV-Flaeche unvollstaendig?)',
                'MOPUBE_V8', 'FEHLT')
    if st in ('GEMESSEN', 'TEILGEMESSEN') and f3 is not None and f3 < wk and seg.get('hw') in ('service', 'track'):
        # Zufahrten/Hofflaechen: AV-"Strasse" deckt oft nur einen Teil der befestigten Flaeche ab (Rest = uebrige befestigte,
        # Gebaeudeumschwung). Ohne Messung der Nebenflaechen keine Bestaetigung (Negativkontrolle Schleppkurve: 25 % Fehlalarme).
        return ('VERDACHT_GRENZFALL', 'Zufahrt: AV-Strassenflaeche nur {:.2f} m (< Karosserie {:.2f} m); angrenzende befestigte Flaeche nicht gemessen'.format(f3, wk),
                'MOPUBE_V8', 'BELEGT')
    if st in ('GEMESSEN', 'TEILGEMESSEN') and f3 is not None and f3 < wk:
        return ('BESCHRAENKUNG_BESTAETIGT', 'zu schmal auch ohne parkierte Autos: mind. 3 Querprofile (6 m) Strassenflaeche < Karosserie {:.2f} m'.format(wk),
                'MOPUBE_V8', 'BELEGT')
    if st == 'TEILGEMESSEN' and km is not None and km < bk + GRENZ:
        return 'VERDACHT_GRENZFALL', 'gemessene Teile: min {:.2f} m < Bedarf {:.2f} m (Karosserie {:.2f} + Reserve + 0.30), Rest nicht messbar'.format(km, bk + GRENZ, wk), 'MOPUBE_V8', 'BELEGT'
    if st == 'GEMESSEN':
        txt = []
        kat = 'KEIN_HINWEIS'
        if km is not None and km < bk:
            kat = 'VERDACHT_GRENZFALL'; txt.append('eng: Fahrbahn zwischen Parkierung/Baeumen min {:.2f} m < Karosserie {:.2f} m + Reserve = {:.2f} m'.format(km, wk, bk))
        elif km is not None and km < bk + GRENZ:
            kat = 'VERDACHT_GRENZFALL'; txt.append('Grenzfall: min {:.2f} m, Bedarf Karosserie {:.2f} m'.format(km, bk))
        if bs is not None and fm is not None:
            if fm < bs:
                kat = 'VERDACHT_GRENZFALL'; txt.append('Spiegel: Strassenflaeche min {:.2f} m < Spiegel {:.2f} m (ohne Trottoir)'.format(fm, bs))
            elif fm < bs + GRENZ and kat == 'KEIN_HINWEIS':
                kat = 'VERDACHT_GRENZFALL'; txt.append('Spiegel-Grenzfall: min {:.2f} m'.format(fm))
        if kat == 'KEIN_HINWEIS':
            txt.append('gemessen: min {:.2f} m >= {:.2f} m (+0.30)'.format(km if km is not None else 6.0, bk))
        return kat, '; '.join(txt), 'MOPUBE_V8', 'BELEGT'
    u = _f(seg.get('v8_b_untergrenze'))
    if u is not None:
        if u >= bk + GRENZ and (bs is None or u >= bs + GRENZ):
            return 'KEIN_HINWEIS', 'abgeleitet: mind. {:.2f} m ({})'.format(u, seg.get('v8_b_text') or ''), 'ABGELEITET', 'ABGELEITET'
    v7 = seg.get('v7_breite_' + fz['kategorie'])
    if v7 and v7[0] == 'KEIN_HINWEIS' and not v7[2].startswith('R1'):
        return 'KEIN_HINWEIS', 'V7.6-Ableitung ({}) fuer Kategorie {}'.format(v7[1], fz['kategorie']), v7[1] or 'V7', 'ABGELEITET'
    if v7 and v7[0] == 'VERDACHT_GRENZFALL' and v7[1] in ('TLM_KLASSE', 'TLM_NOMINAL', 'OSM_WIDTH'):
        return 'VERDACHT_GRENZFALL', 'V7.6: {}'.format(v7[2][:100]), v7[1], 'ABGELEITET'
    if u is not None:
        return 'UNGEKLAERT', 'nur Untergrenze {:.2f} m bekannt ({})'.format(u, seg.get('v8_b_text') or ''), 'ABGELEITET', 'ABGELEITET'
    return 'UNGEKLAERT', 'Breite nicht messbar ({})'.format(seg.get('v8_b_text') or 'keine Messung'), 'KEINE', 'FEHLT'


def hoehe(fz, seg):
    h = fz['hoehe_m']
    lim = _f(seg.get('v8_h_limit'))
    st = seg.get('v8_h_status') or 'KEINE'
    if lim is not None:
        if h > lim + 1e-9:
            return 'BESCHRAENKUNG_BESTAETIGT', 'Hoechsthoehe {:.2f} m < {:.2f} m ({})'.format(lim, h, seg.get('v8_h_text') or ''), st, 'BELEGT'
        if h > lim - HOEHE_RESERVE:
            return 'VERDACHT_GRENZFALL', 'Hoechsthoehe {:.2f} m knapp'.format(lim), st, 'BELEGT'
        return 'KEIN_HINWEIS', 'Hoechsthoehe {:.2f} m'.format(lim), st, 'BELEGT'
    if st == 'UEBERBAUUNG':
        if h <= GEBAEUDE_DURCHFAHRT_OK_BIS_M:
            return 'KEIN_HINWEIS', 'Ueberbauung ohne Angabe, Fahrzeug nur {:.2f} m hoch'.format(h), 'REGEL', 'ABGELEITET'
        return 'UNGEKLAERT', 'Ueberbauung ohne Hoehenangabe ({})'.format(seg.get('v8_h_text') or ''), 'KEINE', 'FEHLT'
    if st in ('ABGELEITET_R7', 'NORMPROFIL'):
        return 'KEIN_HINWEIS', seg.get('v8_h_text') or st, 'REGEL', 'ABGELEITET'
    return 'KEIN_HINWEIS', 'keine Ueberbauung in OSM', 'OSM_GEOMETRIE', 'ABGELEITET'


def gewicht(fz, seg):
    t = fz['gewicht_t']
    lim = _f(seg.get('v8_g_limit'))
    if lim is not None:
        if t > lim + 1e-9:
            return 'BESCHRAENKUNG_BESTAETIGT', 'Hoechstgewicht {:.1f} t < {:.1f} t ({})'.format(lim, t, seg.get('v8_g_quelle') or ''), seg.get('v8_g_quelle') or 'SIGNAL', 'BELEGT'
        return 'KEIN_HINWEIS', 'Hoechstgewicht {:.1f} t'.format(lim), seg.get('v8_g_quelle') or 'SIGNAL', 'BELEGT'
    if seg.get('hw') == 'service' and t > FKS_ZUFAHRT_T:
        return 'VERDACHT_GRENZFALL', 'Zufahrt: nach FKS nur {:.0f} t ausgelegt ({:.1f} t)'.format(FKS_ZUFAHRT_T, t), 'REGEL_FKS', 'ANNAHME'
    return 'KEIN_HINWEIS', 'kein Gewichtssignal -> gesetzlich 40 t', 'REGEL_40T', 'ANNAHME'


def steigung(fz, seg):
    p = _f(seg.get('steigung_max_pct'))
    if p is None:
        return 'KEIN_HINWEIS', 'nicht berechnet (Bruecke/Tunnel/kurz)', 'KEINE', 'FEHLT'
    if fz['gewicht_t'] > STEIGUNG_T and p > STEIGUNG_PCT:
        return 'VERDACHT_GRENZFALL', 'Steigung ca. {:.0f} % > {:.0f} % (schwer beladen)'.format(p, STEIGUNG_PCT), 'SWISSALTI3D', 'BELEGT'
    return 'KEIN_HINWEIS', 'Steigung {:.0f} %'.format(p), 'SWISSALTI3D', 'BELEGT'


def hindernis(fz, seg):
    k = seg.get(fz['kategorie'].lower() + '_hindernis_kat') or 'KEIN_HINWEIS'
    g = seg.get('hindernisse') or ''
    if k == 'BESCHRAENKUNG_BESTAETIGT' and seg.get('_feste_sperre_als_punkt'):
        return 'KEIN_HINWEIS', 'feste Sperre: nur Durchgang am Punkt gesperrt ({})'.format(g[:80]), 'OSM_HINDERNIS', 'BELEGT'
    return k, g[:120] if k != 'KEIN_HINWEIS' else '', 'OSM_HINDERNIS' if g else 'KEINE', 'BELEGT' if g else 'ANNAHME'


def bewerte(fz, seg):
    """-> (kategorie, grundtext, {kriterium: (kat, grund, quelle, stufe)})"""
    k = {'breite': breite(fz, seg), 'hoehe': hoehe(fz, seg), 'gewicht': gewicht(fz, seg),
         'steigung': steigung(fz, seg), 'hindernis': hindernis(fz, seg)}
    kat = max((v[0] for v in k.values()), key=lambda x: RANG.get(x, 1))
    if (seg.get(fz['kategorie'].lower() + '_kat_v7_grund') or '').startswith('R2'):
        kat = 'BESCHRAENKUNG_BESTAETIGT'
        k['freigabe'] = ('BESCHRAENKUNG_BESTAETIGT', seg[fz['kategorie'].lower() + '_kat_v7_grund'][:120], 'FREIGABE', 'BELEGT')
    teile = ['{}: {}'.format(n.capitalize(), v[1]) for n, v in k.items() if v[1] and (v[0] != 'KEIN_HINWEIS' or v[1].startswith('feste Sperre'))]
    return kat, ' | '.join(teile) or 'kein Hinweis (KEINE Freigabe)', k  # feste Sperre: Router sperrt den Punkt (Ziel zu Fuss)
