/* Shared cross-app chrome JS for FAE Field Forms pages.
   - Hydrates the user badge from localStorage SSO session (mirrored from
     .40ac.us cookie, same key the portal/SCADA/Analyst use).
   - Polls prices.json (15 min) to keep WTI/Waha ticker fresh. */

(function () {
  var SESSION_KEY = 'fae_user';

  // Mirror SSO cookie ↔ localStorage so a login on portal/scada/analyst
  // carries over to form pages.
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { applyBadge(); refreshPrices(); });
  } else {
    applyBadge(); refreshPrices();
  }
  setInterval(refreshPrices, 15 * 60 * 1000);
})();
