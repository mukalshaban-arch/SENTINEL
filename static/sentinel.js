/* =============================================================
   SENTINEL — Shared Client Library v2.1
   All icons defined FIRST to avoid temporal dead zone errors.
   ============================================================= */

/* ══════════════════════════════════════════════════════════════
   ICONS — must be declared before any function that uses them
   ══════════════════════════════════════════════════════════════ */
const iGrid   = `<svg viewBox="0 0 16 16" fill="none"><rect x="1" y="1" width="6" height="6" stroke="currentColor" stroke-width="1.3"/><rect x="9" y="1" width="6" height="6" stroke="currentColor" stroke-width="1.3"/><rect x="1" y="9" width="6" height="6" stroke="currentColor" stroke-width="1.3"/><rect x="9" y="9" width="6" height="6" stroke="currentColor" stroke-width="1.3"/></svg>`;
const iUsers  = `<svg viewBox="0 0 16 16" fill="none"><circle cx="6" cy="5" r="2.5" stroke="currentColor" stroke-width="1.3"/><path d="M1 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.3"/><circle cx="12" cy="5" r="2" stroke="currentColor" stroke-width="1.3"/><path d="M12 9c1.66 0 3 1.34 3 3" stroke="currentColor" stroke-width="1.3"/></svg>`;
const iGroup  = `<svg viewBox="0 0 16 16" fill="none"><polygon points="8,2 14,5.5 14,10.5 8,14 2,10.5 2,5.5" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.2"/></svg>`;
const iMap    = `<svg viewBox="0 0 16 16" fill="none"><path d="M8 2C5.79 2 4 3.79 4 6c0 3 4 8 4 8s4-5 4-8c0-2.21-1.79-4-4-4z" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="6" r="1.5" stroke="currentColor" stroke-width="1.2"/></svg>`;
const iDoc    = `<svg viewBox="0 0 16 16" fill="none"><path d="M3 2h7l3 3v9H3V2z" stroke="currentColor" stroke-width="1.3"/><path d="M10 2v3h3" stroke="currentColor" stroke-width="1.3"/><line x1="5" y1="7" x2="11" y2="7" stroke="currentColor" stroke-width="1.2"/><line x1="5" y1="10" x2="11" y2="10" stroke="currentColor" stroke-width="1.2"/></svg>`;
const iHome   = `<svg viewBox="0 0 16 16" fill="none"><path d="M2 7l6-5 6 5v7H2V7z" stroke="currentColor" stroke-width="1.3"/><rect x="6" y="10" width="4" height="4" stroke="currentColor" stroke-width="1.2"/></svg>`;
const iShield = `<svg viewBox="0 0 16 16" fill="none"><path d="M8 2l5 2v4c0 3-2.5 5.5-5 6.5C5.5 13.5 3 11 3 8V4l5-2z" stroke="currentColor" stroke-width="1.3"/><path d="M5.5 8l2 2 3-3" stroke="currentColor" stroke-width="1.3"/></svg>`;
const iPlus   = `<svg viewBox="0 0 16 16" fill="none"><line x1="8" y1="2" x2="8" y2="14" stroke="currentColor" stroke-width="1.5"/><line x1="2" y1="8" x2="14" y2="8" stroke="currentColor" stroke-width="1.5"/></svg>`;
const iEdit   = `<svg viewBox="0 0 16 16" fill="none"><path d="M11 2l3 3L5 14H2v-3L11 2z" stroke="currentColor" stroke-width="1.3"/></svg>`;
const iTrash  = `<svg viewBox="0 0 16 16" fill="none"><polyline points="3,4 13,4" stroke="currentColor" stroke-width="1.3"/><path d="M5 4V3h6v1" stroke="currentColor" stroke-width="1.3"/><path d="M4 4l1 10h6l1-10" stroke="currentColor" stroke-width="1.3"/></svg>`;
const iSearch = `<svg viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4.5" stroke="currentColor" stroke-width="1.3"/><line x1="10.5" y1="10.5" x2="14" y2="14" stroke="currentColor" stroke-width="1.5"/></svg>`;
const iEye    = `<svg viewBox="0 0 16 16" fill="none"><path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.2"/></svg>`;
const iClose  = `<svg viewBox="0 0 16 16" fill="none"><line x1="3" y1="3" x2="13" y2="13" stroke="currentColor" stroke-width="1.5"/><line x1="13" y1="3" x2="3" y2="13" stroke="currentColor" stroke-width="1.5"/></svg>`;
const iCam    = `<svg viewBox="0 0 16 16" fill="none"><rect x="1" y="4" width="14" height="10" rx="1" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="9" r="2.5" stroke="currentColor" stroke-width="1.2"/><path d="M5 4l1-2h4l1 2" stroke="currentColor" stroke-width="1.3"/></svg>`;
const iPrint  = `<svg viewBox="0 0 16 16" fill="none"><rect x="3" y="6" width="10" height="7" stroke="currentColor" stroke-width="1.3"/><path d="M5 6V2h6v4" stroke="currentColor" stroke-width="1.3"/><rect x="5" y="9" width="6" height="2" stroke="currentColor" stroke-width="1"/></svg>`;
const iDown   = `<svg viewBox="0 0 16 16" fill="none"><path d="M3 6l5 5 5-5" stroke="currentColor" stroke-width="1.5"/></svg>`;
const iCheck  = `<svg viewBox="0 0 16 16" fill="none"><path d="M3 8l4 4 6-6" stroke="currentColor" stroke-width="1.5"/></svg>`;
const iUser   = `<svg viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="3" stroke="currentColor" stroke-width="1.3"/><path d="M2 14c0-3.31 2.69-6 6-6s6 2.69 6 6" stroke="currentColor" stroke-width="1.3"/></svg>`;
const iKey    = `<svg viewBox="0 0 16 16" fill="none"><circle cx="6" cy="8" r="4" stroke="currentColor" stroke-width="1.3"/><line x1="9.5" y1="8" x2="15" y2="8" stroke="currentColor" stroke-width="1.3"/><line x1="13" y1="8" x2="13" y2="11" stroke="currentColor" stroke-width="1.3"/></svg>`;
const iSave   = `<svg viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="1" stroke="currentColor" stroke-width="1.3"/><path d="M5 2v4h6V2" stroke="currentColor" stroke-width="1.2"/><rect x="4" y="9" width="8" height="4" stroke="currentColor" stroke-width="1"/></svg>`;
const iSun    = `<svg viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="3" stroke="currentColor" stroke-width="1.4"/><line x1="8" y1="1" x2="8" y2="2.5" stroke="currentColor" stroke-width="1.4"/><line x1="8" y1="13.5" x2="8" y2="15" stroke="currentColor" stroke-width="1.4"/><line x1="1" y1="8" x2="2.5" y2="8" stroke="currentColor" stroke-width="1.4"/><line x1="13.5" y1="8" x2="15" y2="8" stroke="currentColor" stroke-width="1.4"/><line x1="3.1" y1="3.1" x2="4.2" y2="4.2" stroke="currentColor" stroke-width="1.4"/><line x1="11.8" y1="11.8" x2="12.9" y2="12.9" stroke="currentColor" stroke-width="1.4"/><line x1="3.1" y1="12.9" x2="4.2" y2="11.8" stroke="currentColor" stroke-width="1.4"/><line x1="11.8" y1="4.2" x2="12.9" y2="3.1" stroke="currentColor" stroke-width="1.4"/></svg>`;
const iMoon   = `<svg viewBox="0 0 16 16" fill="none"><path d="M13.5 9.5A6 6 0 1 1 6.5 2.5a5 5 0 0 0 7 7z" stroke="currentColor" stroke-width="1.3" fill="currentColor" fill-opacity="0.15"/></svg>`;
const iGlobe  = `<svg viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6.5" stroke="currentColor" stroke-width="1.3"/><ellipse cx="8" cy="8" rx="2.6" ry="6.5" stroke="currentColor" stroke-width="1.1"/><line x1="1.5" y1="8" x2="14.5" y2="8" stroke="currentColor" stroke-width="1.1"/><path d="M2.5 5h11M2.5 11h11" stroke="currentColor" stroke-width="1"/></svg>`;
const iLink   = `<svg viewBox="0 0 16 16" fill="none"><circle cx="3" cy="4" r="2" stroke="currentColor" stroke-width="1.3"/><circle cx="13" cy="4" r="2" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="13" r="2" stroke="currentColor" stroke-width="1.3"/><line x1="4.6" y1="5.2" x2="6.7" y2="11.3" stroke="currentColor" stroke-width="1.2"/><line x1="11.4" y1="5.2" x2="9.3" y2="11.3" stroke="currentColor" stroke-width="1.2"/><line x1="5" y1="4" x2="11" y2="4" stroke="currentColor" stroke-width="1.2"/></svg>`;

/* ══════════════════════════════════════════════════════════════
   API CLIENT
   Communicates with the Python backend over REST/JSON.
   All requests go to the same origin (server serves HTML + API).
   ══════════════════════════════════════════════════════════════ */
const API = (() => {
  const BASE = '';  // same-origin; set to 'http://192.168.x.x:8080' for cross-origin

  function token() {
    return sessionStorage.getItem('snt_token') || '';
  }

  async function req(method, path, body) {
    const opts = {
      method,
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${token()}`
      }
    };
    if (body !== undefined) opts.body = JSON.stringify(body);

    let res;
    try {
      res = await fetch(BASE + path, opts);
    } catch (networkErr) {
      throw new Error('Cannot reach server. Is it running on port 8080?');
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (res.status === 401) {
        sessionStorage.clear();
        if (!location.pathname.endsWith('login.html')) location.href = 'login.html';
      }
      throw new Error(data.error || `Server error ${res.status}`);
    }
    return data;
  }

  return {
    /* raw verbs */
    get:    (p)      => req('GET',    p),
    post:   (p, b)   => req('POST',   p, b),
    put:    (p, b)   => req('PUT',    p, b),
    delete: (p)      => req('DELETE', p),

    /* auth */
    async login(username, password) {
      const d = await req('POST', '/api/auth/login', { username, password });
      sessionStorage.setItem('snt_token', d.token);
      sessionStorage.setItem('snt_user',  JSON.stringify(d.user));
      return d.user;
    },
    logout() {
      req('POST', '/api/auth/logout').catch(() => {});
      sessionStorage.clear();
      location.href = 'login.html';
    },

    /* stats & search */
    stats:   ()  => req('GET', '/api/stats'),
    search:  (q) => req('GET', `/api/search?q=${encodeURIComponent(q)}`),

    /* country profiles */
    countries:     (qs='') => req('GET', `/api/countries${qs}`),
    country:       (name)  => req('GET', `/api/countries/${encodeURIComponent(name)}`),
    knownCountries:()      => req('GET', '/api/countries/known-list'),

    /* persons */
    persons:      (qs='') => req('GET',    `/api/persons${qs}`),
    person:       (id)    => req('GET',    `/api/persons/${id}`),
    personActs:   (id, qs='') => req('GET',    `/api/persons/${id}/activities${qs}`),
    createPerson: (b)     => req('POST',   '/api/persons', b),
    updatePerson: (id, b) => req('PUT',    `/api/persons/${id}`, b),
    deletePerson: (id)    => req('DELETE', `/api/persons/${id}`),
    addGallery:   (id, b) => req('POST',   `/api/persons/${id}/gallery`, b),
    delGallery:   (pid, gid) => req('DELETE', `/api/persons/${pid}/gallery/${gid}`),

    /* groups */
    groups:       (qs='') => req('GET',    `/api/groups${qs}`),
    group:        (id)    => req('GET',    `/api/groups/${id}`),
    groupActs:    (id, qs='') => req('GET',    `/api/groups/${id}/activities${qs}`),
    createGroup:  (b)     => req('POST',   '/api/groups', b),
    updateGroup:  (id, b) => req('PUT',    `/api/groups/${id}`, b),
    deleteGroup:  (id)    => req('DELETE', `/api/groups/${id}`),

    /* activities */
    activities:     (qs='') => req('GET',    `/api/activities${qs}`),
    activity:       (id)    => req('GET',    `/api/activities/${id}`),
    createActivity: (b)     => req('POST',   '/api/activities', b),
    updateActivity: (id, b) => req('PUT',    `/api/activities/${id}`, b),
    deleteActivity: (id)    => req('DELETE', `/api/activities/${id}`),

    /* hotspots */
    hotspots:      ()       => req('GET',    '/api/hotspots'),
    createHotspot: (b)      => req('POST',   '/api/hotspots', b),
    updateHotspot: (id, b)  => req('PUT',    `/api/hotspots/${id}`, b),
    deleteHotspot: (id)     => req('DELETE', `/api/hotspots/${id}`),

    /* Multipart upload helper — must NOT set Content-Type (browser adds the boundary). */
    async _upload(path, formData) {
      let res;
      try {
        res = await fetch(BASE + path, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token()}` },
          body: formData,
        });
      } catch (e) {
        throw new Error('Cannot reach server.');
      }
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (res.status === 401) { sessionStorage.clear(); location.href = 'login.html'; }
        throw new Error(data.error || `Server error ${res.status}`);
      }
      return data;
    },

    /* NLP / document analysis (multipart submit, then poll + commit) */
    nlpSubmit: (formData) => API._upload('/api/nlp/submit', formData),
    nlpJobs:   ()   => req('GET',  '/api/nlp/jobs'),
    nlpJob:    (id) => req('GET',  `/api/nlp/jobs/${id}`),
    nlpCommit: (id, selections) => req('POST', `/api/nlp/jobs/${id}/commit`, selections ? { selections } : {}),
    nlpReject: (id) => req('POST', `/api/nlp/jobs/${id}/reject`, {}),

    /* Face search (multipart photo upload -> ranked POI matches) */
    faceSearch: (formData) => API._upload('/api/face/search', formData),

    /* Link Analysis charts */
    linkCharts:      ()          => req('GET',    '/api/link-charts'),
    createLinkChart: (b)         => req('POST',   '/api/link-charts', b),
    getLinkChart:    (id)        => req('GET',    `/api/link-charts/${id}`),
    updateLinkChart: (id, b)     => req('PUT',    `/api/link-charts/${id}`, b),
    deleteLinkChart: (id)        => req('DELETE', `/api/link-charts/${id}`),
    addLinkNode:     (id, b)     => req('POST',   `/api/link-charts/${id}/nodes`, b),
    updateLinkNode:  (id, nid, b)=> req('PUT',    `/api/link-charts/${id}/nodes/${nid}`, b),
    deleteLinkNode:  (id, nid)   => req('DELETE', `/api/link-charts/${id}/nodes/${nid}`),

    /* intel */
    intelList:   ()       => req('GET',    '/api/intel'),
    intelGet:    (id)     => req('GET',    `/api/intel/${id}`),
    createIntel: (b)      => req('POST',   '/api/intel', b),
    updateIntel: (id, b)  => req('PUT',    `/api/intel/${id}`, b),
    deleteIntel: (id)     => req('DELETE', `/api/intel/${id}`),

    /* users */
    users:       ()       => req('GET',    '/api/users'),
    createUser:  (b)      => req('POST',   '/api/users', b),
    updateUser:  (id, b)  => req('PUT',    `/api/users/${id}`, b),
    deleteUser:  (id)     => req('DELETE', `/api/users/${id}`),

    /* audit & backups */
    audit:        (qs='') => req('GET',  `/api/audit${qs}`),
    backups:      ()      => req('GET',  '/api/backups'),
    createBackup: ()      => req('POST', '/api/backups', {}),

    /* extras — tags, notes, fields, attachments, relationships */
    extras:          (type, id)     => req('GET',    `/api/${type}/${id}/extras`),
    getTags:         (type, id)     => req('GET',    `/api/${type}/${id}/tags`),
    addTag:          (type, id, b)  => req('POST',   `/api/${type}/${id}/tags`, b),
    deleteTag:       (tid)          => req('DELETE', `/api/tags/${tid}`),
    getNotes:        (type, id)     => req('GET',    `/api/${type}/${id}/notes`),
    addNote:         (type, id, b)  => req('POST',   `/api/${type}/${id}/notes`, b),
    updateNote:      (nid, b)       => req('PUT',    `/api/notes/${nid}`, b),
    deleteNote:      (nid)          => req('DELETE', `/api/notes/${nid}`),
    getFields:       (type, id)     => req('GET',    `/api/${type}/${id}/fields`),
    addField:        (type, id, b)  => req('POST',   `/api/${type}/${id}/fields`, b),
    updateField:     (fid, b)       => req('PUT',    `/api/fields/${fid}`, b),
    deleteField:     (fid)          => req('DELETE', `/api/fields/${fid}`),
    getAttachments:  (type, id)     => req('GET',    `/api/${type}/${id}/attachments`),
    addAttachment:   (type, id, b)  => req('POST',   `/api/${type}/${id}/attachments`, b),
    deleteAttachment:(aid)          => req('DELETE', `/api/attachments/${aid}`),
    getImages:       (type, id)     => req('GET',    `/api/${type}/${id}/images`),
    addImage:        (type, id, b)  => req('POST',   `/api/${type}/${id}/images`, b),
    deleteImage:     (iid)          => req('DELETE', `/api/images/${iid}`),
    getLocations:    (type, id)     => req('GET',    `/api/${type}/${id}/locations`),
    addLocation:     (type, id, b)  => req('POST',   `/api/${type}/${id}/locations`, b),
    deleteLocation:  (lid)          => req('DELETE', `/api/locations/${lid}`),
    getRels:         (type, id)     => req('GET',    `/api/${type}/${id}/relationships`),
    addRel:          (type, id, b)  => req('POST',   `/api/${type}/${id}/relationships`, b),
    deleteRel:       (rid)          => req('DELETE', `/api/relationships/${rid}`),
  };
})();

/* ══════════════════════════════════════════════════════════════
   MAP — shared MapLibre GL helpers (all GIS maps in the app)
   Basemap: OpenFreeMap's free public vector-tile endpoint (no self-hosting,
   no API key). This is the one part of SENTINEL that needs internet — all
   pin/marker data stays fully local either way.

   IMPORTANT: Leaflet used [lat,lng] point order everywhere; MapLibre (like
   GeoJSON) uses [lng,lat]. Every helper below takes the app's existing
   [lat,lng] convention as input and converts internally, so call sites
   migrating off Leaflet don't have to juggle the swap themselves.
   ══════════════════════════════════════════════════════════════ */
const MAP = (() => {
  const STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty';

  function create(containerId, { center = [1, 35], zoom = 4, scrollZoom = false } = {}) {
    const map = new maplibregl.Map({
      container: containerId,
      style: STYLE_URL,
      center: [center[1], center[0]],
      zoom,
      attributionControl: true,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
    if (!scrollZoom) map.scrollZoom.disable();
    return map;
  }

  /* A small filled circle marker, styled to match the old Leaflet
     circleMarker look. Returns the maplibregl.Marker. */
  function circleMarker(map, lat, lng, { radius = 8, color = '#4a8fe8', weight = 2 } = {}) {
    const el = document.createElement('div');
    el.style.cssText = `width:${radius * 2}px;height:${radius * 2}px;border-radius:50%;` +
      `background:${color};opacity:.85;border:${weight}px solid ${color};` +
      `box-shadow:0 0 4px rgba(0,0,0,.5);cursor:pointer`;
    return new maplibregl.Marker({ element: el }).setLngLat([lng, lat]).addTo(map);
  }

  /* A marker built from arbitrary custom HTML (replaces Leaflet's L.divIcon). */
  function htmlMarker(map, lat, lng, html) {
    const el = document.createElement('div');
    el.innerHTML = html;
    const node = el.firstElementChild || el;
    return new maplibregl.Marker({ element: node }).setLngLat([lng, lat]).addTo(map);
  }

  /* Attaches a popup that opens on hover (mirrors the old
     .bindPopup() + mouseover-opens pattern) and optionally a dblclick handler. */
  function bindHoverPopup(marker, html, { maxWidth = '280px', onDblClick = null } = {}) {
    const popup = new maplibregl.Popup({ offset: 12, maxWidth, closeButton: false }).setHTML(html);
    marker.setPopup(popup);
    const el = marker.getElement();
    el.addEventListener('mouseenter', () => { if (!popup.isOpen()) marker.togglePopup(); });
    el.addEventListener('mouseleave', () => { if (popup.isOpen()) marker.togglePopup(); });
    if (onDblClick) el.addEventListener('dblclick', onDblClick);
    return popup;
  }

  /* Fit the view to a list of [lat,lng] points (mirrors L.map.fitBounds(points)). */
  function fitToPoints(map, points, padding = 30) {
    if (!points.length) return;
    const bounds = points.reduce(
      (b, p) => b.extend([p[1], p[0]]),
      new maplibregl.LngLatBounds([points[0][1], points[0][0]], [points[0][1], points[0][0]])
    );
    map.fitBounds(bounds, { padding, maxZoom: 14 });
  }

  return { STYLE_URL, create, circleMarker, htmlMarker, bindHoverPopup, fitToPoints };
})();

/* ══════════════════════════════════════════════════════════════
   SESSION HELPERS
   ══════════════════════════════════════════════════════════════ */
function getUser() {
  try { return JSON.parse(sessionStorage.getItem('snt_user') || 'null'); }
  catch { return null; }
}

function requireAuth(roles) {
  const u = getUser();
  if (!u || !sessionStorage.getItem('snt_token')) {
    location.href = 'login.html';
    return null;
  }
  if (roles && !roles.includes(u.role)) {
    showToast('Access denied for your role.', 'error');
    setTimeout(() => history.back(), 1200);
    return null;
  }
  return u;
}

/* ══════════════════════════════════════════════════════════════
   THEME ENGINE — Light / Dark mode
   Persisted in localStorage so it's shared across the whole app
   and survives logout/login. Applied immediately (before this file
   finishes loading) via the IIFE further down to avoid a flash of
   the wrong theme on page load.
   ══════════════════════════════════════════════════════════════ */
const THEME_KEY = 'snt_theme';

function getTheme() {
  return localStorage.getItem(THEME_KEY) === 'light' ? 'light' : 'dark';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
  // keep any open Leaflet maps' tile layer looking right; nothing to re-render,
  // the CSS filter on .leaflet-tile-pane handles it reactively.
  document.dispatchEvent(new CustomEvent('sentinel:theme', { detail: { theme } }));
  syncThemeToggleUI(theme);
}

function toggleTheme() {
  applyTheme(getTheme() === 'dark' ? 'light' : 'dark');
}

function syncThemeToggleUI(theme) {
  document.querySelectorAll('[data-theme-toggle]').forEach(el => {
    el.setAttribute('aria-checked', theme === 'light' ? 'true' : 'false');
    const label = el.querySelector('[data-theme-label]');
    if (label) label.textContent = theme === 'light' ? 'LIGHT' : 'DARK';
    const thumb = el.querySelector('.theme-toggle-thumb');
    if (thumb) thumb.innerHTML = theme === 'light' ? iSun : iMoon;
  });
}

/** Returns the HTML for a theme toggle switch. Call wireThemeToggles()
 *  after inserting this into the DOM (buildSidebar/buildTopbar do this
 *  automatically wherever they place it).
 *  @param {string} idSuffix - unique suffix so multiple toggles can coexist
 *  @param {boolean} compact - icon-only, no text label (used in topbar) */
function themeToggleHtml(idSuffix = '', compact = false) {
  const theme = getTheme();
  return `
    <div class="theme-toggle ${compact ? 'theme-toggle-compact' : ''}" data-theme-toggle role="switch" aria-checked="${theme === 'light'}"
         tabindex="0" id="themeToggle${idSuffix}"
         title="Toggle light / dark theme">
      ${compact ? '' : `<span data-theme-label>${theme === 'light' ? 'LIGHT' : 'DARK'}</span>`}
      <span class="theme-toggle-track">
        <span class="theme-toggle-thumb">${theme === 'light' ? iSun : iMoon}</span>
      </span>
    </div>`;
}

function wireThemeToggles() {
  document.querySelectorAll('[data-theme-toggle]').forEach(el => {
    if (el._wired) return;
    el._wired = true;
    el.addEventListener('click', toggleTheme);
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleTheme(); }
    });
  });
}

/* Apply the saved theme as early as possible (before DOMContentLoaded)
   to prevent a flash of the default dark theme on light-mode reloads. */
(function initThemeEarly() {
  document.documentElement.setAttribute('data-theme', getTheme());
})();

/* ══════════════════════════════════════════════════════════════
   NAVIGATION — Sidebar & Topbar
   ══════════════════════════════════════════════════════════════ */
function buildSidebar(activePage) {
  const user    = getUser() || {};
  const isAdmin = user.role === 'ADMIN';

  const nav = [
    ...(isAdmin ? [] : [
      { label: 'Main', items: [
        { href: 'dashboard.html',            icon: iGrid,   text: 'Dashboard',            key: 'dashboard'  },
      ]},
      { label: 'Intelligence', items: [
        { href: 'persons.html',              icon: iUsers,  text: 'Persons of Interest',  key: 'persons'    },
        { href: 'groups.html',               icon: iGroup,  text: 'Groups of Interest',   key: 'groups'     },
        { href: 'activities_hotspots.html',  icon: iMap,    text: 'Activities & Hotspots',key: 'activities' },
        { href: 'countries.html',            icon: iGlobe,  text: 'Country Profiles',     key: 'countries'  },
        { href: 'analysis.html',             icon: iDoc,    text: 'Intel / Analysis',     key: 'analysis'   },
        { href: 'linkanalysis.html',         icon: iLink,   text: 'Link Analysis',        key: 'linkanalysis' },
      ]},
    ]),
    ...(isAdmin ? [{ label: 'Administration', items: [
      { href: 'admin.html',                icon: iShield, text: 'Admin Panel',          key: 'admin'      },
    ]}] : []),
    { label: 'System', items: [
      { href: 'index.html',                icon: iHome,   text: 'Home',                 key: 'home'       },
    ]},
  ];

  const roleColors = { ADMIN: 'var(--danger)', ANALYST: 'var(--accent)', VIEWER: 'var(--accent2)' };
  const roleColor  = roleColors[user.role] || 'var(--text-dim)';

  const html = `
  <div class="sidebar" id="sidebar">
    <div class="sidebar-logo">
      <div class="logo-icon">
        <svg viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="5" stroke="#e8c44a" stroke-width="1.2"/>
          <circle cx="8" cy="8" r="2" fill="#e8c44a"/>
          <line x1="8" y1="1"    x2="8"  y2="3.5" stroke="#e8c44a" stroke-width="1.2"/>
          <line x1="8" y1="12.5" x2="8"  y2="15"  stroke="#e8c44a" stroke-width="1.2"/>
          <line x1="1" y1="8"    x2="3.5" y2="8"  stroke="#e8c44a" stroke-width="1.2"/>
          <line x1="12.5" y1="8" x2="15"  y2="8"  stroke="#e8c44a" stroke-width="1.2"/>
        </svg>
      </div>
      <a href="index.html" class="logo-text"><span>S</span>ENTINEL</a>
    </div>

    ${nav.map(sec => `
      <div class="sidebar-section">
        <div class="sidebar-section-label">${sec.label}</div>
        ${sec.items.map(it => `
          <a href="${it.href}" class="nav-item ${activePage === it.key ? 'active' : ''}">
            ${it.icon} ${it.text}
          </a>`).join('')}
      </div>`).join('')}

    <div class="sidebar-footer">
      <div class="user-name">${escHtml(user.name || '')}</div>
      <div class="mono" style="font-size:10px">${escHtml(user.unit || '')}</div>
      <div style="margin-top:6px">
        <span class="badge" style="background:${roleColor}22;color:${roleColor};border:1px solid ${roleColor}44;font-family:'JetBrains Mono',monospace;font-size:10px;padding:2px 7px">
          ${user.role || ''}
        </span>
      </div>
      <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
        ${themeToggleHtml('Sidebar')}
      </div>
      <div style="margin-top:10px">
        <a href="#" onclick="API.logout();return false"
           style="color:var(--danger);font-size:10px;font-family:'JetBrains Mono',monospace;text-decoration:none">
          ⏻ Logout
        </a>
      </div>
    </div>
  </div>`;

  const mount = document.getElementById('sidebarMount');
  if (mount) mount.outerHTML = html;
  wireThemeToggles();
}

function buildTopbar(crumbs = []) {
  const html = `
  <div class="topbar">
    <div class="topbar-breadcrumb">
      <a href="index.html">SENTINEL</a>
      ${crumbs.map(c =>
        `<span style="color:var(--muted)">›</span>${
          c.href
            ? `<a href="${c.href}">${escHtml(c.label)}</a>`
            : `<span>${escHtml(c.label)}</span>`
        }`).join('')}
    </div>
    <div class="topbar-right">
      <div id="globalSearch" style="position:relative">
        <div class="search-bar" style="max-width:260px">
          ${iSearch}
          <input type="text" id="globalSearchInput" placeholder="Search…" autocomplete="off"
                 aria-label="Global search"/>
        </div>
        <div id="searchResults" class="hidden"
             style="position:absolute;top:100%;left:0;right:0;
                    background:var(--panel);border:1px solid var(--border);
                    z-index:500;max-height:320px;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,.4)">
        </div>
      </div>
      <div class="topbar-clock" id="topClock"></div>
      <div id="topThemeToggle">${themeToggleHtml('Topbar', true)}</div>
      <div class="topbar-user">
        <div class="avatar" id="topAvatar">?</div>
        <span id="topUser" style="font-size:12px"></span>
      </div>
    </div>
  </div>`;

  const mount = document.getElementById('topbarMount');
  if (mount) mount.outerHTML = html;
  wireThemeToggles();
}

function initTopbar() {
  wireThemeToggles();
  const u = getUser();
  if (u) {
    const av = document.getElementById('topAvatar');
    const tu = document.getElementById('topUser');
    if (av) av.textContent = (u.name || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
    if (tu) tu.textContent = u.name;
  }

  /* Clock */
  const tick = () => {
    const el = document.getElementById('topClock');
    if (el) el.textContent = new Date().toLocaleTimeString('en-GB');
  };
  tick();
  setInterval(tick, 1000);

  /* Global search */
  const inp = document.getElementById('globalSearchInput');
  const box = document.getElementById('searchResults');
  if (!inp || !box) return;

  let timer;
  inp.addEventListener('input', () => {
    clearTimeout(timer);
    const q = inp.value.trim();
    if (q.length < 2) { box.classList.add('hidden'); return; }
    timer = setTimeout(async () => {
      try {
        const res = await API.search(q);
        if (!res.length) {
          box.innerHTML = '<div style="padding:12px;color:var(--text-dim);font-size:12px;font-family:JetBrains Mono,monospace">No results found.</div>';
        } else {
          const typeStyle = {
            person:   'badge-amber',
            group:    'badge-blue',
            activity: 'badge-grey',
          };
          box.innerHTML = res.map(r => `
            <a href="${escHtml(r.url)}"
               style="display:flex;gap:10px;padding:10px 12px;border-bottom:1px solid var(--border);
                      text-decoration:none;align-items:center;color:inherit"
               onmouseover="this.style.background='var(--panel2)'"
               onmouseout="this.style.background=''">
              <span class="badge ${typeStyle[r.type] || 'badge-grey'}" style="flex-shrink:0">${escHtml(r.type)}</span>
              <div>
                <div style="font-size:12px;color:var(--text-hi)">${escHtml(r.label)}</div>
                <div style="font-size:10px;color:var(--text-dim);font-family:JetBrains Mono,monospace">${escHtml(r.sub)}</div>
              </div>
            </a>`).join('');
        }
        box.classList.remove('hidden');
      } catch (e) {
        box.innerHTML = `<div style="padding:10px 12px;color:var(--danger);font-size:11px;font-family:JetBrains Mono,monospace">Search error: ${escHtml(e.message)}</div>`;
        box.classList.remove('hidden');
      }
    }, 320);
  });

  document.addEventListener('click', e => {
    const gs = document.getElementById('globalSearch');
    if (gs && !gs.contains(e.target)) box.classList.add('hidden');
  });
}

/* ══════════════════════════════════════════════════════════════
   UTILITY FUNCTIONS
   ══════════════════════════════════════════════════════════════ */
function escHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatDate(d) {
  if (!d) return '—';
  try {
    const dt = new Date(d);
    if (isNaN(dt)) return String(d);
    return dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch { return String(d); }
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function riskBadge(level) {
  const cls = { CRITICAL:'badge-red', HIGH:'badge-red', MEDIUM:'badge-amber', LOW:'badge-green', INACTIVE:'badge-grey' }[level] || 'badge-grey';
  return `<span class="badge ${cls}">${escHtml(level || '—')}</span>`;
}

function threatBadge(level) { return riskBadge(level); }

function statusBadge(s) {
  const cls = { ACTIVE:'badge-green', INACTIVE:'badge-grey', DORMANT:'badge-amber' }[s] || 'badge-grey';
  return `<span class="badge ${cls}">${escHtml(s || '—')}</span>`;
}

function sevBadge(s) {
  const cls = { CRITICAL:'badge-red', HIGH:'badge-red', MEDIUM:'badge-amber', LOW:'badge-green' }[s] || 'badge-grey';
  return `<span class="badge ${cls}">${escHtml(s || '—')}</span>`;
}

function openModal(id)  { document.getElementById(id)?.classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id)?.classList.add('hidden'); }

function initTabs(containerId) {
  const c = document.getElementById(containerId);
  if (!c) return;
  c.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      c.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      c.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const target = document.getElementById(btn.dataset.target);
      if (target) target.classList.add('active');
    });
  });
}

function showToast(msg, type = 'info') {
  /* Remove any existing toast */
  document.querySelectorAll('.snt-toast').forEach(t => t.remove());

  const colors = {
    success: { bg: '#1a3a1a', border: '#4ae87a', text: '#6aeaa0' },
    error:   { bg: '#3a1a1a', border: 'var(--danger)', text: '#e88a8a' },
    info:    { bg: 'var(--panel)', border: 'var(--border)', text: 'var(--text)' },
  };
  const c = colors[type] || colors.info;

  const t = document.createElement('div');
  t.className = 'snt-toast';
  t.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:9999;
    padding:12px 20px;max-width:340px;
    background:${c.bg};border:1px solid ${c.border};color:${c.text};
    font-family:'JetBrains Mono',monospace;font-size:12px;
    box-shadow:0 4px 20px rgba(0,0,0,.5);
    animation:fadeInUp .2s ease;pointer-events:none;
  `;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(() => t.remove(), 300); }, 3200);
}

function printReport(title, html) {
  const w = window.open('', '_blank');
  w.document.write(`<!DOCTYPE html><html><head>
    <title>${escHtml(title)}</title>
    <link rel="stylesheet" href="${location.origin}/vendor/fonts/fonts.css">
    <style>
      * { box-sizing: border-box; }
      body{font-family:Inter,sans-serif;color:#111;padding:32px;max-width:1000px;margin:auto}
      h1{font-size:22px;margin-bottom:4px}
      h2{font-size:16px;margin:22px 0 10px;border-bottom:1px solid #ddd;padding-bottom:5px;page-break-after:avoid}
      p,div{font-size:13px;margin:4px 0;color:#333}
      table{width:100%;border-collapse:collapse;margin:8px 0;page-break-inside:avoid}
      th{background:#f0f0f0;text-align:left;padding:7px 10px;font-size:11px;letter-spacing:.04em;border:1px solid #ddd}
      td{padding:7px 10px;font-size:12px;border:1px solid #eee}
      pre{font-family:'JetBrains Mono',monospace;font-size:11px;white-space:pre-wrap;background:#f8f8f8;padding:12px;border:1px solid #eee}

      /* Report header strip */
      .rpt-header{display:flex;align-items:flex-start;gap:18px;margin-bottom:18px;padding-bottom:18px;border-bottom:2px solid #222}
      .rpt-photo{width:96px;height:116px;object-fit:cover;border:1px solid #ccc;background:#f4f4f4;flex-shrink:0}
      .rpt-photo-empty{width:96px;height:116px;border:1px dashed #bbb;background:#f7f7f7;display:flex;align-items:center;justify-content:center;color:#999;font-size:10px;text-align:center;flex-shrink:0}
      .rpt-class{display:inline-block;background:#c0392b;color:#fff;font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:.12em;padding:2px 8px;margin-bottom:6px}

      /* Badges (flattened for print — no CSS vars) */
      .badge{display:inline-block;padding:2px 8px;border-radius:2px;font-size:10px;font-family:'JetBrains Mono',monospace;letter-spacing:.05em;border:1px solid transparent;margin-right:4px}
      .badge-red{background:#fde2e2;color:#a52a2a;border-color:#e8b4b4}
      .badge-amber{background:#fdf3d8;color:#8a6d1f;border-color:#e8d49a}
      .badge-green{background:#e1f5e6;color:#1f7a3a;border-color:#a9d9b8}
      .badge-blue{background:#e3edfb;color:#1d4f91;border-color:#a9c4ec}
      .badge-grey{background:#eee;color:#555;border-color:#ddd}

      /* Image gallery grid */
      .rpt-gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:10px 0}
      .rpt-gallery img{width:100%;aspect-ratio:4/3;object-fit:cover;border:1px solid #ddd;display:block}
      .rpt-gallery figcaption{font-size:9px;color:#777;margin-top:3px;text-align:center}
      .rpt-gallery figure{margin:0;page-break-inside:avoid}

      /* GIS map embed */
      .rpt-map-wrap{margin:10px 0;page-break-inside:avoid}
      .rpt-map-wrap img{width:100%;max-width:640px;border:1px solid #ccc;display:block}
      .rpt-map-caption{font-family:'JetBrains Mono',monospace;font-size:10px;color:#777;margin-top:4px}
      .rpt-map-empty{padding:20px;border:1px dashed #bbb;background:#f7f7f7;color:#999;font-size:11px;text-align:center}

      .rpt-footer{margin-top:30px;padding-top:10px;border-top:1px solid #ddd;font-family:'JetBrains Mono',monospace;font-size:9px;color:#999;display:flex;justify-content:space-between}

      @media print {
        body{padding:0}
        a{color:inherit;text-decoration:none}
        .rpt-gallery{grid-template-columns:repeat(3,1fr)}
      }
    </style>
  </head><body>${html}
    <div class="rpt-footer">
      <span>SENTINEL Intelligence Tracking System — RESTRICTED</span>
      <span>Printed ${new Date().toLocaleString()}</span>
    </div>
  </body></html>`);
  w.document.close();
  setTimeout(() => w.print(), 700);
}

/** Returns a static map for embedding in printed reports, where a live
 *  interactive map can't be used (it's a separate print window). Renders an
 *  offscreen MapLibre map against the same OpenFreeMap style the rest of the
 *  app uses, then snapshots it to a PNG data URI via canvas.toDataURL() —
 *  the print window just gets a plain <img>, no map library needed there.
 *  Falls back to a placeholder block if no coordinates are given, or if the
 *  snapshot can't be produced (e.g. offline). */
async function staticMapHtml(points, opts = {}) {
  const { width = 640, height = 320, zoom = null, caption = '' } = opts;
  const valid = (points || []).filter(p => p && p.lat != null && p.lng != null && !isNaN(p.lat) && !isNaN(p.lng));
  if (!valid.length) {
    return `<div class="rpt-map-wrap"><div class="rpt-map-empty">No geo-tagged locations available for this record.</div></div>`;
  }

  let dataUrl = null;
  try {
    dataUrl = await _snapshotStaticMap(valid, { width, height, zoom });
  } catch (e) {
    console.warn('Map snapshot failed:', e);
  }

  if (!dataUrl) {
    return `<div class="rpt-map-wrap"><div class="rpt-map-empty">Map preview unavailable (could not render — offline or the basemap failed to load).</div>${caption ? `<div class="rpt-map-caption">${escHtml(caption)}</div>` : ''}</div>`;
  }
  return `
    <div class="rpt-map-wrap">
      <img src="${dataUrl}" width="${width}" height="${height}" style="width:100%;max-width:${width}px;border:1px solid #ccc;display:block;background:#e8e8e8"/>
      ${caption ? `<div class="rpt-map-caption">${escHtml(caption)}</div>` : ''}
    </div>`;
}

/** Renders `points` on an offscreen MapLibre map and resolves a PNG data URI
 *  once tiles/markers have finished drawing. Markers are added as a native
 *  circle layer (not DOM Markers) so they're actually part of the WebGL
 *  canvas — a DOM-overlay marker wouldn't show up in canvas.toDataURL(). */
function _snapshotStaticMap(points, { width, height, zoom }) {
  return new Promise((resolve, reject) => {
    if (typeof maplibregl === 'undefined') return reject(new Error('MapLibre not loaded'));

    const container = document.createElement('div');
    container.style.cssText = `position:fixed;left:-99999px;top:0;width:${width}px;height:${height}px;`;
    document.body.appendChild(container);

    const map = new maplibregl.Map({
      container, style: MAP.STYLE_URL,
      center: [points[0].lng, points[0].lat], zoom: zoom || (points.length > 1 ? 5 : 9),
      interactive: false, attributionControl: false, preserveDrawingBuffer: true,
    });

    let settled = false;
    const cleanup = () => { try { map.remove(); } catch {} container.remove(); };
    const finish = (err, dataUrl) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      cleanup();
      err ? reject(err) : resolve(dataUrl);
    };
    const timer = setTimeout(() => finish(new Error('Map snapshot timed out')), 15000);

    map.on('load', () => {
      map.addSource('rpt-points', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: points.map(p => ({
          type: 'Feature', geometry: { type: 'Point', coordinates: [p.lng, p.lat] }, properties: {},
        })) },
      });
      map.addLayer({
        id: 'rpt-points-layer', type: 'circle', source: 'rpt-points',
        paint: {
          'circle-radius': 6, 'circle-color': '#2a7ae2',
          'circle-stroke-width': 2, 'circle-stroke-color': '#ffffff',
        },
      });
      if (points.length > 1) {
        const bounds = points.reduce(
          (b, p) => b.extend([p.lng, p.lat]),
          new maplibregl.LngLatBounds([points[0].lng, points[0].lat], [points[0].lng, points[0].lat])
        );
        map.fitBounds(bounds, { padding: 30, animate: false });
      }
    });
    map.on('idle', () => {
      try { finish(null, map.getCanvas().toDataURL('image/png')); }
      catch (e) { finish(e); }
    });
    map.on('error', e => finish(e.error || new Error('Map error')));
  });
}

/** Returns an image-gallery grid for printed reports from an array of
 *  { src, caption } objects (e.g. person_gallery rows or attachment images). */
function reportGalleryHtml(images, opts = {}) {
  const { emptyText = 'No photos on file.' } = opts;
  const valid = (images || []).filter(i => i && i.src);
  if (!valid.length) {
    return `<div style="font-size:12px;color:#999;padding:8px 0">${escHtml(emptyText)}</div>`;
  }
  return `<div class="rpt-gallery">
    ${valid.map(img => `
      <figure>
        <img src="${img.src}" alt="${escHtml(img.caption || '')}"/>
        <figcaption>${escHtml(img.caption || '')}</figcaption>
      </figure>`).join('')}
  </div>`;
}

/** Returns a fixed-size <img> or labelled placeholder block for a single
 *  profile photo, used in the header strip of printed person/group reports. */
function reportPhotoHtml(src, label = 'NO PHOTO') {
  return src
    ? `<img class="rpt-photo" src="${src}" alt="Photo"/>`
    : `<div class="rpt-photo-empty">${escHtml(label)}</div>`;
}

async function fileToB64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload  = e => resolve(e.target.result);
    r.onerror = () => reject(new Error('File read failed'));
    r.readAsDataURL(file);
  });
}

/* ══════════════════════════════════════════════════════════════
   SUI — Reusable UI Component Library
   ══════════════════════════════════════════════════════════════ */
const SUI = (() => {

  /* ── TAGS ───────────────────────────────────────────────────── */
  async function tags(container, entityType, entityId, canEdit = false) {
    const wrap = typeof container === 'string' ? document.getElementById(container) : container;
    if (!wrap) return;
    wrap.innerHTML = '<span style="font-size:11px;color:var(--text-dim)">Loading tags…</span>';
    try {
      const list = await API.getTags(entityType, entityId);
      _renderTags(wrap, list, entityType, entityId, canEdit);
    } catch {
      wrap.innerHTML = '';
    }
  }

  function _renderTags(wrap, list, entityType, entityId, canEdit) {
    wrap.innerHTML = `
      <div class="tag-list" id="tagList_${entityId}">
        ${list.map(t => `
          <span class="tag-pill"
                style="background:${t.color}22;border:1px solid ${t.color}55;color:${t.color}">
            ${escHtml(t.tag)}
            ${canEdit
              ? `<button onclick="SUI._removeTag('${t.id}','${entityType}','${entityId}')"
                         style="background:none;border:none;color:inherit;cursor:pointer;margin-left:3px;font-size:11px;line-height:1">×</button>`
              : ''}
          </span>`).join('')}
        ${canEdit ? `
          <span class="tag-add-btn"
                onclick="SUI._openTagInput('${entityType}','${entityId}')">+ tag</span>
          <input id="tagInput_${entityId}" class="tag-input hidden"
                 placeholder="add tag…"
                 onkeydown="if(event.key==='Enter'){SUI._addTag('${entityType}','${entityId}');}
                            if(event.key==='Escape'){this.classList.add('hidden');}"/>
        ` : ''}
      </div>`;
  }

  async function _removeTag(tid, etype, eid) {
    try {
      await API.deleteTag(tid);
      const wrap = document.getElementById(`tagList_${eid}`)?.parentElement;
      if (wrap) await tags(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  function _openTagInput(etype, eid) {
    const inp = document.getElementById(`tagInput_${eid}`);
    if (inp) { inp.classList.toggle('hidden'); inp.focus(); }
  }

  async function _addTag(etype, eid) {
    const inp = document.getElementById(`tagInput_${eid}`);
    const val = inp?.value.trim().toLowerCase().replace(/\s+/g, '-');
    if (!val) return;
    const palette = ['#e8c44a','#4a8fe8','#4ae87a','#e88a4a','#e84a4a','#c44ae8'];
    const color   = palette[Math.abs(val.split('').reduce((a, c) => a + c.charCodeAt(0), 0)) % palette.length];
    try {
      await API.addTag(etype, eid, { tag: val, color });
      inp.value = ''; inp.classList.add('hidden');
      const wrap = document.getElementById(`tagList_${eid}`)?.parentElement;
      if (wrap) await tags(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  /* ── NOTES ──────────────────────────────────────────────────── */
  const NOTE_COLORS = {
    GENERAL:      'var(--border)',
    FIELD_REPORT: 'rgba(74,143,232,.4)',
    ASSESSMENT:   'rgba(232,196,74,.4)',
    OBSERVATION:  'rgba(74,232,122,.35)',
    WARNING:      'rgba(232,74,74,.5)',
  };
  const NOTE_ICONS = { GENERAL:'📝', FIELD_REPORT:'🔭', ASSESSMENT:'📊', OBSERVATION:'👁', WARNING:'⚠️' };

  async function notes(container, entityType, entityId, canEdit = false) {
    const wrap = typeof container === 'string' ? document.getElementById(container) : container;
    if (!wrap) return;
    wrap.innerHTML = '<span style="font-size:11px;color:var(--text-dim)">Loading notes…</span>';
    try {
      const list = await API.getNotes(entityType, entityId);
      _renderNotes(wrap, list, entityType, entityId, canEdit);
    } catch (e) {
      wrap.innerHTML = `<span style="color:var(--danger);font-size:11px">Failed to load notes: ${escHtml(e.message)}</span>`;
    }
  }

  function _renderNotes(wrap, list, etype, eid, canEdit) {
    wrap.innerHTML = `
      ${canEdit ? `
        <div id="noteCompose_${eid}" style="display:none;margin-bottom:14px">
          <div class="form-row" style="margin-bottom:8px">
            <input class="form-input" id="noteTitle_${eid}" placeholder="Note title (optional)"/>
            <select class="form-select" id="noteType_${eid}">
              <option value="GENERAL">General</option>
              <option value="FIELD_REPORT">Field Report</option>
              <option value="ASSESSMENT">Assessment</option>
              <option value="OBSERVATION">Observation</option>
              <option value="WARNING">Warning</option>
            </select>
          </div>
          <textarea class="form-textarea" id="noteBody_${eid}"
                    placeholder="Write note…" style="min-height:90px"></textarea>
          <div class="flex flex-gap-8 mt-8" style="align-items:center">
            <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-dim)">
              <input type="checkbox" id="notePin_${eid}"/> Pin
            </label>
            <div style="margin-left:auto;display:flex;gap:8px">
              <button class="btn btn-secondary btn-sm"
                      onclick="document.getElementById('noteCompose_${eid}').style.display='none'">Cancel</button>
              <button class="btn btn-primary btn-sm"
                      onclick="SUI._saveNote('${etype}','${eid}')">Save Note</button>
            </div>
          </div>
        </div>
        <div style="margin-bottom:12px">
          <button class="btn btn-secondary btn-sm"
                  onclick="const c=document.getElementById('noteCompose_${eid}');c.style.display=c.style.display==='none'?'block':'none'">
            ${iPlus} Add Note
          </button>
        </div>` : ''}
      <div id="notesList_${eid}">
        ${list.length ? list.map(n => `
          <div class="note-card"
               style="border-left:3px solid ${NOTE_COLORS[n.note_type] || 'var(--border)'}">
            <div class="note-header">
              <span class="note-icon">${NOTE_ICONS[n.note_type] || '📝'}</span>
              <span class="note-type-badge">${n.note_type}</span>
              ${n.is_pinned ? '<span class="note-pin">📌 PINNED</span>' : ''}
              <span class="note-date">${formatDate(n.created_at)}</span>
              ${canEdit ? `
                <button class="btn btn-danger btn-sm" style="margin-left:auto;padding:3px 8px"
                        onclick="SUI._deleteNote('${n.id}','${etype}','${eid}')">✕</button>` : ''}
            </div>
            ${n.title ? `<div class="note-title">${escHtml(n.title)}</div>` : ''}
            <div class="note-body">${escHtml(n.body)}</div>
          </div>`).join('')
        : '<div style="color:var(--text-dim);font-size:12px;padding:10px 0">No notes recorded.</div>'}
      </div>`;
  }

  async function _saveNote(etype, eid) {
    const body = document.getElementById(`noteBody_${eid}`)?.value.trim();
    if (!body) { showToast('Note body is required', 'error'); return; }
    try {
      await API.addNote(etype, eid, {
        title:    document.getElementById(`noteTitle_${eid}`)?.value.trim() || '',
        body,
        noteType: document.getElementById(`noteType_${eid}`)?.value || 'GENERAL',
        isPinned: document.getElementById(`notePin_${eid}`)?.checked ? 1 : 0,
      });
      showToast('Note saved', 'success');
      const wrap = document.getElementById(`notesList_${eid}`)?.parentElement;
      if (wrap) await notes(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  async function _deleteNote(nid, etype, eid) {
    if (!confirm('Delete this note?')) return;
    try {
      await API.deleteNote(nid);
      const wrap = document.getElementById(`notesList_${eid}`)?.parentElement;
      if (wrap) await notes(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  /* ── CUSTOM FIELDS ──────────────────────────────────────────── */
  async function fields(container, entityType, entityId, canEdit = false) {
    const wrap = typeof container === 'string' ? document.getElementById(container) : container;
    if (!wrap) return;
    try {
      const list = await API.getFields(entityType, entityId);
      _renderFields(wrap, list, entityType, entityId, canEdit);
    } catch (e) {
      wrap.innerHTML = `<span style="color:var(--danger);font-size:11px">Failed: ${escHtml(e.message)}</span>`;
    }
  }

  function _renderFields(wrap, list, etype, eid, canEdit) {
    wrap.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Field</th><th>Value</th><th>Type</th>${canEdit ? '<th></th>' : ''}</tr></thead>
        <tbody id="fieldsBody_${eid}">
          ${list.map(f => `
            <tr>
              <td class="mono text-dim" style="font-size:11px">${escHtml(f.field_key)}</td>
              <td id="fval_${f.id}" style="font-size:12px">${escHtml(f.field_value)}</td>
              <td><span class="badge badge-grey" style="font-size:9px">${f.field_type}</span></td>
              ${canEdit ? `<td style="white-space:nowrap">
                <button class="btn btn-secondary btn-sm"
                        onclick="SUI._editField('${f.id}','${escHtml(f.field_value).replace(/'/g,"\\'")}')">Edit</button>
                <button class="btn btn-danger btn-sm"
                        onclick="SUI._deleteField('${f.id}','${etype}','${eid}')">✕</button>
              </td>` : ''}
            </tr>`).join('')}
          ${canEdit ? `
            <tr>
              <td><input class="form-input" id="nfKey_${eid}"
                         placeholder="field name" style="font-size:11px;padding:5px 8px"/></td>
              <td><input class="form-input" id="nfVal_${eid}"
                         placeholder="value"      style="font-size:11px;padding:5px 8px"/></td>
              <td><select class="form-select" id="nfType_${eid}" style="font-size:11px;padding:4px 6px">
                <option>TEXT</option><option>NUMBER</option><option>DATE</option><option>URL</option><option>JSON</option>
              </select></td>
              <td><button class="btn btn-primary btn-sm"
                          onclick="SUI._addField('${etype}','${eid}')">Add</button></td>
            </tr>` : ''}
        </tbody>
      </table>`;
  }

  async function _addField(etype, eid) {
    const key  = document.getElementById(`nfKey_${eid}`)?.value.trim();
    const val  = document.getElementById(`nfVal_${eid}`)?.value.trim();
    const type = document.getElementById(`nfType_${eid}`)?.value || 'TEXT';
    if (!key) { showToast('Field name required', 'error'); return; }
    try {
      await API.addField(etype, eid, { key, value: val, fieldType: type });
      const wrap = document.getElementById(`fieldsBody_${eid}`)?.closest('div') ||
                   document.getElementById(`fieldsBody_${eid}`)?.parentElement?.parentElement;
      if (wrap) await fields(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  async function _editField(fid, currentVal) {
    const newVal = prompt('Edit value:', currentVal);
    if (newVal === null) return;
    try {
      await API.updateField(fid, { value: newVal });
      const el = document.getElementById(`fval_${fid}`);
      if (el) el.textContent = newVal;
      showToast('Updated', 'success');
    } catch (e) { showToast(e.message, 'error'); }
  }

  async function _deleteField(fid, etype, eid) {
    if (!confirm('Delete this field?')) return;
    try {
      await API.deleteField(fid);
      const wrap = document.getElementById(`fieldsBody_${eid}`)?.parentElement?.parentElement;
      if (wrap) await fields(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  /* ── ATTACHMENTS ────────────────────────────────────────────── */
  async function attachments(container, entityType, entityId, canEdit = false) {
    const wrap = typeof container === 'string' ? document.getElementById(container) : container;
    if (!wrap) return;
    try {
      const list = await API.getAttachments(entityType, entityId);
      _renderAttachments(wrap, list, entityType, entityId, canEdit);
    } catch (e) {
      wrap.innerHTML = `<span style="color:var(--danger);font-size:11px">Failed: ${escHtml(e.message)}</span>`;
    }
  }

  const ATTACH_ICONS = { TEXT:'📄', IMAGE:'🖼', URL:'🔗', DATA:'💾', DOCUMENT:'📋' };

  function _renderAttachments(wrap, list, etype, eid, canEdit) {
    wrap.innerHTML = `
      ${canEdit ? `
        <div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-secondary btn-sm"
                  onclick="SUI._openAttachText('${etype}','${eid}')">+ Text Note</button>
          <button class="btn btn-secondary btn-sm"
                  onclick="SUI._openAttachUrl('${etype}','${eid}')">+ URL</button>
          <button class="btn btn-secondary btn-sm"
                  onclick="document.getElementById('attachFile_${eid}').click()">+ File</button>
          <input type="file" id="attachFile_${eid}" class="hidden"
                 onchange="SUI._attachFile('${etype}','${eid}',this)"/>
        </div>
        <div id="attachCompose_${eid}" class="hidden" style="margin-bottom:12px;background:var(--surface);border:1px solid var(--border);padding:12px">
          <input class="form-input" id="attachName_${eid}"
                 placeholder="Name / title" style="margin-bottom:6px"/>
          <textarea class="form-textarea" id="attachContent_${eid}"
                    placeholder="Content…" style="min-height:70px;margin-bottom:6px"></textarea>
          <div class="flex flex-gap-8">
            <button class="btn btn-secondary btn-sm"
                    onclick="document.getElementById('attachCompose_${eid}').classList.add('hidden')">Cancel</button>
            <button class="btn btn-primary btn-sm"
                    onclick="SUI._saveAttach('${etype}','${eid}')">Save</button>
          </div>
        </div>` : ''}
      <div id="attachList_${eid}">
        ${list.length ? list.map(a => `
          <div class="attach-item">
            <span class="attach-icon">${ATTACH_ICONS[a.attach_type] || '📄'}</span>
            <div class="attach-body">
              <div class="attach-name">${escHtml(a.name)}</div>
              <div class="attach-meta">${a.attach_type}${a.size_bytes ? ` · ${(a.size_bytes/1024).toFixed(1)} KB` : ''} · ${formatDate(a.created_at)}</div>
              ${a.description ? `<div class="attach-desc">${escHtml(a.description)}</div>` : ''}
              ${a.url ? `<a href="${escHtml(a.url)}" target="_blank" rel="noopener"
                           style="font-size:11px;color:var(--accent2)">${escHtml(a.url)}</a>` : ''}
            </div>
            ${canEdit ? `
              <button class="btn btn-danger btn-sm"
                      onclick="SUI._deleteAttach('${a.id}','${etype}','${eid}')">✕</button>` : ''}
          </div>`).join('')
        : '<div style="color:var(--text-dim);font-size:12px;padding:8px 0">No attachments.</div>'}
      </div>`;
  }

  function _openAttachText(etype, eid) {
    const c = document.getElementById(`attachCompose_${eid}`);
    if (c) {
      c.classList.remove('hidden');
      c.dataset.mode = 'TEXT';
      document.getElementById(`attachContent_${eid}`).placeholder = 'Write text content…';
    }
  }
  function _openAttachUrl(etype, eid) {
    const c = document.getElementById(`attachCompose_${eid}`);
    if (c) {
      c.classList.remove('hidden');
      c.dataset.mode = 'URL';
      document.getElementById(`attachContent_${eid}`).placeholder = 'https://…';
    }
  }

  async function _saveAttach(etype, eid) {
    const c       = document.getElementById(`attachCompose_${eid}`);
    const name    = document.getElementById(`attachName_${eid}`)?.value.trim() || 'Attachment';
    const content = document.getElementById(`attachContent_${eid}`)?.value.trim();
    const mode    = c?.dataset.mode || 'TEXT';
    try {
      await API.addAttachment(etype, eid, {
        name,
        content: mode !== 'URL' ? content : '',
        url:     mode === 'URL' ? content : '',
        attachType: mode,
      });
      c?.classList.add('hidden');
      showToast('Saved', 'success');
      const wrap = document.getElementById(`attachList_${eid}`)?.parentElement;
      if (wrap) await attachments(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  async function _attachFile(etype, eid, input) {
    const file = input.files[0]; if (!file) return;
    try {
      const b64     = await fileToB64(file);
      const isImage = file.type.startsWith('image/');
      await API.addAttachment(etype, eid, {
        name:        file.name,
        content:     b64,
        attachType:  isImage ? 'IMAGE' : 'DOCUMENT',
        mimeType:    file.type,
        description: `Uploaded ${today()}`,
      });
      showToast('File attached', 'success');
      const wrap = document.getElementById(`attachList_${eid}`)?.parentElement;
      if (wrap) await attachments(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  async function _deleteAttach(aid, etype, eid) {
    if (!confirm('Remove this attachment?')) return;
    try {
      await API.deleteAttachment(aid);
      const wrap = document.getElementById(`attachList_${eid}`)?.parentElement;
      if (wrap) await attachments(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  /* ── TIMELINE ───────────────────────────────────────────────── */
  const SEV_COLORS = { CRITICAL:'var(--danger)', HIGH:'var(--warning)', MEDIUM:'var(--accent)', LOW:'var(--green)' };

  function timeline(activities, opts = {}) {
    const { showPoi = false, linkItems = true } = opts;
    if (!activities || !activities.length) {
      return '<div style="color:var(--text-dim);font-size:12px;padding:12px 0">No activities recorded.</div>';
    }
    return `<div class="timeline">
      ${[...activities].sort((a, b) => (b.date || '').localeCompare(a.date || '')).map(a => `
        <div class="timeline-item">
          <div class="timeline-line">
            <div class="timeline-dot" style="background:${SEV_COLORS[a.severity] || 'var(--accent)'}"></div>
            <div class="timeline-connector"></div>
          </div>
          <div class="timeline-body">
            <div class="timeline-date">
              ${formatDate(a.date)}
              ${a.location ? `· <span style="color:var(--text)">${escHtml(a.location)}</span>` : ''}
              ${showPoi && (a.alias || a.poi_id) ? `· <a href="person.html?id=${a.poi_id}" style="color:var(--accent2)">${escHtml(a.alias || a.poi_id)}</a>` : ''}
              · by ${escHtml(a.reported_by || 'Unknown')}
            </div>
            <div class="timeline-title">
              ${sevBadge(a.severity)}
              <span style="margin-left:6px">${escHtml(a.type)}</span>
              ${linkItems ? `<a href="activity.html?id=${a.id}" style="color:var(--accent2);font-size:11px;margin-left:10px">View →</a>` : ''}
            </div>
            <div class="timeline-text">${escHtml(a.description)}</div>
          </div>
        </div>`).join('')}
    </div>`;
  }

  /* ── NETWORK GRAPH ──────────────────────────────────────────── */
  function networkGraph(canvasId, centerNode, connectedNodes) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const container = canvas.parentElement;
    canvas.width  = container.clientWidth  || 600;
    canvas.height = container.clientHeight || 360;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const RISK_COL = { CRITICAL:'#e84a4a', HIGH:'#e88a4a', MEDIUM:'#e8c44a', LOW:'#4ae87a', INACTIVE:'#6b7a90' };
    const all = [centerNode, ...connectedNodes];
    const positions = all.map((_, i) => {
      if (i === 0) return { x: W / 2, y: H / 2 };
      const angle = (2 * Math.PI / connectedNodes.length) * (i - 1) - Math.PI / 2;
      const r = Math.min(W, H) * 0.33;
      return { x: W / 2 + r * Math.cos(angle), y: H / 2 + r * Math.sin(angle) };
    });

    /* edges */
    connectedNodes.forEach((_, i) => {
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(74,143,232,0.3)';
      ctx.lineWidth   = 1.5;
      ctx.setLineDash([4, 3]);
      ctx.moveTo(positions[0].x, positions[0].y);
      ctx.lineTo(positions[i + 1].x, positions[i + 1].y);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    /* nodes */
    all.forEach((node, i) => {
      const pos    = positions[i];
      const isCenter = i === 0;
      const col    = RISK_COL[node.risk || node.risk_level || node.threat_level || 'MEDIUM'] || '#4a8fe8';
      const radius = isCenter ? 20 : 13;

      ctx.beginPath(); ctx.arc(pos.x, pos.y, radius + 5, 0, 2 * Math.PI);
      ctx.fillStyle = col + '12'; ctx.fill();

      ctx.beginPath(); ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = col + '25'; ctx.fill();
      ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.stroke();

      if (isCenter) {
        ctx.beginPath(); ctx.arc(pos.x, pos.y, 6, 0, 2 * Math.PI);
        ctx.fillStyle = col; ctx.fill();
      }

      ctx.fillStyle = col;
      ctx.font = `${isCenter ? 'bold ' : ''}${isCenter ? 12 : 10}px JetBrains Mono, monospace`;
      ctx.textAlign = 'center';
      ctx.fillText(String(node.alias || node.name || node.id || '?').slice(0, 16), pos.x, pos.y + radius + 14);
    });

    if (!connectedNodes.length) {
      ctx.fillStyle = 'rgba(107,122,144,0.5)';
      ctx.font = '12px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText('No connections recorded', W / 2, H / 2 + 36);
    }
  }

  /* ── MINI MAP ───────────────────────────────────────────────── */
  function initMiniMap(divId, points = [], opts = {}) {
    if (typeof maplibregl === 'undefined') return;
    const el = document.getElementById(divId);
    if (!el || el._sntMapInited) return;
    el._sntMapInited = true;

    const withCoords = points.filter(p => p.lat && p.lng);
    const center = opts.center || (withCoords.length ? [withCoords[0].lat, withCoords[0].lng] : [1, 35]);
    const zoom   = opts.zoom || (withCoords.length > 0 ? 5 : 3);

    const m = MAP.create(divId, { center, zoom, scrollZoom: false });

    const SEV = { CRITICAL:'#e84a4a', HIGH:'#e88a4a', MEDIUM:'#e8c44a', LOW:'#4ae87a' };
    m.on('load', () => {
      withCoords.forEach(p => {
        const col = SEV[p.severity || p.risk] || '#4a8fe8';
        const marker = MAP.circleMarker(m, p.lat, p.lng, { radius: 8, color: col, weight: 2 });
        if (p.popup) MAP.bindHoverPopup(marker, p.popup);
      });
      if (withCoords.length > 1) MAP.fitToPoints(m, withCoords.map(p => [p.lat, p.lng]), 20);
    });
    return m;
  }

  /* ── IMAGE GALLERY (multi-photo, any entity) ───────────────────
     Renders an upload control (analyst/admin only) + a responsive grid of
     thumbnails with lightbox-style click-to-enlarge and delete. */
  async function images(container, entityType, entityId, canEdit = false) {
    const wrap = typeof container === 'string' ? document.getElementById(container) : container;
    if (!wrap) return;
    wrap.innerHTML = '<span style="font-size:11px;color:var(--text-dim)">Loading photos…</span>';
    try {
      const list = await API.getImages(entityType, entityId);
      _renderImages(wrap, list, entityType, entityId, canEdit);
    } catch (e) {
      wrap.innerHTML = `<span style="color:var(--danger);font-size:11px">Failed to load photos: ${escHtml(e.message)}</span>`;
    }
  }

  function _renderImages(wrap, list, etype, eid, canEdit) {
    wrap.innerHTML = `
      ${canEdit ? `
        <div style="margin-bottom:12px">
          <button class="btn btn-secondary btn-sm" onclick="document.getElementById('imgFile_${eid}').click()">📷 Add Photo(s)</button>
          <input type="file" id="imgFile_${eid}" accept="image/*" multiple class="hidden"
                 onchange="SUI._uploadImages('${etype}','${eid}',this)"/>
        </div>` : ''}
      <div class="photo-grid" id="imgGrid_${eid}" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px">
        ${list.length ? list.map(img => `
          <div class="photo-thumb" style="position:relative;background:var(--panel2);border:1px solid var(--border);overflow:hidden">
            <img src="${img.content}" alt="${escHtml(img.description || img.name || '')}"
                 style="width:100%;aspect-ratio:4/3;object-fit:cover;display:block;cursor:pointer"
                 onclick="SUI._openLightbox('${img.content.replace(/'/g,"\\'")}','${escHtml(img.description||img.name||'').replace(/'/g,"\\'")}')"/>
            <div style="padding:5px 7px;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
              ${escHtml(img.description || img.name || 'Untitled')}
            </div>
            ${canEdit ? `
              <button onclick="SUI._deleteImage('${img.id}','${etype}','${eid}')"
                      style="position:absolute;top:4px;right:4px;background:rgba(0,0,0,.75);border:none;color:var(--danger);cursor:pointer;padding:2px 6px;font-size:11px;border-radius:2px">✕</button>` : ''}
          </div>`).join('')
        : '<div style="grid-column:1/-1;color:var(--text-dim);font-size:12px;padding:10px 0">No photographs on file.</div>'}
      </div>`;
  }

  async function _uploadImages(etype, eid, input) {
    const files = Array.from(input.files || []);
    if (!files.length) return;
    let okCount = 0;
    for (const file of files) {
      try {
        const b64 = await fileToB64(file);
        const caption = files.length === 1 ? (prompt('Caption for this photo (optional):', '') || '') : file.name;
        await API.addImage(etype, eid, { name: file.name, content: b64, mimeType: file.type, caption });
        okCount++;
      } catch (e) { showToast(`Failed to upload ${file.name}: ${e.message}`, 'error'); }
    }
    if (okCount) showToast(`${okCount} photo(s) uploaded`, 'success');
    input.value = '';
    const wrap = document.getElementById(`imgGrid_${eid}`)?.parentElement;
    if (wrap) await images(wrap, etype, eid, true);
  }

  async function _deleteImage(iid, etype, eid) {
    if (!confirm('Remove this photo?')) return;
    try {
      await API.deleteImage(iid);
      const wrap = document.getElementById(`imgGrid_${eid}`)?.parentElement;
      if (wrap) await images(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  function _openLightbox(src, caption) {
    let overlay = document.getElementById('sntLightbox');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'sntLightbox';
      overlay.style.cssText = 'position:fixed;inset:0;z-index:9000;background:rgba(0,0,0,.88);display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:zoom-out;padding:40px';
      overlay.onclick = () => overlay.remove();
      document.body.appendChild(overlay);
    }
    overlay.innerHTML = `
      <img src="${src}" style="max-width:90vw;max-height:80vh;object-fit:contain;box-shadow:0 8px 40px rgba(0,0,0,.6)"/>
      ${caption ? `<div style="color:#fff;font-family:'JetBrains Mono',monospace;font-size:12px;margin-top:14px;text-align:center">${escHtml(caption)}</div>` : ''}
      <div style="color:rgba(255,255,255,.5);font-family:'JetBrains Mono',monospace;font-size:10px;margin-top:8px">Click anywhere to close</div>`;
  }

  /* ── MULTI-COORDINATE LOCATIONS (any entity) ───────────────────
     Lets an analyst attach more than one lat/lng to a person, group, or
     activity (e.g. a person's known residence + last-sighting point, or a
     group's multiple safehouses). Renders a small manage-list; the
     detail-page map renderer reads these via API.getLocations() alongside
     whatever primary coordinates the entity/activities already carry. */
  async function locations(container, entityType, entityId, canEdit = false) {
    const wrap = typeof container === 'string' ? document.getElementById(container) : container;
    if (!wrap) return;
    wrap.innerHTML = '<span style="font-size:11px;color:var(--text-dim)">Loading locations…</span>';
    try {
      const list = await API.getLocations(entityType, entityId);
      _renderLocations(wrap, list, entityType, entityId, canEdit);
    } catch (e) {
      wrap.innerHTML = `<span style="color:var(--danger);font-size:11px">Failed to load locations: ${escHtml(e.message)}</span>`;
    }
  }

  function _renderLocations(wrap, list, etype, eid, canEdit) {
    wrap.innerHTML = `
      ${canEdit ? `
        <div id="locCompose_${eid}" style="display:none;margin-bottom:12px;background:var(--surface);border:1px solid var(--border);padding:12px">
          <div class="form-row" style="margin-bottom:8px">
            <input class="form-input" id="locLabel_${eid}" placeholder="Label (e.g. Known residence)"/>
            <input class="form-input" id="locDate_${eid}" type="date" placeholder="Date observed"/>
          </div>
          <div class="form-row" style="margin-bottom:8px">
            <input class="form-input" id="locLat_${eid}" type="number" step="any" placeholder="Latitude"/>
            <input class="form-input" id="locLng_${eid}" type="number" step="any" placeholder="Longitude"/>
          </div>
          <textarea class="form-textarea" id="locNote_${eid}" placeholder="Note (optional)" style="min-height:60px;margin-bottom:8px"></textarea>
          <div class="flex flex-gap-8">
            <button class="btn btn-secondary btn-sm" onclick="document.getElementById('locCompose_${eid}').style.display='none'">Cancel</button>
            <button class="btn btn-primary btn-sm" onclick="SUI._saveLocation('${etype}','${eid}')">Save Location</button>
          </div>
        </div>
        <div style="margin-bottom:12px">
          <button class="btn btn-secondary btn-sm"
                  onclick="const c=document.getElementById('locCompose_${eid}');c.style.display=c.style.display==='none'?'block':'none'">
            ${iPlus} Add Coordinate
          </button>
        </div>` : ''}
      <div id="locList_${eid}">
        ${list.length ? list.map(l => `
          <div class="note-card" style="border-left:3px solid var(--accent2)">
            <div class="note-header">
              <span class="note-icon">📍</span>
              <span class="note-type-badge">${l.lat.toFixed(4)}, ${l.lng.toFixed(4)}</span>
              ${l.date_observed ? `<span class="note-date">${formatDate(l.date_observed)}</span>` : ''}
              ${canEdit ? `<button class="btn btn-danger btn-sm" style="margin-left:auto;padding:3px 8px"
                  onclick="SUI._deleteLocation('${l.id}','${etype}','${eid}')">✕</button>` : ''}
            </div>
            ${l.label ? `<div class="note-title">${escHtml(l.label)}</div>` : ''}
            ${l.note ? `<div class="note-body">${escHtml(l.note)}</div>` : ''}
          </div>`).join('')
        : '<div style="color:var(--text-dim);font-size:12px;padding:10px 0">No additional coordinates recorded.</div>'}
      </div>`;
  }

  async function _saveLocation(etype, eid) {
    const lat = parseFloat(document.getElementById(`locLat_${eid}`)?.value);
    const lng = parseFloat(document.getElementById(`locLng_${eid}`)?.value);
    if (isNaN(lat) || isNaN(lng)) { showToast('Valid latitude and longitude are required', 'error'); return; }
    try {
      await API.addLocation(etype, eid, {
        lat, lng,
        label: document.getElementById(`locLabel_${eid}`)?.value.trim() || '',
        note:  document.getElementById(`locNote_${eid}`)?.value.trim() || '',
        dateObserved: document.getElementById(`locDate_${eid}`)?.value || '',
      });
      showToast('Location added', 'success');
      const wrap = document.getElementById(`locList_${eid}`)?.parentElement;
      if (wrap) await locations(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  async function _deleteLocation(lid, etype, eid) {
    if (!confirm('Remove this coordinate?')) return;
    try {
      await API.deleteLocation(lid);
      const wrap = document.getElementById(`locList_${eid}`)?.parentElement;
      if (wrap) await locations(wrap, etype, eid, true);
    } catch (e) { showToast(e.message, 'error'); }
  }

  /* ── DATE-RANGE SLIDER ──────────────────────────────────────────
     Self-contained dual-handle date slider. Given an array of dated items
     (activities), renders a slider spanning their min/max date and a
     readout. On every change it calls opts.onChange(fromISO, toISO, filteredItems).
     Designed to be dropped into any detail page's GIS / Timeline tab. */
  function dateSlider(container, dateItems, opts = {}) {
    const wrap = typeof container === 'string' ? document.getElementById(container) : container;
    if (!wrap) return null;

    const dates = (dateItems || []).map(i => i.date).filter(Boolean).sort();
    if (!dates.length) {
      wrap.innerHTML = '';
      return { from: null, to: null, filter: items => items };
    }

    const minDate = dates[0];
    const maxDate = dates[dates.length - 1];
    const minTs = new Date(minDate).getTime();
    const maxTs = new Date(maxDate).getTime();
    const spanMs = Math.max(1, maxTs - minTs);
    const uid = 'ds_' + Math.random().toString(36).slice(2, 8);

    wrap.innerHTML = `
      <div class="date-slider" id="${uid}">
        <div class="date-slider-readout">
          <span id="${uid}_fromLabel">${formatDate(minDate)}</span>
          <span class="date-slider-readout-sep">→</span>
          <span id="${uid}_toLabel">${formatDate(maxDate)}</span>
          <span class="date-slider-count" id="${uid}_count">${dateItems.length} of ${dateItems.length}</span>
          ${minDate !== maxDate ? `<button class="btn btn-secondary btn-sm" id="${uid}_reset" style="margin-left:auto">Reset</button>` : ''}
        </div>
        <div class="date-slider-track-wrap">
          <div class="date-slider-track"></div>
          <div class="date-slider-range" id="${uid}_range"></div>
          ${dateItems.length <= 60 ? dates.map(d => {
            const pct = ((new Date(d).getTime() - minTs) / spanMs) * 100;
            return `<div class="date-slider-tick" style="left:${pct}%"></div>`;
          }).join('') : ''}
          <input type="range" id="${uid}_from" class="date-slider-input date-slider-input-from"
                 min="0" max="1000" value="0" ${minDate===maxDate?'disabled':''}/>
          <input type="range" id="${uid}_to" class="date-slider-input date-slider-input-to"
                 min="0" max="1000" value="1000" ${minDate===maxDate?'disabled':''}/>
        </div>
      </div>`;

    const fromInput = document.getElementById(`${uid}_from`);
    const toInput   = document.getElementById(`${uid}_to`);
    const fromLabel = document.getElementById(`${uid}_fromLabel`);
    const toLabel   = document.getElementById(`${uid}_toLabel`);
    const countEl   = document.getElementById(`${uid}_count`);
    const rangeEl   = document.getElementById(`${uid}_range`);
    const resetBtn  = document.getElementById(`${uid}_reset`);

    const state = { fromTs: minTs, toTs: maxTs };

    function tsFromSlider(val) { return minTs + (spanMs * (val / 1000)); }
    function isoDate(ts) { return new Date(ts).toISOString().slice(0, 10); }

    function applyFilter() {
      const fromIso = isoDate(state.fromTs);
      const toIso   = isoDate(state.toTs);
      const filtered = dateItems.filter(i => i.date && i.date >= fromIso && i.date <= toIso);
      fromLabel.textContent = formatDate(fromIso);
      toLabel.textContent   = formatDate(toIso);
      countEl.textContent   = `${filtered.length} of ${dateItems.length}`;
      const fromPct = ((state.fromTs - minTs) / spanMs) * 100;
      const toPct   = ((state.toTs   - minTs) / spanMs) * 100;
      rangeEl.style.left  = fromPct + '%';
      rangeEl.style.right = (100 - toPct) + '%';
      if (opts.onChange) opts.onChange(fromIso, toIso, filtered);
      return filtered;
    }

    fromInput?.addEventListener('input', () => {
      let v = parseInt(fromInput.value);
      const toV = parseInt(toInput.value);
      if (v > toV) { v = toV; fromInput.value = v; }
      state.fromTs = tsFromSlider(v);
      applyFilter();
    });
    toInput?.addEventListener('input', () => {
      let v = parseInt(toInput.value);
      const fromV = parseInt(fromInput.value);
      if (v < fromV) { v = fromV; toInput.value = v; }
      state.toTs = tsFromSlider(v);
      applyFilter();
    });
    resetBtn?.addEventListener('click', () => {
      fromInput.value = 0; toInput.value = 1000;
      state.fromTs = minTs; state.toTs = maxTs;
      applyFilter();
    });

    applyFilter();

    return {
      get from() { return isoDate(state.fromTs); },
      get to()   { return isoDate(state.toTs); },
      filter(items) {
        const f = isoDate(state.fromTs), t = isoDate(state.toTs);
        return (items || []).filter(i => i.date && i.date >= f && i.date <= t);
      },
    };
  }

  /* expose everything including private helpers called from inline HTML */
  // ── Narrative AI summary (Phase 2) ──────────────────────────────────────
  const _summaryCache = {};   // "type:id" -> markdown, so the print report can reuse it

  /* Minimal, safe markdown -> HTML for the assessment (## headings, **bold**,
     *italic*, - bullets, paragraphs). Escapes HTML before applying inline marks. */
  function mdToHtml(md) {
    if (!md) return '';
    const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const inline = s => esc(s)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>');
    let html = '', inList = false;
    const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };
    for (const raw of md.split('\n')) {
      const line = raw.trim();
      if (!line) { closeList(); continue; }
      let m;
      if ((m = line.match(/^#{1,3}\s+(.*)/))) { closeList(); html += `<h4 class="ai-h">${inline(m[1])}</h4>`; }
      else if ((m = line.match(/^[-*]\s+(.*)/))) { if (!inList) { html += '<ul class="ai-ul">'; inList = true; } html += `<li>${inline(m[1])}</li>`; }
      else { closeList(); html += `<p class="ai-p">${inline(line)}</p>`; }
    }
    closeList();
    return html;
  }

  /* Markdown of the currently-loaded summary, for embedding in printed reports. */
  function summaryText(entityType, entityId) {
    return _summaryCache[`${entityType}:${entityId}`] || null;
  }

  async function summary(container, entityType, entityId, canEdit = false) {
    const wrap = typeof container === 'string' ? document.getElementById(container) : container;
    if (!wrap) return;
    wrap.innerHTML = '<span style="font-size:11px;color:var(--text-dim)">Loading assessment…</span>';
    try {
      const base = entityType === 'group' ? 'groups' : 'persons';
      const d = await API.get(`/api/${base}/${entityId}/summary`);
      _renderSummary(wrap, entityType, entityId, canEdit, d);
    } catch (e) {
      wrap.innerHTML = `<span style="color:var(--danger);font-size:11px">Failed to load assessment: ${escHtml(e.message)}</span>`;
    }
  }

  function _renderSummary(wrap, etype, eid, canEdit, d) {
    const has = !!(d && d.summary);
    _summaryCache[`${etype}:${eid}`] = has ? d.summary : null;
    const meta = has
      ? `generated ${new Date(d.generatedAt).toLocaleString()}${d.model ? ' · ' + escHtml(d.model) : ''}`
      : '';
    wrap.innerHTML = `
      <div class="ai-summary-head">
        <span class="ai-summary-meta mono">${meta}</span>
        <span class="badge badge-amber" style="font-size:9px" title="Unlike the rest of SENTINEL, this feature calls the Anthropic API and requires internet + a configured key.">⚠ Requires internet</span>
        ${canEdit ? `<button class="btn btn-secondary btn-sm" id="aiGenBtn_${etype}_${eid}"
                       onclick="SUI._genSummary('${etype}','${eid}',this)">${has ? 'Regenerate' : 'Generate'}</button>` : ''}
      </div>
      <div class="ai-summary" id="aiBody_${etype}_${eid}">
        ${has ? mdToHtml(d.summary)
              : `<div class="ai-empty">No assessment generated yet.${canEdit ? " Click Generate to build one from this subject's dossier." : ''}</div>`}
      </div>`;
  }

  async function _genSummary(etype, eid, btn) {
    const base = etype === 'group' ? 'groups' : 'persons';
    const body = document.getElementById(`aiBody_${etype}_${eid}`);
    if (btn) { btn.disabled = true; btn.textContent = 'Generating…'; }
    if (body) body.innerHTML = '<span style="color:var(--text-dim);font-size:12px">Generating intelligence assessment… this can take several seconds.</span>';
    try {
      const d = await API.post(`/api/${base}/${eid}/summary`);
      _summaryCache[`${etype}:${eid}`] = d.summary || null;
      if (body) body.innerHTML = mdToHtml(d.summary);
      const meta = btn ? btn.closest('.ai-summary-head')?.querySelector('.ai-summary-meta') : null;
      if (meta) meta.textContent = `generated ${new Date(d.generatedAt).toLocaleString()}${d.model ? ' · ' + d.model : ''}`;
      if (btn) btn.textContent = 'Regenerate';
      showToast('Assessment generated', 'success');
    } catch (e) {
      if (body) body.innerHTML = `<div class="ai-empty" style="color:var(--danger)">Generation failed: ${escHtml(e.message)}</div>`;
      if (btn) btn.textContent = _summaryCache[`${etype}:${eid}`] ? 'Regenerate' : 'Generate';
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  /* ── COORDINATE PICKER (any lat/lng field pair) ─────────────────
     Opens a click-to-place MapLibre map in a modal. Used to fill a pair of
     number inputs (latId/lngId) without typing raw coordinates. */
  let _pickMapObj = null, _pickMarker = null;

  function pickCoords(latId, lngId) {
    if (typeof maplibregl === 'undefined') return showToast('Map library not loaded', 'error');
    const latInput = document.getElementById(latId);
    const lngInput = document.getElementById(lngId);
    const startLat = parseFloat(latInput?.value) || -1.2864;
    const startLng = parseFloat(lngInput?.value) || 36.8172;
    const hasStart = latInput?.value && lngInput?.value;

    let overlay = document.getElementById('sntCoordPicker');
    if (overlay) overlay.remove();
    overlay = document.createElement('div');
    overlay.id = 'sntCoordPicker';
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal-box" style="max-width:640px">
        <div class="modal-header"><h3>Plot Coordinates</h3>
          <button class="btn btn-secondary btn-sm" id="pcCancel">✕</button></div>
        <div class="modal-body">
          <div style="font-size:11px;color:var(--text-dim);margin-bottom:8px">Click the map to place a pin, or drag it to adjust.</div>
          <div id="pcMap" style="height:360px;border:1px solid var(--border)"></div>
          <div style="margin-top:10px;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-hi)" id="pcCoordsOut">
            ${hasStart ? `${startLat.toFixed(5)}, ${startLng.toFixed(5)}` : 'No pin placed yet'}
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="pcClear">Clear</button>
          <button class="btn btn-secondary" id="pcCancel2">Cancel</button>
          <button class="btn btn-primary" id="pcUse" ${hasStart ? '' : 'disabled'}>Use This Location</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    let picked = hasStart ? { lat: startLat, lng: startLng } : null;

    const close = () => {
      overlay.remove();
      if (_pickMapObj) _pickMapObj.remove();
      _pickMapObj = null; _pickMarker = null;
    };
    overlay.querySelector('#pcCancel').onclick = close;
    overlay.querySelector('#pcCancel2').onclick = close;
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });

    setTimeout(() => {
      _pickMapObj = MAP.create('pcMap', { center: [startLat, startLng], zoom: hasStart ? 10 : 5, scrollZoom: false });

      const setPin = (lat, lng) => {
        picked = { lat, lng };
        if (_pickMarker) _pickMarker.setLngLat([lng, lat]);
        else {
          _pickMarker = new maplibregl.Marker({ draggable: true }).setLngLat([lng, lat]).addTo(_pickMapObj);
          _pickMarker.on('dragend', () => {
            const ll = _pickMarker.getLngLat();
            setPin(ll.lat, ll.lng);
          });
        }
        overlay.querySelector('#pcCoordsOut').textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        overlay.querySelector('#pcUse').disabled = false;
      };
      if (hasStart) setPin(startLat, startLng);
      _pickMapObj.on('click', e => setPin(e.lngLat.lat, e.lngLat.lng));
    }, 30);

    overlay.querySelector('#pcClear').onclick = () => {
      picked = null;
      if (_pickMarker) { _pickMarker.remove(); _pickMarker = null; }
      overlay.querySelector('#pcCoordsOut').textContent = 'No pin placed yet';
      overlay.querySelector('#pcUse').disabled = true;
    };
    overlay.querySelector('#pcUse').onclick = () => {
      if (!picked) return;
      if (latInput) latInput.value = picked.lat.toFixed(6);
      if (lngInput) lngInput.value = picked.lng.toFixed(6);
      close();
    };
  }

  return {
    tags, notes, fields, attachments, images, locations, timeline, networkGraph, initMiniMap, dateSlider,
    summary, summaryText, mdToHtml, pickCoords,
    _removeTag, _openTagInput, _addTag,
    _saveNote, _deleteNote,
    _addField, _editField, _deleteField,
    _openAttachText, _openAttachUrl, _saveAttach, _attachFile, _deleteAttach,
    _uploadImages, _deleteImage, _openLightbox,
    _saveLocation, _deleteLocation,
    _genSummary,
  };
})();

/* inject CSS keyframes if not already present */
(function injectStyles() {
  if (document.getElementById('snt-runtime-styles')) return;
  const s = document.createElement('style');
  s.id = 'snt-runtime-styles';
  s.textContent = `
    @keyframes fadeInUp {
      from { opacity:0; transform:translateY(8px); }
      to   { opacity:1; transform:translateY(0); }
    }
  `;
  document.head.appendChild(s);
})();
