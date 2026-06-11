/* Shared cross-app chrome JS for FAE Field Forms pages.
   - Mirrors SSO cookie ↔ localStorage so a login on portal/scada/analyst
     carries over to form pages.
   - Hydrates the user badge.
   - Polls prices.json (15 min) to keep WTI/Waha ticker fresh.
   - Auto-injects burger into the header.
   - Auto-injects the shared sidebar (FORMS + REPORTS) into every page
     that has <header class="appchrome">, with the current page marked active. */

(function () {
  var SESSION_KEY = 'fae_user';

  /* ── SSO mirror ── */
  try {
    var m = document.cookie.match(/(?:^|;\s*)fae40_sso=([^;]+)/);
    if (m && !localStorage.getItem(SESSION_KEY))
      localStorage.setItem(SESSION_KEY, decodeURIComponent(m[1]));
  } catch (e) {}

  function applyBadge() {
    try {
      var raw = localStorage.getItem(SESSION_KEY);
      if (!raw) return;
      var s = JSON.parse(raw);
      if (!s || (s.expires && s.expires < Date.now())) return;
      var badge = document.getElementById('user-badge');
      if (!badge) return;
      badge.style.display = 'flex';
      var nm = document.getElementById('user-name');
      if (nm) nm.textContent = 'Welcome, ' + (s.displayName || s.email || '');
      var av = document.getElementById('user-avatar');
      if (av) {
        if (s.picture) { av.src = s.picture; av.style.display = ''; }
        else { av.style.display = 'none'; }
      }
    } catch (e) {}
  }

  function fmtPrice(p) {
    return p < 0 ? '-$' + Math.abs(p).toFixed(3) : '$' + p.toFixed(2);
  }
  function setChg(elId, chg) {
    var el = document.getElementById(elId);
    if (!el) return;
    if (chg == null) { el.outerHTML = '<span id="' + elId + '" class="price-chg"></span>'; return; }
    var cls = chg >= 0 ? 'price-up' : 'price-down';
    var arrow = chg >= 0 ? '▲' : '▼';
    el.outerHTML = '<span id="' + elId + '" class="price-chg ' + cls + '">' + arrow + ' ' + Math.abs(chg).toFixed(2) + '</span>';
  }
  function setText(id, v) {
    var el = document.getElementById(id);
    if (el) el.textContent = v;
  }
  function refreshPrices() {
    try {
      fetch('prices.json', { cache: 'no-cache' })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
        .then(function (p) {
          if (!p) return;
          if (p.wti) { setText('wti-val', fmtPrice(p.wti.price));
                      setChg('wti-chg', p.wti.chg);
                      setText('wti-date', p.wti.date || ''); }
          if (p.waha) { setText('waha-val', fmtPrice(p.waha.price));
                       setChg('waha-chg', p.waha.chg);
                       setText('waha-date', p.waha.date || ''); }
        })
        .catch(function () {});
    } catch (e) {}
  }

  window.faeSignOut = function () {
    try { localStorage.removeItem(SESSION_KEY); } catch (e) {}
    try { document.cookie = 'fae40_sso=;domain=.40ac.us;path=/;max-age=0;Secure;SameSite=Lax'; } catch (e) {}
    location.reload();
  };

  /* ── Sidebar + burger injection ── */

  // Single source of truth for the sidebar menu. Adding a new form here
  // adds the entry to every page automatically.
  var NAV = [
    { sec: 'Dashboard', items: [
      { href: 'index.html', label: 'Activity Dashboard',
        ic: '<svg viewBox="0 0 24 24"><rect x="3" y="11" width="4" height="9" fill="#2b3036"/><rect x="10" y="6" width="4" height="14" fill="#4a5158"/><rect x="17" y="14" width="4" height="6" fill="#9aa0a6"/></svg>' },
    ]},
    { sec: 'Forms', items: [
      { href: 'my-avo.html', label: 'My AVO Inspections',
        ic: '<img src="avo.png?v=2" alt="" style="width:24px;height:24px;display:block">' },
      { href: 'gwi.html', label: 'Gas Well Inspection',
        ic: '<svg viewBox="0 0 24 24"><path d="M12 2C10 5 7 7 7 11c0 2.76 2.24 5 5 5s5-2.24 5-5c0-1.5-.6-2.8-1.5-3.8C15 8.5 14 10 12 10c1-2 1.5-5 0-8z" fill="#e67e22"/></svg>' },
      { href: 'fap.html', label: 'Fluid Levels (FAP)',
        ic: '<svg viewBox="0 0 24 24"><rect x="9" y="19" width="6" height="2" rx="0.5" fill="#555"/><rect x="11.2" y="11" width="1.6" height="8" fill="#555"/><polygon points="10,11 14,11 12,6" fill="#666"/><line x1="5" y1="9" x2="19" y2="11" stroke="#444" stroke-width="1.8" stroke-linecap="round"/></svg>' },
      { href: 'pumpup.html', label: 'Pump Up Entry',
        ic: '<svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="8" fill="#e8e8e8" stroke="#888" stroke-width="1.2"/><circle cx="12" cy="13" r="6" fill="#fff" stroke="#aaa" stroke-width="0.8"/><line x1="12" y1="13" x2="15" y2="9" stroke="#c0392b" stroke-width="1.5" stroke-linecap="round"/><circle cx="12" cy="13" r="1" fill="#555"/></svg>' },
      { href: 'wellsite.html', label: 'Well Site Inspection', ic: '🔍' },
      { href: 'facility.html', label: 'Facility Inspection',
        ic: '<svg viewBox="0 0 24 24"><ellipse cx="12" cy="7" rx="7" ry="3" fill="#5a8fa8"/><rect x="5" y="7" width="14" height="10" fill="#4a7f98"/><ellipse cx="12" cy="17" rx="7" ry="3" fill="#3a6f88"/></svg>' },
      { href: 'grounding.html', label: 'Wellhead Grounding', ic: '⚡' },
      { href: 'https://forms.gle/PKeZWY5mUHxjVJXZA', label: 'Spare Vessels', extern: true,
        ic: '<svg viewBox="0 0 24 24"><rect x="2" y="8" width="16" height="8" rx="4" fill="#5a8fa8"/><ellipse cx="18" cy="12" rx="2" ry="4" fill="#4a7f98"/><circle cx="4" cy="12" r="2" fill="#c0392b" opacity="0.85"/></svg>' },
    ]},
    { sec: 'Reports', items: [
      { href: 'avo-report.html', label: 'AVO Inspections',
        ic: '<img src="avo.png?v=2" alt="" style="width:24px;height:24px;display:block">' },
      { href: 'spare-vessels.html', label: 'Spare Vessels View', ic: '📋' },
    ]},
  ];

  function currentPage() {
    var p = (location.pathname || '').split('/').pop().toLowerCase();
    if (!p || p === '') return 'index.html';
    return p;
  }

  function injectChrome() {
    var header = document.querySelector('header.appchrome');
    if (!header) return;

    /* Burger — leftmost in the header */
    if (!header.querySelector('.burger')) {
      var burger = document.createElement('button');
      burger.type = 'button';
      burger.className = 'burger';
      burger.setAttribute('aria-label', 'Menu');
      burger.innerHTML = '&#9776;';
      burger.addEventListener('click', function () {
        document.body.classList.toggle('sb-open');
      });
      header.insertBefore(burger, header.firstChild);
    }

    /* Sidebar + scrim — injected once, after the header */
    if (!document.querySelector('.appchrome-sidebar')) {
      var here = currentPage();
      var html = '';
      NAV.forEach(function (group) {
        html += '<div class="nav-sec">' + group.sec + '</div>';
        group.items.forEach(function (item) {
          var fname = (item.href.split('/').pop() || '').toLowerCase();
          var active = (fname && fname === here) ? ' on' : '';
          var tgt = item.extern ? ' target="_blank" rel="noopener"' : '';
          var ic = item.ic || '';
          // Wrap raw text icon in nothing; SVG / emoji both go straight in.
          html += '<a class="nav-i' + active + '" href="' + item.href + '"' + tgt + '>'
                + '<span class="ic">' + ic + '</span>' + item.label + '</a>';
        });
      });

      var aside = document.createElement('aside');
      aside.className = 'appchrome-sidebar';
      aside.innerHTML = '<nav>' + html + '</nav>';

      var scrim = document.createElement('div');
      scrim.className = 'appchrome-scrim';

      var close = function () { document.body.classList.remove('sb-open'); };
      scrim.addEventListener('click', close);

      header.parentNode.insertBefore(aside, header.nextSibling);
      header.parentNode.insertBefore(scrim, aside.nextSibling);

      // ESC closes the sidebar.
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') close();
      });
    }
  }

  function init() {
    injectChrome();
    applyBadge();
    refreshPrices();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  setInterval(refreshPrices, 15 * 60 * 1000);
})();
