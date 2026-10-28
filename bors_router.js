/* BORS Router (Web) - 1:1-Portierung des Routing-Kerns und der Routenlogik aus 7_Router_V9_2c.py (QGIS).
   Eingabe: netz.json (Export aus dem echten Router: Graph, Kosten je Profil und Modus, Hindernisse, Abbiegen).
   Gleiche Regeln: validiert zuerst, sonst experimentell (Risikofaktor x2), Alternativpunkt bei gesperrtem Start/Ziel,
   F4-Kandidaten, Halt <= 60 m vor dem Ziel, Dominanz (leichteres Fahrzeug nie langsamer als schwereres). */
(function (root) {
  'use strict';

  class Heap {
    constructor() { this.a = []; }
    get size() { return this.a.length; }
    push(x) { const a = this.a; a.push(x); let i = a.length - 1; while (i > 0) { const p = (i - 1) >> 1; if (a[p][0] <= x[0]) break; a[i] = a[p]; i = p; } a[i] = x; }
    pop() { const a = this.a, top = a[0], last = a.pop(); if (a.length) { let i = 0; const n = a.length; for (;;) { let l = 2 * i + 1, r = l + 1, m = i; if (l < n && a[l][0] < (m === i ? last[0] : a[m][0])) m = l; if (r < n && a[r][0] < (m === i ? last[0] : a[m][0])) m = r; if (m === i) break; a[i] = a[m]; i = m; } a[i] = last; } return top; }
  }

  const TK = (u, a, b) => (u * 32768 + a) * 32768 + b;
  function Netz(D) {
    const N = this;
    N.D = D;
    const nn = D.nodes.length / 2;
    N.x = new Float64Array(nn); N.y = new Float64Array(nn);
    for (let i = 0; i < nn; i++) { N.x[i] = D.nodes[2 * i] / 100; N.y[i] = D.nodes[2 * i + 1] / 100; }
    N.out = Array.from({ length: nn }, () => []);
    N.und = Array.from({ length: nn }, () => []);
    N.feat = D.segs.map((s, f) => {
      const parts = s[0], fw = !!(s[1] & 1), bw = !!(s[1] & 2), cums = [], offs = []; let off = 0;
      parts.forEach((ids, pi) => {
        const cum = [0];
        for (let i = 1; i < ids.length; i++) cum.push(cum[i - 1] + Math.hypot(N.x[ids[i]] - N.x[ids[i - 1]], N.y[ids[i]] - N.y[ids[i - 1]]));
        for (let i = 0; i < ids.length - 1; i++) {
          const L = cum[i + 1] - cum[i];
          if (L <= 1e-9 || ids[i] === ids[i + 1]) continue;
          if (fw) N.out[ids[i]].push([ids[i + 1], f, pi, cum[i], cum[i + 1], L]);
          if (bw) N.out[ids[i + 1]].push([ids[i], f, pi, cum[i + 1], cum[i], L]);
          N.und[ids[i]].push([ids[i + 1], f]); N.und[ids[i + 1]].push([ids[i], f]);
        }
        cums.push(cum); offs.push(off); off += cum[cum.length - 1];
      });
      return { ids: parts, cum: cums, off: offs, L: off, fw, bw };
    });
    // Rasterindex 100 m (jede Kante in allen Zellen ihres Rechtecks)
    N.G = 100; N.grid = new Map();
    N.feat.forEach((F, f) => F.ids.forEach(ids => { for (let i = 0; i < ids.length - 1; i++) {
      const a = ids[i], b = ids[i + 1];
      const x0 = Math.floor(Math.min(N.x[a], N.x[b]) / N.G), x1 = Math.floor(Math.max(N.x[a], N.x[b]) / N.G);
      const y0 = Math.floor(Math.min(N.y[a], N.y[b]) / N.G), y1 = Math.floor(Math.max(N.y[a], N.y[b]) / N.G);
      for (let gx = x0; gx <= x1; gx++) for (let gy = y0; gy <= y1; gy++) { const k = gx * 100000 + gy; let s = N.grid.get(k); if (!s) N.grid.set(k, s = new Set()); s.add(f); }
    } }));
    // Attribute
    const ac = {}; D.attr_cols.forEach((c, i) => ac[c] = i); N.ac = ac;
    N.attr = (f, c) => D.attr[f][ac[c]];
    // Hindernisse und Abbiegen
    N.punkte = new Map(Object.entries(D.punkte).map(([k, v]) => [+k, v]));
    N.abb = {};
    for (const c of Object.keys(D.abb)) {
      const t = { turn: new Map(), kurve: new Map(), ttext: new Map(), ktext: new Map() };
      D.abb[c].turn.forEach(([u, a, b, s, tx]) => { const k = TK(u, a, b); t.turn.set(k, s); t.ttext.set(k, D.texte[tx]); });
      D.abb[c].kurve.forEach(([f, fw, s, tx]) => { t.kurve.set(f * 2 + (fw ? 1 : 0), s); t.ktext.set(f, D.texte[tx]); });
      N.abb[c] = t;
    }
    N.K = D.konst;
  }

  Netz.prototype.lv2rel = function (E, Nn) { return [E - this.D.x0, Nn - this.D.y0]; };

  Netz.prototype.project = function (f, x, y) {
    const F = this.feat[f]; let best = null;
    for (let pi = 0; pi < F.ids.length; pi++) {
      const ids = F.ids[pi], cum = F.cum[pi];
      for (let i = 0; i < ids.length - 1; i++) {
        const ax = this.x[ids[i]], ay = this.y[ids[i]], bx = this.x[ids[i + 1]], by = this.y[ids[i + 1]];
        const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
        if (l2 <= 0) continue;
        const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / l2));
        const px = ax + t * dx, py = ay + t * dy, d = Math.hypot(x - px, y - py);
        if (best === null || d < best[0]) best = [d, pi, i, cum[i] + t * (cum[i + 1] - cum[i]), px, py];
      }
    }
    return best;
  };

  Netz.prototype.nearest = function (x, y, k, maxd) {
    const G = this.G, r = Math.floor(maxd / G) + 1, cx = Math.floor(x / G), cy = Math.floor(y / G), cand = new Set();
    for (let i = cx - r; i <= cx + r; i++) for (let j = cy - r; j <= cy + r; j++) { const s = this.grid.get(i * 100000 + j); if (s) s.forEach(f => cand.add(f)); }
    const ds = []; cand.forEach(f => { const sn = this.project(f, x, y); if (sn && sn[0] <= maxd) ds.push([sn[0], f, sn]); });
    ds.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    return ds.slice(0, k);
  };

  Netz.prototype._anbindung = function (f, snap, start) {
    const [, pi, i, pos] = snap, F = this.feat[f], cum = F.cum[pi], ids = F.ids[pi], r = [];
    if (start) {
      if (F.fw) r.push([ids[i + 1], f, pi, pos, cum[i + 1], Math.abs(cum[i + 1] - pos)]);
      if (F.bw) r.push([ids[i], f, pi, pos, cum[i], Math.abs(pos - cum[i])]);
    } else {
      if (F.fw) r.push([ids[i], [f, pi, cum[i], pos, Math.abs(pos - cum[i])]]);
      if (F.bw) r.push([ids[i + 1], [f, pi, cum[i + 1], pos, Math.abs(cum[i + 1] - pos)]]);
    }
    return r;
  };

  // Dijkstra wie RoutingKern.route. kosten: Float-Array (0 = gesperrt). punkte: Map f -> [[pi,pos,sek|null]]
  Netz.prototype.route = function (sF, sS, tF, tS, kosten, punkte, abb) {
    const S = -1, T = -2, M = 30000;
    const key = (u, fin) => (u + 2) * M + (fin + 1);
    const turn = abb ? abb.turn : new Map(), kurve = abb ? abb.kurve : new Map();
    this.letzte_abbiegen = [];
    const startEdges = this._anbindung(sF, sS, true);
    const intoT = new Map();
    for (const [node, [f, pi, a, b, L]] of this._anbindung(tF, tS, false)) { if (!intoT.has(node)) intoT.set(node, []); intoT.get(node).push([T, f, pi, a, b, L]); }
    if (sF === tF && sS[1] === tS[1]) { const F = this.feat[sF], a = sS[3], b = tS[3]; if ((b >= a && F.fw) || (b <= a && F.bw)) startEdges.push([T, sF, sS[1], a, b, Math.abs(b - a)]); }
    const dist = new Map(), prev = new Map(), pq = new Heap();
    const k0 = key(S, -1); dist.set(k0, 0); pq.push([0, S, -1]);
    let ziel = null;
    while (pq.size) {
      const [d, u, fin] = pq.pop();
      if (u === T) { ziel = [u, fin]; break; }
      const dk = dist.get(key(u, fin)); if (dk !== undefined && d > dk) continue;
      const lists = [u === S ? startEdges : this.out[u], intoT.get(u) || []];
      for (const lst of lists) for (const e of lst) {
        const c = kosten[e[1]];
        if (!c) continue;
        let extra = 0;
        if (fin !== -1 && e[1] !== fin && turn.size) extra += turn.get(TK(u, fin, e[1])) || 0;
        if (e[1] !== fin && kurve.size) extra += kurve.get(e[1] * 2 + (e[4] >= e[3] ? 1 : 0)) || 0;
        const pl = punkte.get(e[1]);
        if (pl) {
          const lo = Math.min(e[3], e[4]), hi = Math.max(e[3], e[4]); let sperre = false;
          for (const [ppi, pos, sek] of pl) {
            if (ppi !== e[2]) continue;
            if (sek === null) { if (lo - 0.01 <= pos && pos <= hi + 0.01) { sperre = true; break; } }
            else if ((lo + 0.01 < pos && pos < hi - 0.01) || Math.abs(pos - e[4]) <= 0.01) extra += sek;
          }
          if (sperre) continue;
        }
        const nd = d + e[5] * c + extra, kk = key(e[0], e[1]);
        const ok_ = dist.get(kk); if (ok_ === undefined || nd < ok_ - 1e-12) { dist.set(kk, nd); prev.set(kk, [u, fin, e]); pq.push([nd, e[0], e[1]]); }
      }
    }
    if (!ziel) { const reached = new Set(); dist.forEach((_, k) => reached.add(Math.floor(k / M) - 2)); this.letzte_erreicht = reached; return null; }
    this.letzte_erreicht = null;
    const weg = []; let v = ziel;
    while (key(v[0], v[1]) !== k0) {
      const [u, fin, e] = prev.get(key(v[0], v[1]));
      weg.push([e[1], e[2], e[3], e[4], e[5]]);
      if (fin !== -1 && e[1] !== fin && turn.has(TK(u, fin, e[1]))) this.letzte_abbiegen.push(TK(u, fin, e[1]));
      v = [u, fin];
    }
    weg.reverse(); this.letzte_abbiegen.reverse();
    return [dist.get(key(ziel[0], ziel[1])), weg];
  };

  Netz.prototype.zusammenfassen = function (weg) {
    const rows = [];
    for (const [f, pi, a, b, L] of weg) {
      if (L <= 1e-9) continue;
      const r = rows[rows.length - 1];
      if (r && r[0] === f && r[1] === pi && Math.abs(r[3] - a) < 1e-6 && (r[3] - r[2]) * (b - a) >= 0) { rows[rows.length - 1] = [f, pi, r[2], b, r[4] + L]; continue; }
      rows.push([f, pi, a, b, L]);
    }
    return rows;
  };

  Netz.prototype.teilgeometrie = function (f, pi, a, b) {
    const ids = this.feat[f].ids[pi], cum = this.feat[f].cum[pi], lo = Math.min(a, b), hi = Math.max(a, b);
    const at = p => { for (let i = 0; i < cum.length - 1; i++) if (cum[i] - 1e-9 <= p && p <= cum[i + 1] + 1e-9) { const t = cum[i + 1] === cum[i] ? 0 : (p - cum[i]) / (cum[i + 1] - cum[i]); return [this.x[ids[i]] + t * (this.x[ids[i + 1]] - this.x[ids[i]]), this.y[ids[i]] + t * (this.y[ids[i + 1]] - this.y[ids[i]])]; } const l = ids[ids.length - 1]; return [this.x[l], this.y[l]]; };
    const out = [at(lo)]; for (let i = 0; i < ids.length; i++) if (lo + 1e-9 < cum[i] && cum[i] < hi - 1e-9) out.push([this.x[ids[i]], this.y[ids[i]]]); out.push(at(hi));
    return b >= a ? out : out.reverse();
  };

  Netz.prototype.ungerichtet_verbunden = function (sF, sS, tF, tS, erlaubt) {
    const f = this.feat[sF], g = this.feat[tF];
    const start = new Set([f.ids[sS[1]][sS[2]], f.ids[sS[1]][sS[2] + 1]]), ziel = new Set([g.ids[tS[1]][tS[2]], g.ids[tS[1]][tS[2] + 1]]);
    for (const s of start) if (ziel.has(s)) return true;
    const seen = new Set(start), stack = [...start];
    while (stack.length) { const u = stack.pop(); for (const [v, fid] of this.und[u]) { if (seen.has(v) || (erlaubt && !erlaubt[fid])) continue; if (ziel.has(v)) return true; seen.add(v); stack.push(v); } }
    return false;
  };

  // ---------------------------------------------------------------- Routenlogik (BorsRouterV7 / V9.2c)
  const URSACHE = {
    KEIN_NETZ_IN_ZIELNAEHE: 'Keine Strasse in Klicknähe (max. 30 m)',
    NETZ_VORHANDEN_ABER_FUER_FAHRZEUG_AUSGESCHLOSSEN: 'Strasse vorhanden, aber für dieses Fahrzeug gesperrt',
    EINBAHNRICHTUNG_VERHINDERT_VERBINDUNG: 'Nur gegen die Einbahnrichtung erreichbar',
    FAHRZEUGBESCHRAENKUNG_TRENNT: 'Beschränkungen (Höhe, Gewicht, Breite, Sperre) trennen Start und Ziel',
    AUSSERHALB_UNTERSUCHUNGSGEBIET: 'Start oder Ziel ausserhalb des Untersuchungsgebiets – keine Aussage',
    UNTERSCHIEDLICHE_NETZKOMPONENTEN: 'Start und Ziel liegen in getrennten Netzteilen',
  };

  function Router(netz) { this.N = netz; this.D = netz.D; }

  Router.prototype.kosten = function (modus, c) { return this.D.kosten[modus[0]][c]; };
  Router.prototype.kat = function (c, f) { return c === 'REF' ? 0 : this.D.kat[c][f]; };
  Router.prototype.punkteFuer = function (c, kosten) {
    const out = new Map();
    this.N.punkte.forEach((pl, f) => { if (!kosten[f]) return; const l = []; for (const [pi, pos, fest] of pl) { if (fest) l.push([pi, pos, null]); else if (c !== 'REF') l.push([pi, pos, this.N.K.OEFFNEN_SEK]); } if (l.length) out.set(f, l); });
    return out;
  };
  Router.prototype.naechste = function (pt, kosten) {
    let any = null, ok = null;
    for (const [d, f, sn] of this.N.nearest(pt[0], pt[1], 80, this.N.K.DIAG_SUCHE_M)) {
      const m = d + this.N.attr(f, 'klick_malus');
      if (!any || m < any[3]) any = [d, f, sn, m];
      if (kosten[f] && (!ok || m < ok[3])) ok = [d, f, sn, m];
    }
    return [any, ok];
  };
  Router.prototype.kandidaten = function (pt, kosten) {
    const o = [];
    for (const [d, f, sn] of this.N.nearest(pt[0], pt[1], 80, this.N.K.F4_MAX_M)) if (kosten[f]) o.push([d + this.N.attr(f, 'klick_malus'), d, f, sn]);
    o.sort((a, b) => a[0] - b[0]);
    return o.slice(0, this.N.K.F4_KANDIDATEN).map(q => [q[1], q[2], q[3]]);
  };
  // Web: Klickpunkt auf die naechste Strasse ziehen (wie ein genauer Klick in QGIS); Tunnel/Autobahn mit Malus
  Router.prototype.snap = function (pt, maxd) {
    let best = null;
    for (const [d, f, sn] of this.N.nearest(pt[0], pt[1], 20, maxd)) { const m = d + this.N.attr(f, 'klick_malus'); if (!best || m < best[0]) best = [m, sn[4], sn[5], d]; }
    return best ? [best[1], best[2], best[3]] : null;
  };
  Router.prototype.ausgrund = function (modus, c, f) { return this.D.texte[this.D.aus[modus[0]][c][f]] || '?'; };

  Router.prototype.routeProfil = function (c, p1, p2, modus) {
    const N = this.N, K = N.K, kosten = this.kosten(modus, c), diag = {}, snaps = [];
    for (const [name, p] of [['start', p1], ['ziel', p2]]) {
      const [any, ok] = this.naechste(p, kosten);
      const gesperrtNaeher = any && ok && !kosten[any[1]] && ok[0] - any[0] > 5;
      if (any && any[0] <= K.MAX_SNAP_M && ok && (ok[0] > K.MAX_SNAP_M || gesperrtNaeher)) {
        diag[name + '_status'] = (name === 'ziel' ? 'ZIEL' : 'START') + '_NICHT_ANFAHRBAR';
        diag[name + '_gesperrt_f'] = any[1]; diag[name + '_gesperrt_grund'] = this.ausgrund(modus, c, any[1]);
        diag[name + '_alt'] = [ok[2][4], ok[2][5]]; diag[name + '_klick'] = [any[2][4], any[2][5]];
        diag[name + '_rest_m'] = Math.hypot(ok[2][4] - any[2][4], ok[2][5] - any[2][5]);
        snaps.push(ok); continue;
      }
      if (!ok || ok[0] > K.MAX_SNAP_M) {
        if (!any || any[0] > K.MAX_SNAP_M) return { code: c, ok: false, ursache: 'KEIN_NETZ_IN_ZIELNAEHE', text: (name === 'start' ? 'Start' : 'Ziel') + ': nächste Strasse ' + (any ? Math.round(any[0]) + ' m' : '> 500 m') + ' entfernt (max. 30 m)', diag };
        return { code: c, ok: false, ursache: 'NETZ_VORHANDEN_ABER_FUER_FAHRZEUG_AUSGESCHLOSSEN', text: (name === 'start' ? 'Start' : 'Ziel') + ': nächste Strasse ist für ' + c + ' gesperrt: ' + this.ausgrund(modus, c, any[1]), diag };
      }
      snaps.push(ok);
    }
    let [[d1, f1, s1], [d2, f2, s2]] = snaps;
    const pkt = this.punkteFuer(c, kosten), abb = N.abb[c];
    let r = N.route(f1, s1, f2, s2, kosten, pkt, abb);
    if (!r && c !== 'REF') {
      const ks = this.kandidaten(p1, kosten), kz = this.kandidaten(p2, kosten), vs = [];
      ks.forEach((a, i) => kz.forEach((b, j) => vs.push([a[0] + b[0], i, j])));
      vs.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
      // Beschleunigung ohne Ergebnisaenderung: eine fehlgeschlagene Suche hat alle von diesem Start erreichbaren Knoten
      // besucht. Liegt kein Zugangsknoten des Zielkandidaten darin, kann es keine Route geben -> Suche ueberspringen.
      const erreicht = new Map();
      erreicht.set(f1 + ':' + s1[1] + ':' + s1[2] + ':' + s1[3], N.letzte_erreicht);
      for (const [, i, j] of vs.slice(0, 24)) {
        const a = ks[i], b = kz[j];
        if (a[1] === f1 && b[1] === f2) continue;
        const sk = a[1] + ':' + a[2][1] + ':' + a[2][2] + ':' + a[2][3], er = erreicht.get(sk);
        if (er && a[1] !== b[1]) { const zi = N._anbindung(b[1], b[2], false).map(q => q[0]); if (!zi.some(n => er.has(n))) continue; }
        const rr = N.route(a[1], a[2], b[1], b[2], kosten, pkt, abb);
        if (!rr) erreicht.set(sk, N.letzte_erreicht);
        if (!rr) continue;
        r = rr; diag.f4 = true;
        for (const [name, alt, neu, pt] of [['start', [d1, f1, s1], a, p1], ['ziel', [d2, f2, s2], b, p2]]) {
          if (neu[1] !== alt[1]) {
            diag[name + '_status'] = (name === 'ziel' ? 'ZIEL' : 'START') + '_NICHT_ANFAHRBAR';
            diag[name + '_gesperrt_f'] = alt[1];
            diag[name + '_gesperrt_grund'] = diag[name + '_gesperrt_grund'] || 'nächster zulässiger Abschnitt ist vom übrigen zulässigen Netz abgeschnitten';
            diag[name + '_alt'] = [neu[2][4], neu[2][5]]; diag[name + '_klick'] = diag[name + '_klick'] || pt;
            diag[name + '_rest_m'] = Math.hypot(neu[2][4] - pt[0], neu[2][5] - pt[1]);
          }
        }
        [d1, f1, s1] = a; [d2, f2, s2] = b; break;
      }
    }
    let abbGenutzt = (N.letzte_abbiegen || []).slice();
    if (r && c !== 'REF') {
      const alt = this.restweg(c, p2, kosten, pkt, abb, f1, s1, r[0]);
      if (alt) { r = alt.r; abbGenutzt = alt.abb; diag.ziel_status = 'ZIEL_ZU_FUSS'; diag.ziel_rest_m = alt.rest; diag.ziel_alt = [alt.sn[4], alt.sn[5]]; diag.ziel_klick = p2; diag.ziel_gesperrt_f = f2; }
    }
    if (!r) {
      let u;
      if (N.ungerichtet_verbunden(f1, s1, f2, s2, kosten)) u = 'EINBAHNRICHTUNG_VERHINDERT_VERBINDUNG';
      else if (N.ungerichtet_verbunden(f1, s1, f2, s2, null)) u = 'FAHRZEUGBESCHRAENKUNG_TRENNT';
      else u = 'UNTERSCHIEDLICHE_NETZKOMPONENTEN';
      if (u !== 'EINBAHNRICHTUNG_VERHINDERT_VERBINDUNG' && (N.attr(f1, 'ausserhalb') || N.attr(f2, 'ausserhalb'))) u = 'AUSSERHALB_UNTERSUCHUNGSGEBIET';
      return { code: c, ok: false, ursache: u, text: URSACHE[u], diag };
    }
    const [sek, weg] = r, rows = []; let fz = 0, laenge = 0;
    for (const [f, pi, a, b, L] of N.zusammenfassen(weg)) {
      const basis = L / (N.attr(f, 'speed') / 3.6);
      let nAuf = 0;
      for (const [ppi, pos, psek] of (pkt.get(f) || [])) if (psek !== null && ppi === pi && ((Math.min(a, b) + 0.01 < pos && pos < Math.max(a, b) - 0.01) || Math.abs(pos - b) <= 0.01)) nAuf++;
      fz += basis + nAuf * K.OEFFNEN_SEK; laenge += L;
      rows.push({ f, pi, a, b, L, kat: this.kat(c, f), pts: N.teilgeometrie(f, pi, a, b), oeffnen: nAuf });
    }
    const out = { code: c, ok: true, laenge_m: laenge, modell_min: sek / 60, fahrzeit_min: fz / 60, rows, diag,
      abbiegen: abbGenutzt.map(k => abb.ttext.get(k)).filter(Boolean) };
    new Set(rows.map(x => x.f)).forEach(f => { const t = abb.ktext.get(f); if (t) out.abbiegen.push(t); });
    if (diag.ziel_status === 'ZIEL_ZU_FUSS') out.ursache = 'ZIEL_ZU_FUSS';
    else if (diag.ziel_status || diag.start_status) out.ursache = diag.ziel_status || diag.start_status;
    return out;
  };

  Router.prototype.restweg = function (c, p2, kosten, pkt, abb, f1, s1, kOrig) {
    const N = this.N; let best = null;
    for (const [d, f, sn] of N.nearest(p2[0], p2[1], 30, N.K.ZUFAHRT_RESTWEG_M)) {
      if (!kosten[f] || this.D.kat[c][f] !== 0 || N.attr(f, 'ist_service')) continue;
      if (sn[0] <= N.K.ZUFAHRT_RESTWEG_M && (!best || sn[0] < best[0])) best = [sn[0], f, sn];
    }
    if (!best) return null;
    const r2 = N.route(f1, s1, best[1], best[2], kosten, pkt, abb);
    if (!r2) return null;
    if (r2[0] + best[0] * N.K.RESTWEG_SEK_PRO_M < kOrig - 1) return { r: r2, sn: best[2], rest: best[0], abb: (N.letzte_abbiegen || []).slice() };
    return null;
  };

  Router.prototype.berechneModus = function (p1, p2, codes, modus) {
    const reihe = ['A', 'B', 'C', 'D'], res = {};
    for (const c of codes) res[c] = this.routeProfil(c, p1, p2, modus);
    for (let i = 0; i < reihe.length; i++) {
      const x = reihe[i]; let rx = res[x];
      if (!rx || !rx.ok || rx.ursache) continue;
      for (const y of reihe.slice(i + 1)) {
        const ry = res[y];
        if (ry && ry.ok && !ry.ursache && !ry.dominanz_von && ry.fahrzeit_min < rx.fahrzeit_min - 0.05) {
          const kx = this.kosten(modus, x);
          const rows = ry.rows.map(r => Object.assign({}, r, { kat: this.kat(x, r.f) }));
          rx = res[x] = Object.assign({}, ry, { code: x, rows, dominanz_von: y, modell_min: rows.reduce((s, r) => s + r.L * kx[r.f], 0) / 60 });
        }
      }
    }
    return res;
  };

  // codes: immer ['REF','A','B','C','D'] (Dominanz braucht alle). modusUi: 'VALIDIERT' | 'EXPERIMENTELL'
  Router.prototype.berechne = function (p1, p2, modusUi) {
    const codes = ['REF', 'A', 'B', 'C', 'D'];
    const res = this.berechneModus(p1, p2, codes, modusUi);
    codes.forEach(c => res[c].modus = modusUi);
    if (modusUi === 'VALIDIERT') {
      const fehl = codes.filter(c => c !== 'REF' && !res[c].ok && !['KEIN_NETZ_IN_ZIELNAEHE', 'AUSSERHALB_UNTERSUCHUNGSGEBIET'].includes(res[c].ursache));
      if (fehl.length) {
        const rx = this.berechneModus(p1, p2, codes, 'EXPERIMENTELL');
        for (const c of fehl) {
          const alt = res[c]; res[c] = rx[c]; res[c].modus = 'EXPERIMENTELL'; res[c].validiert_ergebnis = alt.text || alt.ursache;
          const rr = res[c].rows || [], okI = [];
          rr.forEach((x, i) => { if (x.kat === 0) okI.push(i); });
          if (rr.length && okI.length) {
            let alle = true; for (let i = okI[0]; i <= okI[okI.length - 1]; i++) if (rr[i].kat !== 0) alle = false;
            if (alle) {
              const aM = rr.slice(0, okI[0]).reduce((s, x) => s + x.L, 0), zM = rr.slice(okI[okI.length - 1] + 1).reduce((s, x) => s + x.L, 0);
              res[c].modus = 'VALIDIERT_BIS_ZUFAHRT'; res[c].zufahrt_m = aM + zM; res[c].zufahrt_anfang_m = aM; res[c].zufahrt_ende_m = zM;
            }
          }
        }
      }
    }
    for (const c of codes) {
      const r = res[c];
      if (c !== 'REF' && r.ok && r.modus === 'VALIDIERT' && (r.ursache === 'ZIEL_NICHT_ANFAHRBAR' || r.ursache === 'START_NICHT_ANFAHRBAR')) {
        r.modus = 'VALIDIERT_BIS_ZUFAHRT';
        r.zufahrt_anfang_m = r.diag.start_rest_m || 0; r.zufahrt_ende_m = r.diag.ziel_rest_m || 0;
        r.zufahrt_m = r.zufahrt_anfang_m + r.zufahrt_ende_m; r.zufahrt_luftlinie = true;
      }
      if (r.ok && c !== 'REF') r.unvalidiert_m = r.rows.filter(x => x.kat !== 0).reduce((s, x) => s + x.L, 0);
    }
    return res;
  };

  root.BORS = { Netz, Router, URSACHE };
})(typeof window !== 'undefined' ? window : globalThis);
