/* Unheat Project · maqueta interactiva sin frameworks. Mapa simulado con SVG (en producción: Leaflet). */
(function () {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const pl = (n, a, b) => n + ' ' + (n === 1 ? a : b);
  const fmt = (n, d = 0) => {
    const s = Math.abs(n).toFixed(d); let [i, f] = s.split('.');
    i = i.replace(/\B(?=(\d{3})+(?!\d))/g, '\u202f');
    return (n < 0 ? '-' : '') + i + (f ? ',' + f : '');
  };

  /* ---------- datos de ejemplo ---------- */
  const MOCKS = [
    ['new-empty', 'Nueva escena · vacía'], ['new-swir', 'Nueva escena · con SWIR'], ['new-coord', 'Nueva escena · 3 composiciones + coordenadas'],
    ['new-tif', 'Nueva escena · 3 composiciones + GeoTIFF'], ['new-err', 'Nueva escena · errores'],
    ['load-up', 'Análisis · subida (47 %)'], ['load-an', 'Análisis · indeterminado'],
    ['work-full', 'Espacio · completo, Zona 1 seleccionada'], ['work-nogeo', 'Espacio · sin georreferencia'], ['work-nopob', 'Espacio · sin poblaciones en umbral'],
    ['work-zero', 'Espacio · cero zonas quemadas'], ['work-nofoc', 'Espacio · cero focos activos'], ['work-swir', 'Espacio · solo SWIR'], ['work-many', 'Espacio · 25 zonas'],
    ['fit', 'Modo encaje sobre el mapa'], ['spec', 'Especificación de tokens y capas']
  ];
  const POBS = [['Niebla', 4116, 1.4, 'foco activo', 'alta'], ['Lucena del Puerto', 3297, 4.1, 'superficie quemada', 'media'], ['Bonares', 6110, 6.8, 'superficie quemada', 'vigilancia'], ['Rociana del Condado', 7932, 9.3, 'superficie quemada', 'vigilancia']];
  const FOCI = [[540, 250, 4], [600, 290, 3], [520, 320, 3], [650, 250, 2], [585, 200, 1], [270, 430, 2], [310, 460, 1]];
  const TOT = 13683.5, PX = 413100, REGION = 'Encaje sobre el mapa';
  const CARDS = [
    ['swir', 'SWIR', 'Obligatoria', 'De ella sale la superficie quemada.', 'linear-gradient(135deg,#c4562b,#3d0b14 60%,#c4562b)', 'incendio_swir.jpg', '3,2 MB'],
    ['tc', 'True Color', 'Opcional', 'Descarta humo y nubes; es el fondo más natural.', 'linear-gradient(135deg,#58753f,#25201b 55%,#8a7a48)', 'incendio_truecolor.jpg', '2,9 MB'],
    ['wf', 'Wildfires', 'Opcional', 'Da los focos activos con su nivel y confianza alta.', 'linear-gradient(135deg,#58753f,#e5301d 50%,#ffd21f 60%,#58753f)', 'incendio_wildfires.jpg', '3,0 MB']
  ];
  const TOKENS = ['bg', 'panel', 'panel2', 'line', 'tx', 'mu', 'ac', 'acink', 'warn', 'ok', 'dg', 'nogeo', 'basemap', 'water'];

  /* ---------- estado ---------- */
  const initialTheme = localStorage.getItem('uh-theme') || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  const state = {
    mock: 'work-full', screen: 'work', scen: 'full', comps: null, geoSrc: REGION, theme: initialTheme,
    up: { swir: false, tc: false, wf: false }, locOpen: false, locTab: 'tif', co: { n: '', s: '', e: '', w: '' }, tif: false, errs: false,
    phase: 1, pct: 0, sel: null, kb: null, layers: { burn: true, sev: true, per: true, foc: true }, bg: null,
    view: 'res', capOpen: false, fit: { x: 90, y: 60, w: 860, h: 520, op: 60 }
  };
  let timers = [], drag = null, focusList = false;
  const clearTimers = () => { timers.forEach((t) => { clearTimeout(t); clearInterval(t); }); timers = []; };

  function setMock(id) {
    clearTimers();
    const viewFor = { 'work-nogeo': 'res', 'work-swir': 'res', 'work-nopob': 'pob', 'work-zero': 'zon', 'work-many': 'zon' }[id] || 'res';
    const base = { mock: id, view: viewFor, capOpen: id === 'work-nofoc', sel: null, kb: null, comps: null, bg: null, errs: false };
    if (id.startsWith('new')) {
      const t = { 'new-empty': [0, 0, 0], 'new-swir': [1, 0, 0] }[id] || [1, 1, 1];
      Object.assign(state, base, { screen: 'new', up: { swir: !!t[0], tc: !!t[1], wf: !!t[2] },
        locOpen: ['new-coord', 'new-tif', 'new-err'].includes(id), locTab: id === 'new-coord' || id === 'new-err' ? 'coord' : 'tif',
        co: id === 'new-coord' ? { n: '37.4120', s: '37.2480', e: '-6.6510', w: '-6.9200' } : id === 'new-err' ? { n: '37.2000', s: '37.3000', e: '-6.65', w: '-6.92' } : { n: '', s: '', e: '', w: '' },
        tif: id === 'new-tif', errs: id === 'new-err' });
    } else if (id === 'load-up') Object.assign(state, base, { screen: 'load', phase: 1, pct: 47 });
    else if (id === 'load-an') Object.assign(state, base, { screen: 'load', phase: 2 });
    else if (id === 'fit') Object.assign(state, base, { screen: 'fit', scen: 'nogeo', geoSrc: null, bg: 'swir', fit: { x: 90, y: 60, w: 860, h: 520, op: 60 } });
    else if (id === 'spec') Object.assign(state, base, { screen: 'spec' });
    else {
      const scen = { 'work-full': 'full', 'work-nogeo': 'nogeo', 'work-nopob': 'nopob', 'work-zero': 'zero', 'work-nofoc': 'nofocus', 'work-swir': 'swir', 'work-many': 'many' }[id];
      Object.assign(state, base, { screen: 'work', scen, geoSrc: scen === 'nogeo' ? null : REGION, sel: id === 'work-full' ? 0 : null });
    }
    render();
  }

  function run(next, phase) {
    clearTimers(); Object.assign(state, { screen: 'load', phase, pct: 0, mock: '' }); render();
    const fin = () => timers.push(setTimeout(() => { Object.assign(state, next, { mock: '' }); render(); }, 2400));
    if (phase === 2) return fin();
    const iv = setInterval(() => {
      const p = state.pct + 9;
      if (p >= 100) { clearInterval(iv); state.pct = 100; state.phase = 2; render(); fin(); } else { state.pct = p; render(); }
    }, 130);
    timers.push(iv);
  }

  /* ---------- geometría simulada ---------- */
  function blob(cx, cy, r, s) {
    const p = [];
    for (let i = 0; i < 36; i++) {
      const a = i / 36 * 6.2832, q = r * (1 + .16 * Math.sin(2 * a + s) + .1 * Math.sin(3 * a + s * 2.3) + .05 * Math.sin(5 * a + s * 1.7));
      p.push((cx + q * Math.cos(a)).toFixed(1) + ',' + (cy + q * Math.sin(a) * .8).toFixed(1));
    }
    return 'M' + p.join('L') + 'Z';
  }
  const tri = (x, y, s) => [x + ',' + (y - s), (x + s * .9) + ',' + (y + s * .7), (x - s * .9) + ',' + (y + s * .7)].join(' ');
  function geometry(scen) {
    if (scen === 'zero') return [];
    const out = [];
    if (scen === 'many') {
      const n = 25, ws = [...Array(n)].map((_, i) => 1 / Math.pow(i + 1, 1.15)), sw = ws.reduce((a, b) => a + b, 0);
      for (let i = 0; i < n; i++) {
        const a = i * 2.4, dist = 40 + i * 10, r = 118 / Math.pow(i + 1, .55) + 8, cx = 500 + dist * Math.cos(a) * 1.6, cy = 309 + dist * Math.sin(a);
        out.push({ cx, cy, r, w: ws[i] / sw, d: blob(cx, cy, r, i + 1), dIn: blob(cx + 4, cy - 3, r * .55, i + 4) });
      }
    } else {
      out.push({ cx: 560, cy: 290, r: 175, w: .85, d: blob(560, 290, 175, 1), dIn: blob(575, 280, 96, 4) });
      out.push({ cx: 280, cy: 440, r: 85, w: .15, d: blob(280, 440, 85, 2), dIn: blob(284, 436, 47, 5) });
    }
    return out;
  }

  /* ---------- modelo de la escena ---------- */
  function model() {
    const sc = state.scen, geo = !!state.geoSrc;
    const comps = state.comps || (sc === 'swir' ? ['SWIR'] : ['SWIR', 'True Color', 'Wildfires']);
    const hasTC = comps.includes('True Color'), hasWF = comps.includes('Wildfires');
    const foci = sc === 'nofocus' ? [] : sc === 'zero' ? [[800, 150, 2], [180, 120, 1]] : FOCI;
    const est = !hasWF && foci.length > 0;
    const zones = geometry(sc).map((g, i) => {
      const a = i === 0 ? 58 : i === 1 ? 64 : 40 + ((i * 13) % 35), km = i === 0 ? 1.4 : i === 1 ? 3.2 : 1.4 + i * .8, pct = g.w * 100;
      return { ...g, i, name: 'Zona ' + (i + 1), area: geo ? fmt(TOT * g.w, 1) + ' ha' : fmt(PX * 0.01) + ' ha (est.)', pctT: pct < 1 ? '<1 %' : Math.round(pct) + ' %',
        nf: foci.filter((f) => Math.hypot(f[0] - g.cx, (f[1] - g.cy) / .8) < g.r * .9).length, sevA: a, sevM: 100 - a, near: POBS[i % 4][0] + ', a ' + fmt(km, 1) + ' km' };
    });
    return { sc, geo, comps, hasTC, hasWF, foci, est, zones, nZ: zones.length, nF: foci.length };
  }

  /* ---------- plantillas ---------- */
  const info = (note, label) => '<span class="info"><button class="info__btn" aria-label="' + esc(label) + '">i</button><span class="info__tip" role="tooltip">' + esc(note) + '</span></span>';
  const brand = (sm) => '<div class="brand' + (sm ? ' brand--sm' : '') + '"><span class="brand__mark"></span><span class="brand__name">UNHEAT PROJECT</span></div>';
  const themeBtn = (cls) => '<button class="btn ' + (cls || '') + '" data-act="theme" aria-label="Cambiar tema">' + (state.theme === 'dark' ? '☀ Tema claro' : '☾ Tema oscuro') + '</button>';

  function newHTML() {
    const s = state, bad = s.co.n && s.co.s && parseFloat(s.co.n) < parseFloat(s.co.s);
    const cards = CARDS.map(([k, title, badge, desc, grad, file, size]) => {
      const loaded = s.up[k], req = k === 'swir', err = s.errs && k === 'tc' ? 'No es una imagen válida.' : '';
      return '<div class="card-wrap"><div class="card' + (req ? ' card--req' : '') + (err ? ' card--err' : '') + '" role="button" tabindex="0" data-act="card" data-k="' + k + '">' +
        '<div class="card__head"><span class="card__title">' + title + '</span><span class="tag' + (req ? ' tag--req' : '') + '">' + badge + '</span></div>' +
        '<div class="card__desc">' + desc + '</div>' +
        (loaded ? '<div class="card__file"><div class="card__thumb" style="background:' + grad + '"></div><div class="card__meta"><span>' + file + '</span><span class="muted">' + size + '</span></div><button class="btn btn--ghost" data-act="remove" data-k="' + k + '">Quitar</button></div>'
          : '<div class="card__drop"><span style="font-size:20px;line-height:1">⤒</span><span>Arrastra el JPEG o haz clic</span></div>') +
        '</div>' + (err ? '<div class="field-error"><b>✕</b><span>' + err + '</span></div>' : '') + '</div>';
    }).join('');
    const tab = (k, t) => '<button class="tab" role="tab" aria-selected="' + (s.locTab === k) + '" data-act="tab" data-k="' + k + '">' + t + '</button>';
    const inp = (k, lab) => '<label>' + lab + ' (°)<input data-input="' + k + '" value="' + esc(s.co[k]) + '" inputmode="decimal"' + (bad ? ' class="is-bad"' : '') + '></label>';
    const loc = s.locOpen ? '<div class="loc__body"><div class="tabs" role="tablist">' + tab('tif', 'Archivo GeoTIFF') + tab('coord', 'Coordenadas') + '</div>' +
      (s.locTab === 'tif' ? '<div class="loc__tif"><div class="loc__row"><button class="btn" data-act="tif">Elegir archivo .tif</button><span class="mono muted" style="font-size:12.5px">' + (s.tif ? 'incendio_georef.tif · 4,8 MB' : 'Ningún archivo seleccionado') + '</span></div><div class="muted">Sus coordenadas se leen solas y tienen prioridad sobre las coordenadas escritas.</div></div>'
        : '<div class="loc__coords"><div class="rose"><div></div>' + inp('n', 'Norte') + '<div></div>' + inp('w', 'Oeste') + '<div class="rose__box">escena</div>' + inp('e', 'Este') + '<div></div>' + inp('s', 'Sur') + '<div></div></div>' +
          '<div class="loc__help"><div>WGS84, en grados decimales. Los JPEG no traen coordenadas; sin ellas también se puede analizar y situar la escena en el mapa después.</div><div class="field-error" id="coordError"' + (bad ? '' : ' hidden') + '><b>✕</b><span>Coordenadas incoherentes: el norte no puede ser menor que el sur.</span></div></div></div>') + '</div>' : '';
    return '<main class="new"><div style="position:absolute;top:16px;right:20px">' + themeBtn() + '</div><div class="new__col">' +
      '<header>' + brand() + '<p class="new__tagline">Sube las composiciones Sentinel‑2 de una escena y mira qué ha ardido y dónde sigue habiendo fuego.</p></header>' +
      '<section class="cards" aria-label="Composiciones">' + cards + '</section>' +
      '<section class="loc"><button class="loc__toggle" data-act="loc" aria-expanded="' + s.locOpen + '"><span>Ubicación <span class="muted" style="font-weight:400">(opcional)</span></span><span class="muted">' + (s.locOpen ? '▾' : '▸') + '</span></button>' + loc + '</section>' +
      '<div style="display:flex;flex-direction:column;gap:10px;align-items:flex-start">' +
      (s.errs ? '<div class="server-error" role="alert"><b style="color:var(--dg)">✕</b><span>Las composiciones tienen tamaños distintos (SWIR 2500×1546 px, True Color 1920×1187 px): no se pueden analizar juntas.</span></div>' : '') +
      '<div class="go"><button class="btn btn--primary" data-act="analyze"' + (s.up.swir ? '' : ' disabled') + '>Analizar escena</button>' + (s.up.swir ? '' : '<span class="muted">Falta la composición SWIR: es la única obligatoria.</span>') + '</div></div>' +
      '</div><footer class="new__foot">Copernicus Sentinel‑2 · Poblaciones: GeoNames (CC BY 4.0) · © colaboradores de OpenStreetMap</footer></main>';
  }

  function loadHTML() {
    const up = state.phase === 1;
    return '<main class="load" role="status">' + brand() + '<div class="load__box"><div class="load__title"><span>' + (up ? 'Subiendo composiciones…' : 'Analizando la escena…') + '</span><span class="mono">' + (up ? state.pct + ' %' : '') + '</span></div>' +
      '<div class="bar">' + (up ? '<div class="bar__fill" style="width:' + state.pct + '%"></div>' : '<div class="bar__slide"></div>') + '</div>' +
      (up ? '' : '<div class="muted">Puede tardar en imágenes grandes.</div>') + '</div></main>';
  }

  /* ----- mapa ----- */
  const DEFS = '<defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="#5a2b94" fill-opacity=".6"/><rect width="2.5" height="7" fill="#fff" fill-opacity=".35"/></pattern>' +
    '<pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M50 0H0V50" fill="none" stroke="var(--grid)"/></pattern>' +
    '<filter id="nzG" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.011" numOctaves="4" seed="3"/><feColorMatrix values="0 0 0 0 0.08  0 0 0 0 0.2  0 0 0 0 0.05  2.4 0 0 0 -0.9"/></filter>' +
    '<filter id="nzY" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.006" numOctaves="3" seed="9"/><feColorMatrix values="0 0 0 0 0.72  0 0 0 0 0.6  0 0 0 0 0.3  0 2.6 0 0 -1.15"/></filter>' +
    '<filter id="nzR" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.014" numOctaves="4" seed="5"/><feColorMatrix values="0 0 0 0 0.28  0 0 0 0 0.05  0 0 0 0 0.02  2.4 0 0 0 -0.85"/></filter>' +
    '<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter><filter id="blur2" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>' +
    '<clipPath id="imgclip"><rect width="1000" height="618"/></clipPath></defs>';

  function bgOf(M) {
    const pick = state.bg;
    if (state.screen === 'fit') return 'swir';
    return (pick === 'tc' && M.hasTC) || pick === 'swir' || (pick === 'wf' && M.hasWF) ? pick : (M.hasTC ? 'tc' : 'swir');
  }

  function mapSVG(M) {
    const s = state, fit = s.screen === 'fit', L = s.layers, bg = bgOf(M), geo = M.geo && !fit, f = s.fit;
    const sel = s.sel != null ? M.zones[s.sel] : null;
    const sc = sel ? Math.max(1.3, Math.min(2.8, 330 / (sel.r * .95))) : 1;
    const world = sel && !fit ? 'transform:translate(500px,309px) scale(' + sc + ') translate(' + (-sel.cx) + 'px,' + (-sel.cy) + 'px)' : 'transform:none';
    const imgT = fit ? 'transform:translate(' + f.x + 'px,' + f.y + 'px) scale(' + (f.w / 1000) + ',' + (f.h / 618) + ');opacity:' + (f.op / 100) : 'transform:none';
    const charred = (c, o) => M.zones.map((z) => '<path d="' + z.d + '" fill="' + c + '" fill-opacity="' + o + '"/>').join('');
    let img;
    if (bg === 'swir') img = '<rect width="1000" height="618" fill="#c4562b"/><rect width="1000" height="618" filter="url(#nzR)"/><rect width="1000" height="618" filter="url(#nzY)" opacity=".25"/>' + charred('#3d0b14', .85);
    else {
      img = '<rect width="1000" height="618" fill="#58753f"/><rect width="1000" height="618" filter="url(#nzG)"/><rect width="1000" height="618" filter="url(#nzY)"/>' + charred('#25201b', .62) +
        (bg === 'wf' ? M.foci.map((p) => '<g filter="url(#blur2)"><circle cx="' + p[0] + '" cy="' + p[1] + '" r="' + (6 + p[2] * 4) + '" fill="#e5301d"/><circle cx="' + p[0] + '" cy="' + p[1] + '" r="' + (2 + p[2] * 2) + '" fill="#ffd21f"/></g>').join('') : '') +
        '<g filter="url(#blur)" fill="#fff" fill-opacity=".6"><circle cx="610" cy="190" r="48"/><circle cx="690" cy="150" r="38"/><circle cx="530" cy="130" r="34"/></g>';
    }
    const base = geo ? '<rect class="basemap-fill" x="-2000" y="-2000" width="5000" height="4000"/><path class="bm-water" d="M-300 520C100 470 300 640 560 540S980 380 1300 470"/><path class="bm-road" d="M-300 120C150 160 350 40 640 140S1000 260 1300 180"/><path class="bm-road bm-road--s" d="M200 -200C260 150 160 400 300 800"/><path class="bm-road bm-road--s" d="M760 -200C700 200 880 420 800 800"/><path class="bm-road2" d="M-300 340L1300 300"/>'
      : '<rect class="grid-fill" x="-2000" y="-2000" width="5000" height="4000"/>';
    const order = M.zones.filter((z) => z.i !== s.sel).concat(M.zones.filter((z) => z.i === s.sel));
    const zonesH = fit ? '' : order.map((z) => '<g class="zone' + (z.i === s.sel ? ' is-selected' : '') + '" data-zone="' + z.i + '"><path class="z-fill" d="' + z.d + '"/><path class="z-sev" d="' + z.dIn + '"/><path class="z-casing" d="' + z.d + '"/><path class="z-line" d="' + z.d + '"/><path class="z-hit" d="' + z.d + '"/></g>').join('');
    const lv = [7, 10, 13, 17];
    const fociH = fit ? '' : '<g class="foci">' + M.foci.map((p) => { const pts = tri(p[0], p[1], M.est ? 10 : lv[p[2] - 1]); return '<polygon class="f-casing" points="' + pts + '"/><polygon class="f-main' + (M.est ? ' est' : '') + '" points="' + pts + '"/>'; }).join('') + '</g>';
    const H = (t, x, y, r, cur) => '<circle class="fit-handle" data-drag="' + t + '" cx="' + x + '" cy="' + y + '" r="' + r + '" style="cursor:' + cur + '"/>';
    const fitH = fit ? '<rect class="fit-frame" x="' + f.x + '" y="' + f.y + '" width="' + f.w + '" height="' + f.h + '"/>' + H('nw', f.x, f.y, 10, 'nwse-resize') + H('ne', f.x + f.w, f.y, 10, 'nesw-resize') + H('sw', f.x, f.y + f.h, 10, 'nesw-resize') + H('se', f.x + f.w, f.y + f.h, 10, 'nwse-resize') + H('c', f.x + f.w / 2, f.y + f.h / 2, 16, 'move') +
      '<path d="M' + (f.x + f.w / 2 - 8) + ' ' + (f.y + f.h / 2) + 'h16M' + (f.x + f.w / 2) + ' ' + (f.y + f.h / 2 - 8) + 'v16" stroke="var(--acink)" stroke-width="2.5" fill="none" pointer-events="none"/>' : '';
    const cls = 'map__svg' + (L.burn ? '' : ' no-burn') + (L.sev ? '' : ' no-sev') + (L.per ? '' : ' no-per') + (L.foc ? '' : ' no-foc');
    return '<svg class="' + cls + '" viewBox="-250 -100 1500 818" data-map>' + DEFS + '<g class="world" style="' + world + '"><rect class="nogeo-fill" x="-2000" y="-2000" width="5000" height="4000"/>' + base +
      '<g style="' + imgT + '"><rect width="1000" height="618" fill="#000" opacity=".35" transform="translate(6 8)"/><g clip-path="url(#imgclip)">' + img + '</g><rect class="img-frame" width="1000" height="618"/></g>' + zonesH + fociH + fitH + '</g></svg>';
  }

  function capPanel(M) {
    const s = state, L = s.layers, bg = bgOf(M), z0 = M.nZ === 0;
    const bgs = [['tc', 'True Color', M.hasTC], ['swir', 'SWIR', true], ['wf', 'Wildfires', M.hasWF]].filter((b) => b[2])
      .map((b) => '<button role="radio" aria-checked="' + (bg === b[0]) + '" data-act="bg" data-k="' + b[0] + '">' + b[1] + '</button>').join('');
    const lv = [7, 10, 13, 17].map((v, i) => '<svg width="' + (8 + i * 3) + '" height="' + (8 + i * 3) + '" viewBox="-12 -12 24 24"><polygon points="' + tri(0, 0, 10) + '" fill="var(--foc)" stroke="var(--tx)" stroke-width="1.6"/></svg>').join('');
    const row = (k, label, off, reason, sw) => '<div class="layer' + (off ? ' is-off' : '') + '"><div class="layer__row"><button class="switch" role="switch" aria-checked="' + (L[k] && !off) + '" aria-label="' + label + '"' + (off ? ' disabled' : '') + ' data-act="layer" data-k="' + k + '"></button><span class="layer__name">' + label + '</span>' + sw + '</div>' +
      (k === 'foc' ? '<div class="layer__note">Niveles 1–4 · hueco discontinuo: estimado desde la SWIR</div>' : '') + (off ? '<div class="layer__note">' + reason + '</div>' : '') + '</div>';
    const nz = 'No hay superficie quemada en esta escena.';
    return '<section class="float" aria-label="Fondo y capas"><div class="float__head"><span>Fondo y capas</span><button class="float__close" data-act="cap" aria-label="Cerrar">✕</button></div><div class="float__body">' +
      '<div><span class="float__label">Fondo</span><div class="seg" role="radiogroup">' + bgs + '</div></div><div><span class="float__label">Capas</span>' +
      row('burn', 'Superficie quemada', z0, nz, '<span class="sw-burn"></span>') + row('sev', 'Severidad relativa', z0, nz, '<span class="sw-sev"><i></i><i></i></span>') + row('per', 'Perímetro', z0, nz, '<span class="sw-per"></span>') +
      row('foc', M.est ? 'Focos activos (estimados)' : 'Focos activos', M.nF === 0, 'No se han detectado focos activos.', '<span class="sw-foc">' + lv + '<svg width="16" height="16" viewBox="-12 -12 24 24"><polygon points="0,-10 9,7 -9,7" fill="none" stroke="var(--foc)" stroke-width="2.2" stroke-dasharray="4 3"/></svg></span>') + '</div></div></section>';
  }

  function fitPanel() {
    return '<section class="fit-panel"><h2>MODO ENCAJE</h2><p>Arrastra el punto central para mover la imagen y las esquinas para estirarla, hasta que ríos y carreteras coincidan con el mapa.</p>' +
      '<label><span>Opacidad de la imagen SWIR <b class="mono" style="color:var(--tx)" id="opv">' + state.fit.op + ' %</b></span><input type="range" min="10" max="100" value="' + state.fit.op + '" data-input="op"></label>' +
      '<div class="fit-panel__btns"><button class="btn btn--primary" data-act="fitdone">Listo</button><button class="btn" data-act="fitcancel">Cancelar</button></div></section>';
  }

  /* ----- columna derecha ----- */
  function sideHTML(M) {
    const s = state, geo = M.geo, z0 = M.nZ === 0, vw = (s.view === 'pob' && !geo) ? 'res' : s.view;
    const nPobs = geo && M.sc !== 'nopob' ? POBS.length : 0;
    const tabs = [['res', 'Resumen', ''], ['zon', 'Zonas', M.nZ || ''], geo ? ['pob', 'Poblaciones', nPobs || ''] : null].filter(Boolean)
      .map((t) => '<button role="tab" aria-selected="' + (vw === t[0]) + '" data-act="view" data-k="' + t[0] + '">' + t[1] + ' <small>' + t[2] + '</small></button>').join('');
    let body = '';
    if (vw === 'res') {
      const tot = z0 ? (geo ? '0 ha' : '0 px') : geo ? fmt(TOT, 1) + ' ha' : fmt(PX * 0.01) + ' ha (est.)';
      const headline = pl(M.nZ, 'zona quemada', 'zonas quemadas') + ' · ' + (geo ? (z0 ? '0 ha' : fmt(Math.round(TOT)) + ' ha') : tot) + ' · ' + pl(M.nF, 'foco activo', 'focos activos');
      const prov = geo ? 'Escala: ' + s.geoSrc.toLowerCase() + ' · 18,2 m/px' : 'Sin escala: cifras en píxeles';
      const noScale = 'Sin georreferencia no hay escala. Sitúa la escena en el mapa o añade un GeoTIFF para obtenerla.';
      const fact = (label, val, na, note) => '<div class="fact' + (na ? ' is-na' : '') + '"><div class="fact__head"><span>' + label + '</span>' + info(note, 'Origen de la cifra: ' + label) + '</div>' + (na ? '<div class="fact__na">no disponible</div>' : '<div class="fact__val">' + val + '</div>') + '</div>';
      const facts = [
        fact('Superficie quemada', tot, false, geo ? 'Suma del área de todas las zonas, medida sobre la composición SWIR y convertida con la escala de la georreferencia.' : 'Suma del área de todas las zonas, medida sobre la SWIR. Superficie estimada asumiendo la resolución de 10 m/px de Sentinel-2 (0,01 ha/px) al carecer de escala.'),
        fact('Zonas', pl(M.nZ, 'zona quemada', 'zonas quemadas'), false, 'Superficies quemadas separadas entre sí, ordenadas de mayor a menor.'),
        fact('Focos activos', pl(M.nF, 'foco activo', 'focos activos'), false, M.est ? 'Estimados desde la SWIR: no tienen nivel de intensidad.' : 'Fuego ardiendo en el momento de la imagen, con su nivel 1–4 según la composición Wildfires.'),
        fact('Longitud del perímetro', z0 ? '0 km' : '96,4 km (tolerancia 40 m)', !geo, noScale + ' Necesaria para convertir el contorno a kilómetros.'),
        fact('Dentro del perímetro frente a quemado', z0 ? '0 ha frente a 0 ha' : '14 120,6 ha frente a 13 683,5 ha', !geo, geo ? 'La diferencia son islas sin quemar dentro del perímetro.' : noScale)
      ].join('');
      const conf = (label, hi, why) => '<div class="conf"><span>Confianza · ' + label + '</span><span class="conf__r"><span class="tag ' + (hi ? 'tag--ok' : 'tag--baja') + '">' + (hi ? '✓ alta' : '▼ baja') + '</span>' + info(why, 'Motivo de la confianza') + '</span></div>';
      const confs = conf('Superficie quemada', M.hasTC, M.hasTC ? 'Con la True Color se descartan humo y nubes al delimitar lo quemado.' : 'Sin la composición True Color no se pueden descartar humo ni nubes. Añade la True Color para mejorarla.') +
        conf('Focos activos', M.hasWF, M.hasWF ? 'La composición Wildfires da los focos con su nivel de intensidad.' : 'Sin la composición Wildfires, los focos se estiman desde la SWIR y puede faltar o sobrar alguno. Añade la Wildfires para mejorarla.');
      const av = []; if (M.hasWF && M.sc === 'full' && M.nF) av.push('La composición Wildfires marca nubes en el 3 % de la escena; bajo ellas se han buscado focos con la SWIR (confianza baja).');
      if (M.est) av.push('Sin la composición Wildfires, los focos se muestran como estimados desde la SWIR.');
      body = '<div class="res"><h2>' + headline + '</h2><div class="res__prov' + (geo ? '' : ' is-warn') + '">' + prov + '</div>' +
        (av.length ? '<div class="notice">' + av.map((a) => '<div>' + a + '</div>').join('') + '</div>' : '') +
        (geo ? '' : '<div class="geo-note"><div>Las cifras están en píxeles. Sitúa la escena en el mapa para obtener hectáreas y poblaciones.</div><button class="btn btn--primary" style="align-self:flex-start" data-act="enterfit">Situar en el mapa</button></div>') +
        '<div class="rows">' + facts + confs + '</div></div>';
    } else if (vw === 'zon') {
      const zf = (label, val, na, note) => '<div class="zfield' + (na ? ' is-na' : '') + '"><div class="zfield__head"><span>' + label + '</span>' + info(note, 'Origen: ' + label) + '</div>' + (na ? '<div class="zfield__na">no disponible</div>' : '<div class="zfield__val">' + val + '</div>') + '</div>';
      body = (z0 ? '<div class="empty">No se ha detectado superficie quemada en esta escena.</div>' : '') +
        '<div role="listbox" tabindex="0" aria-label="Zonas quemadas" data-list>' + M.zones.map((z) => {
          const on = s.sel === z.i, kb = s.kb === z.i && !on;
          return '<div role="option" class="zrow' + (on ? ' is-selected' : '') + (kb ? ' is-kb' : '') + '" aria-selected="' + on + '" data-act="zone" data-k="' + z.i + '"><div class="zrow__head"><b>' + z.name + '</b><span>' + z.area + '</span></div><div class="zrow__sub">' + z.pctT + ' del total · ' + pl(z.nf, 'foco activo', 'focos activos') + '</div>' +
            (on ? '<div class="zdetail"><div class="zgrid">' + zf('Área', z.area, false, geo ? 'Área de esta zona, medida sobre la SWIR y convertida a hectáreas.' : 'Área en píxeles: sin georreferencia no hay escala.') + zf('Parte del total', z.pctT, false, 'Proporción del área de esta zona respecto a la superficie quemada de la escena.') +
              zf('Focos activos', String(z.nf), false, 'Focos cuyo punto cae dentro del perímetro de esta zona.') + zf('Población más cercana', z.near, !geo, geo ? 'Calculada solo por distancia desde el perímetro de la zona.' : 'Sin georreferencia no hay distancias.') + '</div>' +
              '<div class="sev"><div class="float__label">Severidad relativa</div><div class="sev__bar"><div class="sev__a" style="width:' + z.sevA + '%"></div><div class="sev__m" style="width:' + z.sevM + '%"></div></div><div class="sev__labels"><span>' + z.sevA + ' % afectado</span><span>' + z.sevM + ' % muy afectado</span></div><small>Relativa a esta escena; no se compara con otros incendios.</small></div></div>' : '') + '</div>';
        }).join('') + '</div>';
    } else {
      const AL = { alta: ['◆', 'Alta'], media: ['■', 'Media'], vigilancia: ['○', 'Vigilancia'] };
      const list = geo && M.sc !== 'nopob' ? POBS : [];
      body = (list.length ? '' : '<div class="empty">No hay poblaciones del conjunto de datos dentro de los umbrales de alerta.</div>') +
        list.map((p) => '<div class="prow"><div class="prow__head"><b>' + p[0] + '</b><span class="tag tag--' + p[4] + '">' + AL[p[4]][0] + ' ' + AL[p[4]][1] + '</span></div><div class="prow__hab">' + fmt(p[1]) + ' habitantes</div><div class="prow__dist num">' + fmt(p[2], 1) + ' km de ' + (p[3] === 'foco activo' ? 'un foco activo' : 'la superficie quemada') + '</div></div>').join('') +
        '<div class="criteria">Alta: dentro del perímetro o a menos de 2 km de un foco · Media: menos de 5 km · Vigilancia: menos de 10 km. Solo por distancia: no modela humo ni propagación. Poblaciones: GeoNames, CC BY 4.0.</div>';
    }
    return '<aside class="side" aria-label="Resultados"><div class="side__tabs" role="tablist">' + tabs + '</div><div class="side__body">' + body + '</div></aside>';
  }

  function workHTML() {
    const s = state, M = model(), fit = s.screen === 'fit', geo = M.geo && !fit;
    const chips = ['<span class="chip chip--tx">2500×1546 px</span>', '<span class="chip">' + M.comps.join(' · ') + '</span>',
      fit ? '<span class="chip chip--ac">Encaje en curso</span>' : geo ? '<span class="chip chip--ac">⌖ ' + s.geoSrc + ' · 18,2 m/px</span>' : '<span class="chip chip--warn">⌖ Sin georreferencia</span>'].join('');
    const sr = 'Se han detectado ' + pl(M.nZ, 'zona quemada', 'zonas quemadas') + ' y ' + pl(M.nF, 'foco activo', 'focos activos') + '. Confianza ' + (M.hasTC ? 'alta' : 'baja') + ' en la superficie quemada y ' + (M.hasWF ? 'alta' : 'baja') + ' en los focos activos.';
    return '<header class="top">' + brand(true) + '<div class="chips">' + chips + '</div>' + themeBtn() + '<button class="btn btn--outline" data-act="newscene">Nueva escena</button></header>' +
      '<div class="work"><div class="map" data-mapbox><div data-maphost>' + mapSVG(M) + '</div>' +
      (geo ? '<div class="map__attr">© colaboradores de OpenStreetMap</div>' : '<div class="map__note">Coordenadas de píxel · sin mapa base</div>') +
      (M.nZ === 0 && !fit ? '<div class="map__empty">Mapa limpio: no se ha detectado superficie quemada.</div>' : '') +
      (fit ? fitPanel() : (s.capOpen ? capPanel(M) : '<button class="float-btn" data-act="cap">≋ Fondo y capas</button>')) +
      '<div class="sr-only" aria-live="polite">' + sr + '</div></div>' + (fit ? '' : sideHTML(M)) + '</div>';
  }

  function specHTML() {
    const probe = (t) => { const e = document.createElement('div'); e.setAttribute('data-theme', t); document.body.appendChild(e); const cs = getComputedStyle(e); const o = {}; TOKENS.forEach((k) => (o[k] = cs.getPropertyValue('--' + k).trim())); e.remove(); return o; };
    const D = probe('dark'), Lt = probe('light');
    const tok = TOKENS.map((k) => '<div class="spec__tok"><span>--' + k + '</span><span><i style="background:' + D[k] + '"></i>' + D[k] + '</span><span><i style="background:' + Lt[k] + '"></i>' + Lt[k] + '</span></div>').join('');
    const swatch = (inner) => '<svg width="56" height="30" viewBox="0 0 56 30"><rect width="56" height="30" rx="3" fill="#58753f"/><rect x="28" width="28" height="30" fill="#c4562b"/>' + inner + '</svg>';
    const blobP = (extra, st) => '<path d="M6 24C4 8 22 2 30 8S50 18 48 26Z" style="' + st + '"/>' + extra;
    const arc = (c, w) => '<path d="M6 24C4 8 22 2 30 8S50 18 48 26" fill="none" stroke="' + c + '" stroke-width="' + w + '"/>';
    const lay = [
      ['Superficie quemada', 'relleno #c1a6f0 · opacidad .30 · hover .45 · seleccionada .50', blobP('', 'fill:#c1a6f0;fill-opacity:.3')],
      ['Severidad: muy afectado', 'trama 45° #5a2b94 .60 + líneas #fff .35 · (afectado = relleno lila)', blobP('', 'fill:#5a2b94;fill-opacity:.6')],
      ['Perímetro · normal', 'trazo #fff 2px sobre contorno negro .8 de 4,5px', arc('#fff', 2.5)],
      ['Perímetro · hover', 'trazo #00e5ff 3,5px sobre negro 6px', arc('#00e5ff', 3)],
      ['Perímetro · seleccionada', 'trazo #ffe600 4px sobre negro 8px', arc('#ffe600', 4)],
      ['Foco nivel 1 · 2 · 3 · 4', 'triángulo #ff2bd6, trazo #fff 2px; tamaño 7 · 10 · 13 · 17 u', [0, 1, 2, 3].map((k) => '<polygon points="' + tri(10 + k * 13, 16, 4 + k * 1.2) + '" fill="#ff2bd6" stroke="#fff" stroke-width="1.5"/>').join('')],
      ['Foco estimado (SWIR)', 'triángulo hueco, trazo #ff2bd6 2,5px discontinuo 4 3, sin nivel', '<polygon points="28,6 38,24 18,24" fill="none" stroke="#ff2bd6" stroke-width="2.5" stroke-dasharray="4 3"/>']
    ].map((l) => '<div class="spec__layer">' + swatch(l[2]) + '<div><b>' + l[0] + '</b><br><small>' + l[1] + '</small></div></div>').join('');
    return '<main class="spec"><div class="spec__head"><h1>Especificación de tokens y capas</h1>' + themeBtn() + '</div><div class="spec__cols"><div><h3>Colores · oscuro / claro</h3>' + tok +
      '<div class="spec__note">--f: Segoe UI, Helvetica Neue, Helvetica, Arial (sistema)<br>--m: ui-monospace, Consolas, monospace · cifras tabulares<br>espaciado: 4 · 8 · 12 · 16 · 24 · 32 px · radios: 2 · 3 · 4 px</div></div>' +
      '<div><h3>Capas del mapa (iguales en ambos temas)</h3>' + lay + '<h3 style="margin-top:16px">Etiquetas</h3><div class="spec__tags"><span class="tag tag--alta">◆ Alta</span><span class="tag tag--media">■ Media</span><span class="tag tag--vigilancia">○ Vigilancia</span><span class="tag tag--ok">✓ alta</span><span class="tag tag--baja">▼ baja</span></div></div></div></main>';
  }

  /* ---------- render ---------- */
  function render() {
    document.documentElement.setAttribute('data-theme', state.theme);
    const app = $('#app'), side = $('.side__body'), top = side ? side.scrollTop : 0, sc = state.screen;
    const keep = $('#app .new') ? $('#app .new').scrollTop : 0;
    app.innerHTML = sc === 'new' ? newHTML() : sc === 'load' ? loadHTML() : sc === 'spec' ? specHTML() : workHTML();
    const ns = $('.side__body'); if (ns) ns.scrollTop = top;
    const nn = $('#app .new'); if (nn) nn.scrollTop = keep;
    if (focusList) { const l = $('[data-list]'); if (l) l.focus(); }
    const sel = $('#mock'); if (sel.value !== state.mock) sel.value = state.mock;
  }
  function refreshMap() { const h = $('[data-maphost]'); if (h) h.innerHTML = mapSVG(model()); }

  /* ---------- acciones ---------- */
  const actions = {
    theme() { state.theme = state.theme === 'dark' ? 'light' : 'dark'; localStorage.setItem('uh-theme', state.theme); render(); },
    card(el) { state.up[el.dataset.k] = true; render(); },
    remove(el) { state.up[el.dataset.k] = false; render(); },
    loc() { state.locOpen = !state.locOpen; render(); },
    tab(el) { state.locTab = el.dataset.k; render(); },
    tif() { state.tif = true; render(); },
    analyze() {
      const s = state, hasLoc = s.locOpen && ((s.locTab === 'tif' && s.tif) || (s.locTab === 'coord' && s.co.n && s.co.s && s.co.e && s.co.w));
      run({ view: 'res', screen: 'work', scen: hasLoc ? 'full' : 'nogeo', comps: ['SWIR'].concat(s.up.tc ? ['True Color'] : [], s.up.wf ? ['Wildfires'] : []),
        geoSrc: hasLoc ? (s.locTab === 'tif' ? 'GeoTIFF' : 'Coordenadas manuales') : null, sel: null, bg: null, capOpen: false }, 1);
    },
    newscene() { setMock('new-empty'); },
    view(el) { state.view = el.dataset.k; render(); },
    zone(el) { state.sel = +el.dataset.k; state.kb = state.sel; render(); },
    cap() { state.capOpen = !state.capOpen; render(); },
    bg(el) { state.bg = el.dataset.k; render(); },
    layer(el) { const k = el.dataset.k; state.layers[k] = !state.layers[k]; render(); },
    enterfit() { Object.assign(state, { screen: 'fit', bg: 'swir', fit: { x: 90, y: 60, w: 860, h: 520, op: 60 } }); render(); },
    fitdone() { run({ view: 'res', screen: 'work', scen: state.scen === 'nogeo' ? 'full' : state.scen, geoSrc: REGION, bg: null }, 2); },
    fitcancel() { Object.assign(state, { screen: 'work', bg: null }); render(); }
  };
  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-act]');
    if (el) { focusList = false; actions[el.dataset.act](el); return; }
    if (e.target.closest('[data-map]') && state.sel != null) { state.sel = null; render(); }
  });
  /* clic en una zona del mapa: selecciona, abre Zonas y centra */
  document.addEventListener('click', (e) => {
    const z = e.target.closest('.zone'); if (!z) return;
    e.stopPropagation(); state.sel = +z.dataset.zone; state.kb = state.sel; state.view = 'zon'; render();
  }, true);
  document.addEventListener('keydown', (e) => {
    const card = e.target.closest('[data-act="card"]');
    if (card && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); actions.card(card); return; }
    if (!e.target.closest('[data-list]')) return;
    const n = model().nZ; if (!n) return; const cur = state.kb == null ? -1 : state.kb; focusList = true;
    if (e.key === 'ArrowDown') { e.preventDefault(); state.kb = Math.min(n - 1, cur + 1); render(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); state.kb = Math.max(0, cur - 1); render(); }
    else if (e.key === 'Enter' && cur >= 0) { e.preventDefault(); state.sel = cur; render(); }
    else if (e.key === 'Escape') { state.sel = null; render(); }
  });
  document.addEventListener('input', (e) => {
    const k = e.target.dataset && e.target.dataset.input; if (!k) return;
    if (k === 'op') { state.fit.op = +e.target.value; $('#opv').textContent = state.fit.op + ' %'; refreshMap(); return; }
    state.co[k] = e.target.value;
    const bad = state.co.n && state.co.s && parseFloat(state.co.n) < parseFloat(state.co.s), err = $('#coordError');
    if (err) err.hidden = !bad; document.querySelectorAll('.rose input').forEach((i) => i.classList.toggle('is-bad', !!bad));
  });
  $('#mock').innerHTML = MOCKS.map((m) => '<option value="' + m[0] + '">' + m[1] + '</option>').join('');
  $('#mock').addEventListener('change', (e) => setMock(e.target.value));

  /* tooltip y resalte de zonas (sin re-render) */
  const tip = $('#tip');
  document.addEventListener('mouseover', (e) => {
    const z = e.target.closest('.zone'); if (!z) return;
    z.classList.add('is-hover');
    const Z = model().zones[+z.dataset.zone]; tip.textContent = Z.name + ' · ' + Z.area + ' · ' + Z.pctT; tip.hidden = false;
  });
  document.addEventListener('mousemove', (e) => { if (!tip.hidden) { tip.style.left = e.clientX + 14 + 'px'; tip.style.top = e.clientY + 14 + 'px'; } });
  document.addEventListener('mouseout', (e) => { const z = e.target.closest('.zone'); if (z && !z.contains(e.relatedTarget)) { z.classList.remove('is-hover'); tip.hidden = true; } });

  /* arrastre de asas del modo encaje */
  document.addEventListener('pointerdown', (e) => {
    const h = e.target.closest('[data-drag]'); if (!h) return;
    e.preventDefault(); drag = { t: h.dataset.drag, x: e.clientX, y: e.clientY };
  });
  window.addEventListener('pointermove', (e) => {
    if (!drag) return; const box = $('[data-mapbox]'); if (!box) return;
    const k = Math.min(box.clientWidth / 1500, box.clientHeight / 818), dx = (e.clientX - drag.x) / k, dy = (e.clientY - drag.y) / k; drag.x = e.clientX; drag.y = e.clientY;
    const f = state.fit;
    if (drag.t === 'c') { f.x += dx; f.y += dy; } else {
      if (drag.t.includes('w')) { f.x += dx; f.w -= dx; } else f.w += dx;
      if (drag.t.includes('n')) { f.y += dy; f.h -= dy; } else f.h += dy;
      f.w = Math.max(200, f.w); f.h = Math.max(150, f.h);
    }
    refreshMap();
  });
  window.addEventListener('pointerup', () => { drag = null; });

  setMock('work-full');
})();
