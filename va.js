/**
 * PCDeck — Vercel Web Analytics Privacy & Owner Visit Exclusion
 * Bulletproof mechanism to prevent developer, creator, and owner visits from
 * skewing Vercel Web Analytics metrics.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'pcdeck_no_track';
  var VA_DISABLE_KEY = 'va-disable';

  // Helper: check cookie
  function getCookie(name) {
    try {
      var match = document.cookie.match(new RegExp('(^|;\\s*)(' + name + ')=([^;]*)'));
      return match ? decodeURIComponent(match[3]) : null;
    } catch (e) {
      return null;
    }
  }

  // Helper: set persistent cookie (10 years)
  function setCookie(name, val) {
    try {
      document.cookie = name + '=' + encodeURIComponent(val) + '; path=/; max-age=315360000; SameSite=Lax';
    } catch (e) {}
  }

  // Helper: remove cookie
  function removeCookie(name) {
    try {
      document.cookie = name + '=; path=/; max-age=0; SameSite=Lax';
    } catch (e) {}
  }

  // 1. Inspect URL parameters and Hash
  var params = null;
  try {
    params = new URLSearchParams(window.location.search);
  } catch (e) {}

  var hash = (window.location.hash || '').toLowerCase();

  var shouldDisable = false;
  var shouldEnable = false;

  if (params) {
    if (params.get('notrack') === '1' || 
        params.get('admin') === '1' || 
        params.get('dev') === '1' || 
        params.get('owner') === '1' || 
        params.get('ignore') === '1' || 
        params.get('me') === '1') {
      shouldDisable = true;
    } else if (params.get('track') === '1' || params.get('enable_analytics') === '1') {
      shouldEnable = true;
    }
  }

  if (hash === '#admin' || hash === '#notrack' || hash === '#dev' || hash === '#owner' || hash === '#ignore') {
    shouldDisable = true;
  }

  // On dedicated exclusion page (/ignore-my-visit/ or /admin/) automatically block
  if (window.location.pathname.indexOf('/ignore-my-visit') !== -1 || window.location.pathname.indexOf('/admin') !== -1) {
    shouldDisable = true;
  }

  if (shouldDisable) {
    try {
      localStorage.setItem(STORAGE_KEY, '1');
      localStorage.setItem(VA_DISABLE_KEY, '1');
      sessionStorage.setItem(STORAGE_KEY, '1');
    } catch (e) {}
    setCookie(STORAGE_KEY, '1');
    setCookie(VA_DISABLE_KEY, '1');
    showNotification('🛡️ PCDeck: Owner visit restriction ENABLED. Vercel will ignore visits from this device.');
  } else if (shouldEnable) {
    try {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(VA_DISABLE_KEY);
      sessionStorage.removeItem(STORAGE_KEY);
    } catch (e) {}
    removeCookie(STORAGE_KEY);
    removeCookie(VA_DISABLE_KEY);
    showNotification('PCDeck: Analytics re-enabled on this device.');
  }

  // 2. Determine if currently blocked across any storage layer
  var isBlocked = false;
  try {
    if (localStorage.getItem(STORAGE_KEY) === '1' || 
        localStorage.getItem(VA_DISABLE_KEY) === '1' || 
        sessionStorage.getItem(STORAGE_KEY) === '1') {
      isBlocked = true;
    }
  } catch (e) {}

  if (!isBlocked && (getCookie(STORAGE_KEY) === '1' || getCookie(VA_DISABLE_KEY) === '1')) {
    isBlocked = true;
    // Re-sync to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, '1');
      localStorage.setItem(VA_DISABLE_KEY, '1');
    } catch (e) {}
  }

  // Localhost & private network bypass
  var hostname = (window.location.hostname || '').toLowerCase();
  if (hostname === 'localhost' || 
      hostname === '127.0.0.1' || 
      hostname.startsWith('192.168.') || 
      hostname.startsWith('10.') || 
      hostname.startsWith('172.16.')) {
    isBlocked = true;
  }

  // Helper: Automated Bot & Headless Scraper Detection
  function isBotEnvironment() {
    try {
      if (navigator.webdriver) return true;
      if (window._phantom || window.__nightmare || window.callPhantom) return true;
      if (window.outerWidth === 0 && window.outerHeight === 0) return true;
      var ua = (navigator.userAgent || '').toLowerCase();
      if (/headlesschrome|phantomjs|puppeteer|playwright|selenium|bytespider|semrushbot|ahrefsbot|mj12bot|dotbot|petalbot|dataforseo|screaming frog|seobility|crawler|spider/i.test(ua)) {
        return true;
      }
    } catch (e) {}
    return false;
  }

  var isBot = isBotEnvironment();
  if (isBot) {
    isBlocked = true;
  }

  // 3. Expose global toggle function for 1-click UI button
  window.togglePcdeckAnalytics = function () {
    var currentlyBlocked = false;
    try {
      currentlyBlocked = (localStorage.getItem(STORAGE_KEY) === '1' || getCookie(STORAGE_KEY) === '1');
    } catch (e) {}

    if (currentlyBlocked) {
      // Re-enable
      try {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(VA_DISABLE_KEY);
        sessionStorage.removeItem(STORAGE_KEY);
      } catch (e) {}
      removeCookie(STORAGE_KEY);
      removeCookie(VA_DISABLE_KEY);
      showNotification('PCDeck Analytics: Tracking RE-ENABLED for this device.');
      updateUI(false);
    } else {
      // Block
      try {
        localStorage.setItem(STORAGE_KEY, '1');
        localStorage.setItem(VA_DISABLE_KEY, '1');
        sessionStorage.setItem(STORAGE_KEY, '1');
      } catch (e) {}
      setCookie(STORAGE_KEY, '1');
      setCookie(VA_DISABLE_KEY, '1');
      showNotification('🛡️ PCDeck Analytics: Tracking BLOCKED for this device! Vercel will ignore your visits.');
      updateUI(true);
    }
  };

  // 4. Apply restriction or initialize Vercel Analytics
  if (isBlocked) {
    // Completely disable Vercel Analytics — nullify stub and queue
    window.va = function () {};
    window.vaq = [];
    if (isBot) {
      console.info('[PCDeck] Vercel Analytics: EXCLUDED (Automated Bot / Headless Scraper Detected)');
    } else {
      console.info('[PCDeck] Vercel Analytics: EXCLUDED (Owner / Dev Visit Restriction Active)');
    }
  } else {
    // Initialize Vercel Analytics stub with beforeSend safeguard
    window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
    window.va('beforeSend', function (event) {
      // Final sanity check before dispatch
      try {
        if (localStorage.getItem(STORAGE_KEY) === '1' || getCookie(STORAGE_KEY) === '1' || isBotEnvironment()) {
          return null; // Drop event completely
        }
      } catch (e) {}
      return event;
    });

    var s = document.createElement('script');
    s.defer = true;
    s.src = '/_vercel/insights/script.js';
    document.head.appendChild(s);

    // Automated Custom Event Tracking for Downloads and Guide Navigation
    document.addEventListener('click', function (e) {
      if (isBlocked) return;
      var el = e.target.closest('a, button');
      if (!el || typeof window.va !== 'function') return;
      var href = (el.getAttribute('href') || '').toLowerCase();
      var text = (el.textContent || '').trim().toLowerCase();

      if (href.indexOf('pcdeck.exe') !== -1 || href.indexOf('/download/windows') !== -1 || text.indexOf('download for windows') !== -1 || text.indexOf('download pcdeck.exe') !== -1) {
        window.va('event', { name: 'download_windows' });
      } else if (href.indexOf('pcdeck.apk') !== -1 || href.indexOf('/download/android') !== -1 || text.indexOf('download apk') !== -1 || text.indexOf('download pcdeck.apk') !== -1) {
        window.va('event', { name: 'download_android' });
      } else if (href.indexOf('run_linux.sh') !== -1 || href.indexOf('/download/linux') !== -1 || href.indexOf('/linux-install') !== -1 || text.indexOf('linux setup') !== -1) {
        window.va('event', { name: 'download_linux' });
      } else if (el.classList.contains('guide-card') || el.closest('.guide-card')) {
        var card = el.closest('.guide-card') || el;
        var guidePath = card.getAttribute('href') || '';
        window.va('event', { name: 'guide_click', data: { path: guidePath } });
      }
    }, true);
  }

  // Helper: Visual Toast Notification
  function showNotification(msg) {
    function inject() {
      if (!document.body) return;
      var toast = document.getElementById('pcdeck-analytics-toast');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'pcdeck-analytics-toast';
        toast.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#12161c;color:#ffffff;border:1.5px solid #00f0ff;box-shadow:0 8px 30px rgba(0,0,0,0.5);padding:12px 22px;border-radius:999px;font-family:system-ui,-apple-system,sans-serif;font-size:13.5px;font-weight:600;z-index:999999;transition:opacity 0.3s ease, transform 0.3s ease;pointer-events:none;text-align:center;max-width:90vw;';
        document.body.appendChild(toast);
      }
      toast.textContent = msg;
      toast.style.opacity = '1';
      toast.style.transform = 'translateX(-50%) translateY(0)';
      clearTimeout(toast._timer);
      toast._timer = setTimeout(function () {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(-10px)';
      }, 4500);
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', inject);
    } else {
      inject();
    }
  }

  // Helper: Update badge text in footer if element exists
  function updateUI(blocked) {
    var btn = document.getElementById('btn-analytics-toggle');
    if (btn) {
      if (blocked) {
        btn.innerHTML = '🛡️ Analytics: <strong style="color:#10b981;">Blocked for You</strong>';
        btn.title = 'Your visits are currently IGNORED by Vercel Analytics. Click to re-enable.';
      } else {
        btn.innerHTML = '🛡️ Analytics: <span style="color:#64748b;">Active</span> (Click to Block)';
        btn.title = 'Your visits are being tracked. Click to block tracking on this device.';
      }
    }
  }

  // Bind to DOM ready for UI button
  var isOwnerBlocked = isBlocked && !isBot;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { updateUI(isOwnerBlocked); });
  } else {
    updateUI(isOwnerBlocked);
  }
})();
