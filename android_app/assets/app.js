/**
 * NeonTrack - Cyber-Neobrutalism Client Controller
 * Low-Latency PC Remote Touch Display, Universal Virtual Keyboard, In-Built PC File Manager & Anti-Jitter Trackpad
 */

(function () {
  'use strict';

  // Global Direct Tab Switcher (Called from HTML onclick or JS events)
  window.switchTabNav = function(tabEl, targetId) {
    if (window.navigator && window.navigator.vibrate) {
      try { window.navigator.vibrate(15); } catch(e) {}
    }
    state.activeTab = targetId;

    const allTabs = document.querySelectorAll('.dock-tab');
    allTabs.forEach(t => {
      if (t.dataset.target === targetId || t === tabEl) {
        t.classList.add('active');
      } else {
        t.classList.remove('active');
      }
    });

    const allViews = document.querySelectorAll('.tab-view');
    allViews.forEach(v => {
      if (v.id === targetId) {
        v.classList.add('active');
      } else {
        v.classList.remove('active');
      }
    });

    // If switched to files tab, refresh directory listing
    if (targetId === 'tab-files' && typeof window.loadFsPlacesGlobal === 'function') {
      window.loadFsPlacesGlobal();
    }
  };

  // --- Configuration & Default State ---
  const state = {
    serverHost: window.location.hostname || '127.0.0.1',
    serverPort: window.location.port || '8000',
    wsUrl: '',
    screenWsUrl: '',
    connected: false,
    screenConnected: false,
    latency: 0,
    cursorSpeed: 1.5,
    scrollSpeed: 1.4,
    smoothAccel: true,
    invertScroll: false,
    hapticsEnabled: true,
    wakelockEnabled: true,
    autoAudioStream: true,
    pinchZoomEnabled: true,
    // Screen stream encoder settings, pushed to the server as "cfg,quality,scale,fps".
    // The server clamps fps to 10-60, so 60 is the effective maximum.
    streamFps: 30,
    streamQuality: 75,
    streamScale: 0.85,
    autoQualityMode: 'auto',
    zoomSens: 1.0,
    activeTab: 'tab-screen',
    screenMode: 'touch', // 'touch', 'mouse', or 'rclick'
    dragLocked: false,
    titleBarHidden: false,
    wakeLockObj: null,
    // Mouse Smoothing & Anti-Jitter Filter
    smoothDx: 0,
    smoothDy: 0,
    // Pinch & Pan state
    zoomScale: 1.0,
    panX: 0,
    panY: 0,
    initialPinchDist: 0,
    initialZoom: 1.0,
    initialPanX: 0,
    initialPanY: 0,
    pinchMidX: 0,
    pinchMidY: 0,
    isPinching: false,
    lastTapTime: 0,
    // Sticky modifiers state
    capsLock: false,
    shiftPressed: false,
    ctrlPressed: false,
    altPressed: false,
    // In-Built PC File Manager State
    currentFsPath: '',
    fsParentPath: null,
    fsFolders: [],
    fsFiles: [],
    fsFilterText: '',
    markedFsPaths: new Set(),
    // In-Built Phone File Manager State
    phoneFs: {
      currentPath: 'default',
      parentPath: '',
      folders: [],
      files: [],
      filterText: '',
      markedPaths: new Set(),
    },
    // QR Scanner stream
    qrStream: null,
    currentFacingMode: 'environment',
    autoReconnectTimer: null,
  };

  // --- DOM Elements & Context Holder ---
  let el = {};
  let screenCtx = null;

  function initDomElements() {
    el = {
      appWrapper: document.getElementById('app-wrapper'),
      connectModal: document.getElementById('connect-modal'),
      modalIpInput: document.getElementById('modal-ip-input'),
      modalBtnConnect: document.getElementById('modal-btn-connect'),
      modalBtnScanQr: document.getElementById('modal-btn-scan-qr'),
      qrScannerModal: document.getElementById('qr-scanner-modal'),
      qrVideo: document.getElementById('qr-video'),
      qrCanvas: document.getElementById('qr-canvas'),
      btnCloseScanner: document.getElementById('btn-close-scanner'),
      btnSwitchCamera: document.getElementById('btn-switch-camera'),
      btnToggleTorch: document.getElementById('btn-toggle-torch'),
      toastMsg: document.getElementById('toast-msg'),
      toastIcon: document.getElementById('toast-icon'),
      toastText: document.getElementById('toast-text'),
      // Quick Tools Modal & Actions Drawer
      quickToolsModal: document.getElementById('quick-tools-modal'),
      btnQuickToolsToggle: document.getElementById('btn-quick-tools-toggle'),
      btnCloseTools: document.getElementById('btn-close-tools'),
      toolRotate: document.getElementById('tool-rotate'),
      toolKeyboard: document.getElementById('tool-keyboard'),
      toolTouchMode: document.getElementById('tool-touch-mode'),
      toolTouchStatus: document.getElementById('tool-touch-status'),
      toolRclick: document.getElementById('tool-rclick'),
      toolRclickStatus: document.getElementById('tool-rclick-status'),
      toolZoomReset: document.getElementById('tool-zoom-reset'),
      toolWakelock: document.getElementById('tool-wakelock'),
      toolWakelockStatus: document.getElementById('tool-wakelock-status'),
      toolFullscreen: document.getElementById('tool-fullscreen'),
      // Virtual Keyboard Drawer
      kbdDrawer: document.getElementById('virtual-kbd-drawer'),
      btnOpenKbdNav: document.getElementById('btn-open-kbd-nav'),
      btnCloseKbd: document.getElementById('btn-close-kbd'),
      kbdLiveInput: document.getElementById('kbd-live-input'),
      btnKbdPaste: document.getElementById('btn-kbd-paste'),
      btnKbdSend: document.getElementById('btn-kbd-send'),
      btnTabQwerty: document.getElementById('btn-tab-qwerty'),
      btnTabNumpad: document.getElementById('btn-tab-numpad'),
      btnTabFn: document.getElementById('btn-tab-fn'),
      panelQwerty: document.getElementById('panel-qwerty'),
      panelNumpad: document.getElementById('panel-numpad'),
      panelFn: document.getElementById('panel-fn'),
      vkCaps: document.getElementById('vk-caps'),
      vkShift: document.getElementById('vk-shift'),
      vkCtrl: document.getElementById('vk-ctrl'),
      vkAlt: document.getElementById('vk-alt'),
      // Header & Navigation
      topNav: document.querySelector('header.top-nav'),
      btnToggleTitlebar: document.getElementById('btn-toggle-titlebar'),
      btnUnhideTitlebar: document.getElementById('btn-unhide-titlebar'),
      btnReconnectHeader: document.getElementById('btn-reconnect-header'),
      pillStatus: document.getElementById('pill-status'),
      statusIndicator: document.getElementById('status-indicator'),
      statusLabel: document.getElementById('status-label'),
      latencyVal: document.getElementById('latency-val'),
      dockTabs: document.querySelectorAll('.dock-tab'),
      tabViews: document.querySelectorAll('.tab-view'),
      // Screen Tab
      screenViewport: document.getElementById('screen-viewport'),
      screenCanvasWrapper: document.getElementById('screen-canvas-wrapper'),
      screenCanvas: document.getElementById('screen-canvas'),
      screenTouchRippleLayer: document.getElementById('screen-touch-ripple-layer'),
      screenLoader: document.getElementById('screen-loader'),
      // Trackpad Tab
      trackpadSurface: document.getElementById('trackpad-surface'),
      scrollStrip: document.getElementById('scroll-strip'),
      btnLeftClick: document.getElementById('btn-left-click'),
      btnMiddleClick: document.getElementById('btn-middle-click'),
      btnRightClick: document.getElementById('btn-right-click'),
      btnSpeedQuick: document.getElementById('btn-speed-quick'),
      toolDragLock: document.getElementById('tool-drag-lock'),
      btnEscQuick: document.getElementById('btn-esc-quick'),
      btnDesktopQuick: document.getElementById('btn-desktop-quick'),
      btnKbdQuick: document.getElementById('btn-kbd-quick'),
      scrollBar: document.getElementById('scroll-bar'),
      textInput: document.getElementById('text-input'),
      // In-Built PC File Manager
      fsPlacesStrip: document.getElementById('fs-places-strip'),
      fsItemCount: document.getElementById('fs-item-count'),
      fsCurrentPath: document.getElementById('fs-current-path'),
      btnFsUp: document.getElementById('btn-fs-up'),
      btnFsRefresh: document.getElementById('btn-fs-refresh'),
      btnFsNewFolder: document.getElementById('btn-fs-new-folder'),
      btnFsUploadHere: document.getElementById('btn-fs-upload-here'),
      btnFsOpenPcFolder: document.getElementById('btn-fs-open-pc-folder'),
      btnFsModePc: document.getElementById('btn-fs-mode-pc'),
      btnFsModePhone: document.getElementById('btn-fs-mode-phone'),
      fsPcPanel: document.getElementById('fs-pc-panel'),
      fsPhonePanel: document.getElementById('fs-phone-panel'),
      phoneFsPlacesStrip: document.getElementById('phone-fs-places-strip'),
      btnPhoneFsUp: document.getElementById('btn-phone-fs-up'),
      phoneFsCurrentPath: document.getElementById('phone-fs-current-path'),
      btnPhoneFsRefresh: document.getElementById('btn-phone-fs-refresh'),
      btnPhoneFsNewFolder: document.getElementById('btn-phone-fs-new-folder'),
      btnPhoneFsUploadToPc: document.getElementById('btn-phone-fs-upload-to-pc'),
      phoneFsSearchInput: document.getElementById('phone-fs-search-input'),
      phoneFsItemCount: document.getElementById('phone-fs-item-count'),
      phoneFsBatchBar: document.getElementById('phone-fs-batch-bar'),
      phoneFsBatchSelectAll: document.getElementById('phone-fs-batch-select-all'),
      phoneFsBatchCountLabel: document.getElementById('phone-fs-batch-count-label'),
      phoneFsBatchSendLabel: document.getElementById('phone-fs-batch-send-label'),
      btnPhoneFsBatchSendPc: document.getElementById('btn-phone-fs-batch-send-pc'),
      btnPhoneFsBatchDelete: document.getElementById('btn-phone-fs-batch-delete'),
      btnPhoneFsBatchClear: document.getElementById('btn-phone-fs-batch-clear'),
      phoneFsBrowserItems: document.getElementById('phone-fs-browser-items'),
      filePicker: document.getElementById('file-picker'),
      fsSearchInput: document.getElementById('fs-search-input'),
      fsBatchBar: document.getElementById('fs-batch-bar'),
      fsBatchSelectAll: document.getElementById('fs-batch-select-all'),
      fsBatchCountLabel: document.getElementById('fs-batch-count-label'),
      fsBatchDlLabel: document.getElementById('fs-batch-dl-label'),
      btnFsBatchDownload: document.getElementById('btn-fs-batch-download'),
      btnFsBatchDelete: document.getElementById('btn-fs-batch-delete'),
      btnFsBatchClear: document.getElementById('btn-fs-batch-clear'),
      fileTransferBox: document.getElementById('file-transfer-box') || document.getElementById('file-upload-box'),
      fileUploadBox: document.getElementById('file-upload-box') || document.getElementById('file-transfer-box'),
      transferBadge: document.getElementById('transfer-badge'),
      transferFilename: document.getElementById('transfer-filename') || document.getElementById('upload-filename'),
      uploadFilename: document.getElementById('upload-filename') || document.getElementById('transfer-filename'),
      transferPercent: document.getElementById('transfer-percent') || document.getElementById('upload-percent'),
      uploadPercent: document.getElementById('upload-percent') || document.getElementById('transfer-percent'),
      transferBar: document.getElementById('transfer-bar') || document.getElementById('upload-bar'),
      uploadBar: document.getElementById('upload-bar') || document.getElementById('transfer-bar'),
      transferStatus: document.getElementById('transfer-status') || document.getElementById('upload-status'),
      uploadStatus: document.getElementById('upload-status') || document.getElementById('transfer-status'),
      btnTransferOpenPc: document.getElementById('btn-transfer-open-pc'),
      btnTransferOpenPhone: document.getElementById('btn-transfer-open-phone'),
      btnTransferClose: document.getElementById('btn-transfer-close'),
      btnFsPhoneDownloadsChip: document.getElementById('btn-fs-phone-downloads-chip'),
      fsBrowserItems: document.getElementById('fs-browser-items'),
      // Settings Tab
      settingsIpInput: document.getElementById('settings-ip-input'),
      btnSaveIp: document.getElementById('btn-save-ip'),
      settingsBtnScanQr: document.getElementById('settings-btn-scan-qr'),
      settingsBtnRotate: document.getElementById('settings-btn-rotate'),
      settingPinchZoom: document.getElementById('setting-pinch-zoom'),
      settingZoomSens: document.getElementById('setting-zoom-sens'),
      valZoomSens: document.getElementById('val-zoom-sens'),
      settingCursorSpeed: document.getElementById('setting-cursor-speed'),
      valCursorSpeed: document.getElementById('val-cursor-speed'),
      settingScrollSpeed: document.getElementById('setting-scroll-speed'),
      valScrollSpeed: document.getElementById('val-scroll-speed'),
      settingAccel: document.getElementById('setting-accel'),
      settingInvertScroll: document.getElementById('setting-invert-scroll'),
      settingHaptics: document.getElementById('setting-haptics'),
      settingWakelock: document.getElementById('setting-wakelock'),
      settingAutoAudio: document.getElementById('setting-auto-audio'),
      btnSaveAllSettings: document.getElementById('btn-save-all-settings'),
      btnResetSettings: document.getElementById('btn-reset-settings'),
      // Live PC Audio Streaming Elements
      btnToggleAudioStream: document.getElementById('btn-toggle-audio-stream'),
      audioBtnIcon: document.getElementById('audio-btn-icon'),
      audioBtnLabel: document.getElementById('audio-btn-label'),
      audioStatusPill: document.getElementById('audio-status-pill'),
      audioVolumeSlider: document.getElementById('audio-volume-slider'),
      valAudioVolume: document.getElementById('val-audio-volume'),
      audioVisualizerBars: document.getElementById('audio-visualizer-bars'),
    };

    if (el.screenCanvas) {
      screenCtx = el.screenCanvas.getContext('2d', { alpha: false });
    }
  }

  // WebSockets
  let mainWs = null;
  let screenWs = null;
  let pingInterval = null;
  let qrScanAnimationId = null;
  let toastTimer = null;

  // --- Toast Notification System ---
  function showToast(text, type = 'success', icon = '✅') {
    if (!el.toastMsg) return;
    clearTimeout(toastTimer);
    el.toastText.textContent = text;
    el.toastIcon.textContent = icon;
    el.toastMsg.className = 'neo-toast show';
    if (type === 'warn') {
      el.toastMsg.classList.add('toast-warn');
    } else if (type === 'error') {
      el.toastMsg.classList.add('toast-error');
    }
    toastTimer = setTimeout(() => {
      el.toastMsg.classList.remove('show');
    }, 2500);
  }

  // --- Haptic Feedback ---
  function vibrate(ms = 18) {
    if (state.hapticsEnabled && window.navigator && window.navigator.vibrate) {
      try {
        window.navigator.vibrate(ms);
      } catch (e) {}
    }
  }

  // --- Screen Wake Lock API ---
  async function requestWakeLock() {
    if ('wakeLock' in navigator && state.wakelockEnabled) {
      try {
        state.wakeLockObj = await navigator.wakeLock.request('screen');
        state.wakeLockObj.addEventListener('release', () => {
          state.wakeLockObj = null;
        });
      } catch (err) {
        console.warn('Wake Lock error:', err);
      }
    }
  }

  function releaseWakeLock() {
    if (state.wakeLockObj) {
      state.wakeLockObj.release().catch(() => {});
      state.wakeLockObj = null;
    }
  }

  // --- Settings Persistence ---
  function loadSettings() {
    try {
      const isHttp = window.location.protocol.startsWith('http') && window.location.hostname;
      const urlParams = new URLSearchParams(window.location.search);
      const queryIp = urlParams.get('ip');

      if (queryIp) {
        const clean = queryIp.replace(/^https?:\/\//, '');
        const parts = clean.split(':');
        state.serverHost = parts[0];
        state.serverPort = parts[1] || '8000';
        if (el.modalIpInput) el.modalIpInput.value = `${state.serverHost}:${state.serverPort}`;
        if (el.settingsIpInput) el.settingsIpInput.value = `${state.serverHost}:${state.serverPort}`;
        localStorage.setItem('neontrack_ip', `${state.serverHost}:${state.serverPort}`);
        localStorage.setItem('pcdeck_onboarding_completed', 'true');
      } else if (isHttp) {
        // Direct browser connection: host is already the PC server
        state.serverHost = window.location.hostname;
        state.serverPort = window.location.port || '8000';
        if (el.modalIpInput) el.modalIpInput.value = `${state.serverHost}:${state.serverPort}`;
        if (el.settingsIpInput) el.settingsIpInput.value = `${state.serverHost}:${state.serverPort}`;
        localStorage.setItem('neontrack_ip', `${state.serverHost}:${state.serverPort}`);
        localStorage.setItem('pcdeck_onboarding_completed', 'true');
      } else {
        const savedIp = localStorage.getItem('neontrack_ip');
        if (savedIp) {
          const parts = savedIp.split(':');
          state.serverHost = parts[0];
          state.serverPort = parts[1] || '8000';
          if (el.modalIpInput) el.modalIpInput.value = savedIp;
          if (el.settingsIpInput) el.settingsIpInput.value = savedIp;
        }
      }

      const cursor = localStorage.getItem('neontrack_cursor_speed');
      if (cursor) {
        state.cursorSpeed = parseFloat(cursor);
        if (el.settingCursorSpeed) el.settingCursorSpeed.value = cursor;
        if (el.valCursorSpeed) el.valCursorSpeed.textContent = parseFloat(cursor).toFixed(1) + 'x';
        if (el.btnSpeedQuick) el.btnSpeedQuick.textContent = `${parseFloat(cursor).toFixed(1)}x`;
      } else {
        state.cursorSpeed = 1.5;
        if (el.settingCursorSpeed) el.settingCursorSpeed.value = '1.5';
        if (el.valCursorSpeed) el.valCursorSpeed.textContent = '1.5x';
        if (el.btnSpeedQuick) el.btnSpeedQuick.textContent = '1.5x';
      }

      const scroll = localStorage.getItem('neontrack_scroll_speed');
      if (scroll) {
        state.scrollSpeed = parseFloat(scroll);
        if (el.settingScrollSpeed) el.settingScrollSpeed.value = scroll;
        if (el.valScrollSpeed) el.valScrollSpeed.textContent = parseFloat(scroll).toFixed(1) + 'x';
      } else {
        state.scrollSpeed = 1.4;
        if (el.settingScrollSpeed) el.settingScrollSpeed.value = '1.4';
        if (el.valScrollSpeed) el.valScrollSpeed.textContent = '1.4x';
      }

      const zoomSens = localStorage.getItem('neontrack_zoom_sens');
      if (zoomSens) {
        state.zoomSens = parseFloat(zoomSens);
        if (el.settingZoomSens) el.settingZoomSens.value = zoomSens;
        if (el.valZoomSens) el.valZoomSens.textContent = zoomSens + 'x';
      }

      const pinch = localStorage.getItem('neontrack_pinch_zoom');
      if (pinch !== null) {
        state.pinchZoomEnabled = pinch === 'true';
        if (el.settingPinchZoom) el.settingPinchZoom.checked = state.pinchZoomEnabled;
      }

      const accel = localStorage.getItem('neontrack_accel');
      if (accel !== null) {
        state.smoothAccel = accel === 'true';
        if (el.settingAccel) el.settingAccel.checked = state.smoothAccel;
      }

      const invert = localStorage.getItem('neontrack_invert_scroll');
      if (invert !== null) {
        state.invertScroll = invert === 'true';
        if (el.settingInvertScroll) el.settingInvertScroll.checked = state.invertScroll;
      }

      const haptics = localStorage.getItem('neontrack_haptics');
      if (haptics !== null) {
        state.hapticsEnabled = haptics === 'true';
        if (el.settingHaptics) el.settingHaptics.checked = state.hapticsEnabled;
      }

      const wakelock = localStorage.getItem('neontrack_wakelock');
      if (wakelock !== null) {
        state.wakelockEnabled = wakelock === 'true';
        if (el.settingWakelock) el.settingWakelock.checked = state.wakelockEnabled;
      }

      const autoAudio = localStorage.getItem('neontrack_auto_audio');
      if (autoAudio !== null) {
        state.autoAudioStream = autoAudio === 'true';
        if (el.settingAutoAudio) el.settingAutoAudio.checked = state.autoAudioStream;
      } else {
        state.autoAudioStream = true;
        if (el.settingAutoAudio) el.settingAutoAudio.checked = true;
      }

      const savedFps = localStorage.getItem('neontrack_stream_fps');
      if (savedFps !== null) {
        const parsed = parseInt(savedFps, 10);
        if (parsed === 30 || parsed === 60) state.streamFps = parsed;
      }

      const savedQuality = localStorage.getItem('neontrack_stream_quality');
      if (savedQuality !== null) state.streamQuality = parseInt(savedQuality, 10);
      const savedScale = localStorage.getItem('neontrack_stream_scale');
      if (savedScale !== null) state.streamScale = parseFloat(savedScale);
      const savedAutoMode = localStorage.getItem('neontrack_stream_auto_mode');
      if (savedAutoMode) state.autoQualityMode = savedAutoMode;

      const selClarity = document.getElementById('setting-stream-clarity');
      if (selClarity) {
        selClarity.value = state.autoQualityMode || 'auto';
      }

      const titlebarHidden = localStorage.getItem('neontrack_titlebar_hidden');
      if (titlebarHidden === 'true') {
        state.titleBarHidden = true;
        if (el.topNav) el.topNav.classList.add('hidden-bar');
        if (el.btnUnhideTitlebar) el.btnUnhideTitlebar.style.display = 'inline-flex';
      }
    } catch (e) {
      console.warn('Could not load settings from localStorage', e);
    }
  }

  function saveAllSettings(showToastNotify = true) {
    try {
      localStorage.setItem('neontrack_ip', `${state.serverHost}:${state.serverPort}`);
      localStorage.setItem('neontrack_cursor_speed', state.cursorSpeed.toString());
      localStorage.setItem('neontrack_scroll_speed', state.scrollSpeed.toString());
      localStorage.setItem('neontrack_zoom_sens', state.zoomSens.toString());
      localStorage.setItem('neontrack_pinch_zoom', state.pinchZoomEnabled.toString());
      localStorage.setItem('neontrack_accel', state.smoothAccel.toString());
      localStorage.setItem('neontrack_invert_scroll', state.invertScroll.toString());
      localStorage.setItem('neontrack_haptics', state.hapticsEnabled.toString());
      localStorage.setItem('neontrack_wakelock', state.wakelockEnabled.toString());
      localStorage.setItem('neontrack_auto_audio', state.autoAudioStream.toString());
      localStorage.setItem('neontrack_stream_fps', state.streamFps.toString());
      localStorage.setItem('neontrack_stream_quality', state.streamQuality.toString());
      localStorage.setItem('neontrack_stream_scale', state.streamScale.toString());
      localStorage.setItem('neontrack_stream_auto_mode', state.autoQualityMode || 'auto');
      localStorage.setItem('neontrack_titlebar_hidden', state.titleBarHidden.toString());

      if (showToastNotify) {
        showToast('All Preferences Saved!', 'success', '💾');
        vibrate(30);
      }
    } catch (e) {
      console.warn('Could not save settings to localStorage', e);
    }
  }

  function resetAllSettings() {
    localStorage.clear();
    state.cursorSpeed = 1.5;
    state.scrollSpeed = 1.4;
    state.zoomSens = 1.0;
    state.pinchZoomEnabled = true;
    state.smoothAccel = true;
    state.invertScroll = false;
    state.hapticsEnabled = true;
    state.wakelockEnabled = true;
    state.autoAudioStream = true;
    state.titleBarHidden = false;
    if (el.topNav) el.topNav.classList.remove('hidden-bar');
    if (el.btnUnhideTitlebar) el.btnUnhideTitlebar.style.display = 'none';

    if (el.settingCursorSpeed) el.settingCursorSpeed.value = '1.5';
    if (el.valCursorSpeed) el.valCursorSpeed.textContent = '1.5x';
    if (el.btnSpeedQuick) el.btnSpeedQuick.textContent = '1.5x';
    if (el.settingScrollSpeed) el.settingScrollSpeed.value = '1.4';
    if (el.valScrollSpeed) el.valScrollSpeed.textContent = '1.4x';
    if (el.settingZoomSens) el.settingZoomSens.value = '1.0';
    if (el.valZoomSens) el.valZoomSens.textContent = '1.0x';
    if (el.settingPinchZoom) el.settingPinchZoom.checked = true;
    if (el.settingAccel) el.settingAccel.checked = true;
    if (el.settingInvertScroll) el.settingInvertScroll.checked = false;
    if (el.settingHaptics) el.settingHaptics.checked = true;
    if (el.settingWakelock) el.settingWakelock.checked = true;
    if (el.settingAutoAudio) el.settingAutoAudio.checked = true;

    resetPinchZoom();
    showToast('Settings Reset to Defaults', 'warn', '🔄');
    vibrate(30);
  }

  // --- Cyber Touch Ripple After-Effect Engine ---
  function spawnTouchRipple(clientX, clientY, type = 'tap') {
    const layer = el.screenTouchRippleLayer || document.getElementById('screen-touch-ripple-layer');
    if (!layer || !el.screenCanvasWrapper) return;

    const wrapperRect = el.screenCanvasWrapper.getBoundingClientRect();
    const x = clientX - wrapperRect.left;
    const y = clientY - wrapperRect.top;

    const ripple = document.createElement('div');
    ripple.className = `touch-ripple-effect ripple-${type}`;
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;

    layer.appendChild(ripple);

    // Auto cleanup after animation
    const duration = type === 'trail' ? 200 : (type === 'double' ? 380 : 340);
    setTimeout(() => {
      if (ripple.parentNode) {
        ripple.parentNode.removeChild(ripple);
      }
    }, duration);
  }

  // --- Smart Touchscreen Interaction Engine for Streaming Display ---
  function initScreenTouchDisplay() {
    if (!el.screenCanvas || !el.screenViewport) return;

    let touchActive = false;
    let touchStartX = 0, touchStartY = 0;
    let lastX = 0, lastY = 0;
    let touchStartTime = 0;
    let longPressTimer = null;
    let lastTapTime = 0;
    let lastTapX = 0, lastTapY = 0;
    let rAfMoveScheduled = false;
    let pendingNormX = 0, pendingNormY = 0;
    let pendingRelDx = 0, pendingRelDy = 0;
    let lastTrailTime = 0;

    // 1-Finger and 2-Finger Touch State Engine
    let isScrolling = false;
    let isLongPressDrag = false;
    let twoFingerActive = false;
    let twoFingerStartTime = 0;
    let twoFingerStartDist = 0;
    let twoFingerMoved = false;
    let twoFingerMidX = 0, twoFingerMidY = 0;

    // Velocity Tracker for True Mobile Kinetic Momentum (Fling Inertia)
    let touchHistory = [];
    let isMomentumActive = false;
    let momentumAnimId = null;

    // Prevent default context menu and text selection
    el.screenCanvas.oncontextmenu = (e) => { e.preventDefault(); return false; };
    if (el.screenViewport) {
      el.screenViewport.oncontextmenu = (e) => { e.preventDefault(); return false; };
    }

    function getNormalizedCoords(clientX, clientY) {
      if (!el.screenCanvas) return { x: 0.5, y: 0.5 };
      const rect = el.screenCanvas.getBoundingClientRect();
      if (!rect || rect.width <= 0 || rect.height <= 0) return { x: 0.5, y: 0.5 };
      const normX = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      const normY = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height));
      return { x: normX, y: normY };
    }

    function flushScreenMove() {
      rAfMoveScheduled = false;
      if (!touchActive) return;

      if (state.screenMode === 'mouse') {
        // Virtual Cursor Trackpad Mode: relative move
        if (pendingRelDx !== 0 || pendingRelDy !== 0) {
          sendCommand(`m,${pendingRelDx.toFixed(1)},${pendingRelDy.toFixed(1)}`);
          pendingRelDx = 0;
          pendingRelDy = 0;
        }
      } else {
        // Direct Touch Mode: absolute move
        sendScreenCommand(`a,${pendingNormX.toFixed(4)},${pendingNormY.toFixed(4)}`);
      }
    }

    const touchArena = el.screenViewport || el.screenCanvas;

    touchArena.addEventListener('touchstart', (e) => {
      // Instantly cancel any ongoing kinetic momentum glide (tap-to-stop)
      if (isMomentumActive) {
        isMomentumActive = false;
        if (momentumAnimId) {
          cancelAnimationFrame(momentumAnimId);
          momentumAnimId = null;
        }
      }

      // 2-Finger Touch handling (Pinch-to-Zoom & Pan)
      if (e.touches.length === 2) {
        if (longPressTimer) {
          clearTimeout(longPressTimer);
          longPressTimer = null;
        }
        touchActive = false;
        twoFingerActive = true;
        twoFingerMoved = false;
        twoFingerStartTime = Date.now();
        const t1 = e.touches[0];
        const t2 = e.touches[1];
        twoFingerStartDist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
        twoFingerMidX = (t1.clientX + t2.clientX) / 2;
        twoFingerMidY = (t1.clientY + t2.clientY) / 2;

        if (state.pinchZoomEnabled) {
          state.isPinching = true;
          state.initialPinchDist = twoFingerStartDist;
          state.initialZoom = state.zoomScale;
          state.initialPanX = state.panX;
          state.initialPanY = state.panY;
          state.pinchMidX = twoFingerMidX;
          state.pinchMidY = twoFingerMidY;
        }
        e.preventDefault();
        return;
      }

      if (e.touches.length > 1) return;

      twoFingerActive = false;
      touchActive = true;
      isScrolling = false;
      isLongPressDrag = false;
      const touch = e.touches[0];
      touchStartX = lastX = touch.clientX;
      touchStartY = lastY = touch.clientY;
      touchStartTime = Date.now();

      touchHistory = [{ time: touchStartTime, x: touch.clientX, y: touch.clientY }];

      const norm = getNormalizedCoords(touch.clientX, touch.clientY);
      pendingNormX = norm.x;
      pendingNormY = norm.y;
      pendingRelDx = 0;
      pendingRelDy = 0;

      // 1-Finger Long-Press Timer (350ms): Engages Drag & Move Mode for Files / Windows / Text!
      longPressTimer = setTimeout(() => {
        if (touchActive && !isScrolling && !state.isPinching) {
          const dist = Math.hypot(lastX - touchStartX, lastY - touchStartY);
          if (dist < 14) {
            isLongPressDrag = true;
            spawnTouchRipple(lastX, lastY, 'double');
            vibrate(45);
            showToast('Drag & Move Locked ✊ (Move to drag, release to drop)', 'info', '✊');
            const curNorm = getNormalizedCoords(lastX, lastY);
            // Move cursor to position and press down left mouse button on PC
            sendScreenCommand(`td,${curNorm.x.toFixed(4)},${curNorm.y.toFixed(4)},left`);
          }
        }
      }, 350);
    }, { passive: false });

    touchArena.addEventListener('touchmove', (e) => {
      // 2-Finger Pinch-to-Zoom & Pan
      if (e.touches.length === 2 && twoFingerActive) {
        const t1 = e.touches[0];
        const t2 = e.touches[1];
        const curDist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
        const midX = (t1.clientX + t2.clientX) / 2;
        const midY = (t1.clientY + t2.clientY) / 2;

        if (Math.abs(curDist - twoFingerStartDist) > 10 || Math.hypot(midX - twoFingerMidX, midY - twoFingerMidY) > 8) {
          twoFingerMoved = true;
        }

        if (state.pinchZoomEnabled && state.isPinching && state.initialPinchDist > 0) {
          const factor = (curDist / state.initialPinchDist - 1) * state.zoomSens + 1;
          state.zoomScale = Math.max(0.7, Math.min(5.0, state.initialZoom * factor));
          state.panX = state.initialPanX + (midX - state.pinchMidX);
          state.panY = state.initialPanY + (midY - state.pinchMidY);
          updateCanvasTransform();
        }
        e.preventDefault();
        return;
      }

      if (state.isPinching || e.touches.length > 1 || !touchActive) return;
      const touch = e.touches[0];
      const dx = touch.clientX - lastX;
      const dy = touch.clientY - lastY;
      lastX = touch.clientX;
      lastY = touch.clientY;

      const now = Date.now();
      touchHistory.push({ time: now, x: touch.clientX, y: touch.clientY });
      while (touchHistory.length > 0 && now - touchHistory[0].time > 100) {
        touchHistory.shift();
      }

      const totalDist = Math.hypot(lastX - touchStartX, lastY - touchStartY);

      // If in Long-Press Drag Mode: move the file / item / window / selection on PC!
      if (isLongPressDrag) {
        const norm = getNormalizedCoords(touch.clientX, touch.clientY);
        sendScreenCommand(`tm,${norm.x.toFixed(4)},${norm.y.toFixed(4)}`);
        if (now - lastTrailTime > 40) {
          lastTrailTime = now;
          spawnTouchRipple(touch.clientX, touch.clientY, 'trail');
        }
        e.preventDefault();
        return;
      }

      // If moved before long-press engaged (> 7px), cancel long-press timer and scroll
      if (totalDist > 7 && longPressTimer) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }

      if (state.screenMode === 'mouse') {
        // Virtual Cursor Trackpad Glide
        pendingRelDx += dx * state.cursorSpeed;
        pendingRelDy += dy * state.cursorSpeed;
        if (!rAfMoveScheduled) {
          rAfMoveScheduled = true;
          requestAnimationFrame(flushScreenMove);
        }
      } else {
        // Direct Touch Mode: 1-Finger Drag = Targeted 1:1 Smart Scroll at Touch Position!
        if (totalDist > 7 || isScrolling) {
          isScrolling = true;
          const norm = getNormalizedCoords(touch.clientX, touch.clientY);
          const rect = el.screenCanvas.getBoundingClientRect();
          const canvasH = (el.screenCanvas.height && el.screenCanvas.height > 0) ? el.screenCanvas.height : 1080;
          const canvasW = (el.screenCanvas.width && el.screenCanvas.width > 0) ? el.screenCanvas.width : 1920;
          const rectH = (rect && rect.height > 0) ? rect.height : 360;
          const rectW = (rect && rect.width > 0) ? rect.width : 640;

          const effectiveZoom = (state.zoomScale && state.zoomScale > 0.1) ? state.zoomScale : 1.0;

          // True 1:1 Physical PC Screen Tracking:
          // Matches native mobile touch scrolling in folders, browsers, and documents.
          const scrollFactor = state.invertScroll ? -1 : 1;
          const scrollMultiplier = 3.5;
          const scaleY = (canvasH / rectH) / effectiveZoom;
          const scaleX = (canvasW / rectW) / effectiveZoom;

          const wheelDy = dy * scaleY * state.scrollSpeed * scrollFactor * scrollMultiplier;
          const wheelDx = dx * scaleX * state.scrollSpeed * scrollFactor * scrollMultiplier;

          if (Math.abs(wheelDy) >= 0.2 || Math.abs(wheelDx) >= 0.2) {
            sendScreenCommand(`ts,${norm.x.toFixed(4)},${norm.y.toFixed(4)},${wheelDx.toFixed(1)},${wheelDy.toFixed(1)}`);
          }
        }
      }
      e.preventDefault();
    }, { passive: false });

    touchArena.addEventListener('touchend', (e) => {
      if (longPressTimer) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }

      // 2-Finger Release
      if (twoFingerActive && e.touches.length < 2) {
        twoFingerActive = false;
        state.isPinching = false;
        if (state.zoomScale < 0.9) {
          resetPinchZoom();
        }
        return;
      }

      if (state.isPinching || !touchActive) return;
      touchActive = false;

      const touchEndTime = Date.now();
      const tapDuration = touchEndTime - touchStartTime;
      const moveDist = Math.hypot(lastX - touchStartX, lastY - touchStartY);

      // If user was in Long-Press Drag Mode: Release mouse button at drop location!
      if (isLongPressDrag) {
        isLongPressDrag = false;
        const norm = getNormalizedCoords(lastX, lastY);
        sendScreenCommand(`tu,${norm.x.toFixed(4)},${norm.y.toFixed(4)},left`);

        if (moveDist < 12) {
          // Held in place without dragging -> Trigger Right-Click Context Menu!
          sendScreenCommand('c,right');
          spawnTouchRipple(lastX, lastY, 'right');
          showToast('Right Click 🖱️', 'success', '🖱️');
          vibrate(30);
        } else {
          // Dragged and released -> Dropped file/item/selection!
          spawnTouchRipple(lastX, lastY, 'tap');
          showToast('Item Dropped / Moved 🎯', 'success', '🎯');
          vibrate(35);
        }
        return;
      }

      // Calculate release velocity for kinetic momentum (fling physics)
      const now = Date.now();
      const recentPoints = touchHistory.filter(p => now - p.time < 80);
      let vy = 0, vx = 0;
      if (recentPoints.length >= 2) {
        const first = recentPoints[0];
        const last = recentPoints[recentPoints.length - 1];
        const dt = last.time - first.time;
        if (dt > 10) {
          vy = (last.y - first.y) / dt; // px per millisecond
          vx = (last.x - first.x) / dt;
        }
      }

      // If user was scrolling / dragged finger, don't trigger click on release
      if (isScrolling || moveDist > 14) {
        const wasScrolling = isScrolling;
        isScrolling = false;

        // Engage Kinetic Momentum Glide if flicked with velocity (> 0.35 px/ms)
        if (wasScrolling && (Math.abs(vy) > 0.35 || Math.abs(vx) > 0.35) && state.screenMode !== 'mouse') {
          const rect = el.screenCanvas.getBoundingClientRect();
          const canvasH = (el.screenCanvas.height && el.screenCanvas.height > 0) ? el.screenCanvas.height : 1080;
          const canvasW = (el.screenCanvas.width && el.screenCanvas.width > 0) ? el.screenCanvas.width : 1920;
          const rectH = (rect && rect.height > 0) ? rect.height : 360;
          const rectW = (rect && rect.width > 0) ? rect.width : 640;
          const effectiveZoom = (state.zoomScale && state.zoomScale > 0.1) ? state.zoomScale : 1.0;
          const scrollFactor = state.invertScroll ? -1 : 1;
          const scaleY = (canvasH / rectH) / effectiveZoom;
          const scaleX = (canvasW / rectW) / effectiveZoom;

          let momentumVy = vy;
          let momentumVx = vx;
          let lastNorm = getNormalizedCoords(lastX, lastY);
          let lastMomentumTime = performance.now();

          const stepMomentum = (curTime) => {
            if (!isMomentumActive) return;
            const dt = Math.min(32, curTime - lastMomentumTime);
            lastMomentumTime = curTime;

            // Exponential friction decay (smooth mobile deceleration curve)
            const friction = Math.pow(0.92, dt / 16.67);
            momentumVy *= friction;
            momentumVx *= friction;

            const stepDy = momentumVy * dt;
            const stepDx = momentumVx * dt;

            const scrollMultiplier = 3.5;
            const wheelDy = stepDy * scaleY * state.scrollSpeed * scrollFactor * scrollMultiplier;
            const wheelDx = stepDx * scaleX * state.scrollSpeed * scrollFactor * scrollMultiplier;

            if (Math.abs(wheelDy) >= 0.2 || Math.abs(wheelDx) >= 0.2) {
              sendScreenCommand(`ts,${lastNorm.x.toFixed(4)},${lastNorm.y.toFixed(4)},${wheelDx.toFixed(1)},${wheelDy.toFixed(1)}`);
            }

            if (Math.abs(momentumVy) > 0.04 || Math.abs(momentumVx) > 0.04) {
              momentumAnimId = requestAnimationFrame(stepMomentum);
            } else {
              isMomentumActive = false;
              momentumAnimId = null;
            }
          };

          isMomentumActive = true;
          momentumAnimId = requestAnimationFrame(stepMomentum);
        }
        return;
      }

      if (tapDuration < 280 && moveDist < 14) {
        const timeSinceLastTap = touchEndTime - lastTapTime;
        const tapDistance = Math.hypot(lastX - lastTapX, lastY - lastTapY);

        if (timeSinceLastTap < 350 && tapDistance < 24) {
          // 1-Finger Double Tap -> Double Click (Opens file/app/folder)
          lastTapTime = 0;
          spawnTouchRipple(lastX, lastY, 'double');
          const norm = getNormalizedCoords(lastX, lastY);
          sendScreenCommand(`a,${norm.x.toFixed(4)},${norm.y.toFixed(4)}`);
          sendScreenCommand('c,double');
          vibrate(30);
          showToast('Double Click (Open/Run)', 'success', '🖱️');
        } else {
          // 1-Finger Single Tap -> Left Click at exact touch position!
          lastTapTime = touchEndTime;
          lastTapX = lastX;
          lastTapY = lastY;
          vibrate(18);

          spawnTouchRipple(lastX, lastY, state.screenMode === 'rclick' ? 'right' : 'tap');

          const norm = getNormalizedCoords(lastX, lastY);
          sendScreenCommand(`a,${norm.x.toFixed(4)},${norm.y.toFixed(4)}`);

          if (state.screenMode === 'rclick') {
            sendScreenCommand('c,right');
            state.screenMode = 'touch';
            if (el.toolRclickStatus) el.toolRclickStatus.textContent = 'Next Tap: Normal';
            showToast('Right Click 🖱️', 'success', '🖱️');
          } else {
            sendScreenCommand('c,left');
          }
        }
      }
    }, { passive: false });
  }

  // --- Pinch-to-Zoom & Pan Gesture Engine ---
  function updateCanvasTransform() {
    if (!el.screenCanvasWrapper) return;
    el.screenCanvasWrapper.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoomScale})`;
  }

  function resetPinchZoom() {
    state.zoomScale = 1.0;
    state.panX = 0;
    state.panY = 0;
    state.isPinching = false;
    updateCanvasTransform();
    showToast('Zoom reset to 100% Fit', 'success', '🔍');
  }

  function initPinchZoomGestures() {
    // Gestures unified inside initScreenTouchDisplay for smooth synchronization
  }

  // --- Auto-Connect & WebSocket Management ---
  function connect() {
    updateStatus('connecting', 'Connecting...');
    const isHttp = window.location.protocol.startsWith('http') && window.location.hostname;
    const host = state.serverHost || (isHttp ? window.location.hostname : '127.0.0.1');
    const port = state.serverPort || (isHttp ? (window.location.port || '8000') : '8000');
    state.serverHost = host;
    state.serverPort = port;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    state.wsUrl = `${protocol}//${host}:${port}/ws`;
    state.screenWsUrl = `${protocol}//${host}:${port}/ws/screen`;

    if (mainWs) {
      try { mainWs.close(); } catch (e) {}
    }
    // Do NOT close screenWs here: closing it without detaching its handlers fires
    // onclose, which schedules a reconnect that then races the socket connectScreenWs()
    // is about to open. connectScreenWs() tears the old one down properly.

    try {
      mainWs = new WebSocket(state.wsUrl);
      mainWs.onopen = onMainWsOpen;
      mainWs.onmessage = onMainWsMessage;
      mainWs.onclose = onMainWsClose;
      mainWs.onerror = onMainWsError;

      connectScreenWs();
    } catch (e) {
      console.error('Failed to open main WebSocket:', e);
      onMainWsError();
    }
  }

  let screenReconnectTimer = null;
  let lastScreenFrameReceivedTime = Date.now();
  let screenFirstFrameSeen = false;
  let screenWatchdogTimer = null;

  function showScreenLoader(message) {
    if (!el.screenLoader) return;
    if (screenFirstFrameSeen) return; // Never flicker the loader if a frame is already displayed
    el.screenLoader.style.display = '';
    const label = el.screenLoader.querySelector('span');
    if (label && message) label.textContent = message;
  }

  // Self-heals a stalled stream gently without repeatedly destroying active sockets.
  function startScreenWatchdog() {
    if (screenWatchdogTimer) return;
    screenWatchdogTimer = setInterval(() => {
      if (!state.connected) return;
      if (!screenWs || screenWs.readyState === WebSocket.CLOSED) {
        connectScreenWs();
      } else if (screenWs.readyState === WebSocket.OPEN) {
        // If connected but no frame arrived for > 4.5s (idle screen), nudge server for fresh frame
        const stalled = Date.now() - lastScreenFrameReceivedTime > 4500;
        if (stalled) {
          lastScreenFrameReceivedTime = Date.now();
          sendStreamConfig();
        }
      }
    }, 2500);
  }

  // Pushes the encoder settings to the server.
  function sendStreamConfig() {
    if (!screenWs || screenWs.readyState !== WebSocket.OPEN) return;
    const fps = Math.max(10, Math.min(60, parseInt(state.streamFps, 10) || 30));
    const quality = Math.max(20, Math.min(100, parseInt(state.streamQuality, 10) || 75));
    const scale = Math.max(0.3, Math.min(1.0, parseFloat(state.streamScale) || 0.85));
    try {
      screenWs.send(`cfg,${quality},${scale.toFixed(2)},${fps}`);
    } catch (e) {}
  }

  // --- Intelligent Dynamic Adaptive Quality & Latency Controller (Auto ABR) ---
  let smoothedRtt = 25; // ms
  let stableTicks = 0;
  let currentAppliedQuality = 75;
  let currentAppliedScale = 0.85;
  let lastAutoBandwidthClass = '';

  function updateAdaptiveQuality(currentRtt) {
    if (state.autoQualityMode !== 'auto') return;

    // Exponential moving average for jitter-resistant smoothed RTT
    smoothedRtt = Math.round(smoothedRtt * 0.65 + currentRtt * 0.35);

    let targetQuality = 75;
    let targetScale = 0.85;
    let bandwidthLabel = '';

    if (smoothedRtt < 22) {
      // 5 GHz / 6 GHz / USB Tethering / Wi-Fi 6 Ultra-Fast
      targetQuality = 88;
      targetScale = 1.0;
      bandwidthLabel = '5GHz/6G ⚡';
    } else if (smoothedRtt <= 48) {
      // Clean 5 GHz or strong 2.4 GHz
      targetQuality = 78;
      targetScale = 0.90;
      bandwidthLabel = '5GHz 📶';
    } else if (smoothedRtt <= 90) {
      // Standard 2.4 GHz / Mobile Hotspot / USB Dongle
      targetQuality = 70;
      targetScale = 0.78;
      bandwidthLabel = '2.4GHz 📶';
    } else if (smoothedRtt <= 150) {
      // Congested 2.4 GHz / Weak signal
      targetQuality = 58;
      targetScale = 0.65;
      bandwidthLabel = '2.4G Slow ⚠️';
    } else {
      // High packet loss / Severe interference spike
      targetQuality = 45;
      targetScale = 0.50;
      bandwidthLabel = 'Lag Guard 🛡️';
    }

    // Fast-drop on latency spike (immediate drop to prevent queue backlog)
    const isDegrading = (targetQuality < currentAppliedQuality);
    if (isDegrading) {
      stableTicks = 0;
      currentAppliedQuality = targetQuality;
      currentAppliedScale = targetScale;
      state.streamQuality = currentAppliedQuality;
      state.streamScale = currentAppliedScale;
      sendStreamConfig();
    } else if (targetQuality > currentAppliedQuality) {
      // Hysteresis: Require 3 consecutive stable checks (4.5 seconds) before stepping up quality
      stableTicks++;
      if (stableTicks >= 3) {
        stableTicks = 0;
        currentAppliedQuality = targetQuality;
        currentAppliedScale = targetScale;
        state.streamQuality = currentAppliedQuality;
        state.streamScale = currentAppliedScale;
        sendStreamConfig();
      }
    } else {
      stableTicks = 0;
    }

    // Update status label or latency pill
    if (lastAutoBandwidthClass !== bandwidthLabel) {
      lastAutoBandwidthClass = bandwidthLabel;
      if (el.statusLabel && mainWs && mainWs.readyState === WebSocket.OPEN) {
        el.statusLabel.textContent = `${bandwidthLabel} ${smoothedRtt}ms`;
      }
    }
  }

  function connectScreenWs() {
    if (screenReconnectTimer) {
      clearTimeout(screenReconnectTimer);
      screenReconnectTimer = null;
    }
    // If socket is already OPEN or CONNECTING, do not tear it down
    if (screenWs && (screenWs.readyState === WebSocket.OPEN || screenWs.readyState === WebSocket.CONNECTING)) {
      sendStreamConfig();
      return;
    }
    try {
      if (screenWs) {
        screenWs.onopen = null;
        screenWs.onmessage = null;
        screenWs.onclose = null;
        screenWs.onerror = null;
        try { screenWs.close(); } catch (e) {}
        screenWs = null;
      }
      lastScreenFrameReceivedTime = Date.now();
      if (!screenFirstFrameSeen) {
        showScreenLoader('STREAMING PC SCREEN...');
      }
      const ws = new WebSocket(state.screenWsUrl);
      screenWs = ws;
      ws.binaryType = 'blob';
      ws.onopen = () => {
        if (ws !== screenWs) return;
        state.screenConnected = true;
        lastScreenFrameReceivedTime = Date.now();
        startScreenWatchdog();
        // Re-apply encoder settings
        sendStreamConfig();
      };
      ws.onmessage = (event) => {
        if (ws !== screenWs) return;
        if (event.data) {
          lastScreenFrameReceivedTime = Date.now();
          renderScreenFrame(event.data);
        }
      };
      ws.onclose = () => {
        if (ws !== screenWs) return;
        state.screenConnected = false;
        if (state.connected && !screenReconnectTimer) {
          screenReconnectTimer = setTimeout(() => {
            screenReconnectTimer = null;
            if (state.connected) connectScreenWs();
          }, 1200);
        }
      };
      ws.onerror = () => {
        if (ws !== screenWs) return;
        state.screenConnected = false;
        try { ws.close(); } catch (e) {}
      };
    } catch (e) {
      console.error('Failed to open screen WebSocket:', e);
    }
  }

  let reconnectAttempts = 0;

  function onMainWsOpen() {
    reconnectAttempts = 0;
    state.connected = true;
    updateStatus('connected', 'Connected');
    if (el.connectModal) el.connectModal.classList.remove('show');
    showToast(`Connected to PC (${state.serverHost})`, 'success', '💻');
    vibrate(40);

    if (state.autoReconnectTimer) {
      clearInterval(state.autoReconnectTimer);
      state.autoReconnectTimer = null;
    }

    saveAllSettings(false);

    if (pingInterval) clearInterval(pingInterval);
    pingInterval = setInterval(() => {
      if (mainWs && mainWs.readyState === WebSocket.OPEN) {
        mainWs.send(`p,${Date.now()}`);
      }
    }, 1500);

    // Refresh Places & Current Directory
    loadFsPlaces();

    // Auto-enable PC audio streaming if enabled in preferences.
    // Never override a manual stop, or every auto-reconnect would revive the stream.
    if (state.autoAudioStream && !audioStreamActive && !userManuallyStoppedAudio) {
      startAudioStream();
    }
  }

  function onMainWsMessage(event) {
    const data = event.data;
    if (data.startsWith('pong,')) {
      const sentTime = parseInt(data.split(',')[1], 10);
      state.latency = Math.max(1, Date.now() - sentTime);
      if (el.latencyVal) el.latencyVal.textContent = `${state.latency}ms`;
      updateAdaptiveQuality(state.latency);
      return;
    }

    // --- Reverse Control Commands from PC ---
    if (data.startsWith('phone_tap,')) {
      const parts = data.split(',');
      const x = parseFloat(parts[1]);
      const y = parseFloat(parts[2]);
      if (window.AndroidApp && typeof window.AndroidApp.dispatchPhoneTap === 'function') {
        window.AndroidApp.dispatchPhoneTap(x, y);
      }
    } else if (data.startsWith('phone_swipe,')) {
      const parts = data.split(',');
      const x1 = parseFloat(parts[1]);
      const y1 = parseFloat(parts[2]);
      const x2 = parseFloat(parts[3]);
      const y2 = parseFloat(parts[4]);
      const duration = parseInt(parts[5] || '300', 10);
      if (window.AndroidApp && typeof window.AndroidApp.dispatchPhoneSwipe === 'function') {
        window.AndroidApp.dispatchPhoneSwipe(x1, y1, x2, y2, duration);
      }
    } else if (data.startsWith('phone_nav,')) {
      const action = data.split(',')[1];
      if (window.AndroidApp && typeof window.AndroidApp.dispatchPhoneNav === 'function') {
        window.AndroidApp.dispatchPhoneNav(action);
      }
    } else if (data.startsWith('phone_text,')) {
      const text = data.substring('phone_text,'.length);
      if (window.AndroidApp && typeof window.AndroidApp.dispatchPhoneText === 'function') {
        window.AndroidApp.dispatchPhoneText(text);
      }
    }
  }

  function onMainWsClose() {
    state.connected = false;
    reconnectAttempts++;

    if (reconnectAttempts >= 3) {
      updateStatus('disconnected', 'Reconnecting... (Check VPN/Wi-Fi)');
      if (reconnectAttempts === 3) {
        showToast(`Cannot reach PC (${state.serverHost}). If VPN is ON, pause it or allow LAN`, 'warn', '⚠️');
      }
    } else {
      updateStatus('disconnected', 'Reconnecting...');
    }

    if (pingInterval) clearInterval(pingInterval);
    if (audioStreamActive) {
      stopAudioStream();
    }

    if (!state.autoReconnectTimer && localStorage.getItem('neontrack_ip')) {
      state.autoReconnectTimer = setInterval(() => {
        if (!state.connected) {
          connect();
        } else {
          clearInterval(state.autoReconnectTimer);
          state.autoReconnectTimer = null;
        }
      }, 3000);
    }
  }

  function onMainWsError() {
    state.connected = false;
    updateStatus('disconnected', 'Disconnected');
    const isNativeApp = !!window.AndroidApp || window.location.protocol === 'file:';
    if (!localStorage.getItem('neontrack_ip') && el.connectModal && isNativeApp) {
      el.connectModal.classList.add('show');
    }
  }

  function updateStatus(status, label) {
    if (!el.statusIndicator || !el.statusLabel) return;
    el.statusLabel.textContent = label;
    if (status === 'connected') {
      el.statusIndicator.className = 'status-dot connected';
    } else {
      el.statusIndicator.className = 'status-dot';
      if (el.latencyVal) el.latencyVal.textContent = '--ms';
    }
  }

  function sendCommand(cmdStr) {
    if (mainWs && mainWs.readyState === WebSocket.OPEN) {
      mainWs.send(cmdStr);
    } else if (screenWs && screenWs.readyState === WebSocket.OPEN) {
      screenWs.send(cmdStr);
    }
  }

  function sendScreenCommand(cmdStr) {
    if (mainWs && mainWs.readyState === WebSocket.OPEN) {
      mainWs.send(cmdStr);
    } else if (screenWs && screenWs.readyState === WebSocket.OPEN) {
      screenWs.send(cmdStr);
    }
  }

  // --- High-Performance Hardware-Accelerated Zero-Lag Screen Frame Renderer ---
  let isDecodingScreen = false;
  let nextFrameBuffer = null;
  let cachedScreenImg = new Image();
  let activeBlobUrl = null;

  function renderScreenFrame(data) {
    if (!data) return;
    if (typeof data === 'string') {
      // Keepalive heartbeat
      lastScreenFrameReceivedTime = Date.now();
      return;
    }
    lastScreenFrameReceivedTime = Date.now();
    nextFrameBuffer = data;
    if (!isDecodingScreen) {
      processNextScreenFrame();
    }
  }

  async function processNextScreenFrame() {
    if (!nextFrameBuffer || !el.screenCanvas) {
      isDecodingScreen = false;
      return;
    }
    isDecodingScreen = true;
    const data = nextFrameBuffer;
    nextFrameBuffer = null;

    if (!screenCtx) {
      screenCtx = el.screenCanvas.getContext('2d', { alpha: false, desynchronized: true });
      if (screenCtx) {
        screenCtx.imageSmoothingEnabled = true;
        screenCtx.imageSmoothingQuality = 'high';
      }
    }

    let renderedOk = false;
    try {
      const blob = (data instanceof Blob) ? data : new Blob([data], { type: 'image/jpeg' });

      // Primary Decoder: Hardware-Accelerated createImageBitmap
      if (window.createImageBitmap) {
        try {
          const bmp = await createImageBitmap(blob);
          if (el.screenCanvas.width !== bmp.width || el.screenCanvas.height !== bmp.height) {
            el.screenCanvas.width = bmp.width;
            el.screenCanvas.height = bmp.height;
            screenCtx = el.screenCanvas.getContext('2d', { alpha: false, desynchronized: true });
            if (screenCtx) {
              screenCtx.imageSmoothingEnabled = true;
              screenCtx.imageSmoothingQuality = 'high';
            }
          }
          if (screenCtx) {
            screenCtx.drawImage(bmp, 0, 0);
            renderedOk = true;
          }
          if (bmp.close) bmp.close();
        } catch (bmpErr) {
          console.warn('createImageBitmap failed, falling back to Image element:', bmpErr);
        }
      }

      // Secondary Decoder: HTML5 Image element fallback
      if (!renderedOk) {
        await new Promise((resolve) => {
          if (activeBlobUrl) URL.revokeObjectURL(activeBlobUrl);
          activeBlobUrl = URL.createObjectURL(blob);
          cachedScreenImg.onload = () => {
            if (el.screenCanvas.width !== cachedScreenImg.naturalWidth || el.screenCanvas.height !== cachedScreenImg.naturalHeight) {
              el.screenCanvas.width = cachedScreenImg.naturalWidth;
              el.screenCanvas.height = cachedScreenImg.naturalHeight;
              screenCtx = el.screenCanvas.getContext('2d', { alpha: false, desynchronized: true });
              if (screenCtx) {
                screenCtx.imageSmoothingEnabled = true;
                screenCtx.imageSmoothingQuality = 'high';
              }
            }
            if (screenCtx) {
              screenCtx.drawImage(cachedScreenImg, 0, 0);
              renderedOk = true;
            }
            resolve();
          };
          cachedScreenImg.onerror = (err) => {
            console.warn('Image element render error:', err);
            resolve();
          };
          cachedScreenImg.src = activeBlobUrl;
        });
      }

      if (renderedOk || screenFirstFrameSeen) {
        if (el.screenLoader && el.screenLoader.style.display !== 'none') {
          el.screenLoader.style.display = 'none';
        }
        screenFirstFrameSeen = true;
      }
    } catch (e) {
      console.warn('Frame render error:', e);
    } finally {
      if (nextFrameBuffer) {
        setTimeout(processNextScreenFrame, 0);
      } else {
        isDecodingScreen = false;
      }
    }
  }

  // --- Jitter-Free EMA Low-Pass Filter Trackpad ---
  function initTrackpad() {
    const surface = el.trackpadSurface;
    if (!surface) return;

    let touchActive = false;
    let startX = 0, startY = 0;
    let lastX = 0, lastY = 0;
    let tapStartTime = 0;
    let totalMoved = 0;

    // Frame-coalesced kinematic filtering variables
    let filteredDx = 0;
    let filteredDy = 0;
    let pendingDx = 0;
    let pendingDy = 0;
    let rAfScheduled = false;

    // Quick Speed Preset Toggle Button
    if (el.btnSpeedQuick) {
      const SPEED_PRESETS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5];
      el.btnSpeedQuick.onclick = () => {
        let currentIdx = SPEED_PRESETS.findIndex(s => Math.abs(s - state.cursorSpeed) < 0.1);
        let nextIdx = (currentIdx + 1) % SPEED_PRESETS.length;
        if (currentIdx === -1) nextIdx = 1;
        state.cursorSpeed = SPEED_PRESETS[nextIdx];
        el.btnSpeedQuick.textContent = `${state.cursorSpeed.toFixed(1)}x`;
        if (el.settingCursorSpeed) el.settingCursorSpeed.value = state.cursorSpeed.toString();
        if (el.valCursorSpeed) el.valCursorSpeed.textContent = `${state.cursorSpeed.toFixed(1)}x`;
        vibrate(25);
        showToast(`Mouse Speed: ${state.cursorSpeed.toFixed(1)}x`, 'success', '🖱️');
        saveAllSettings(false);
      };
    }

    function flushMovement() {
      rAfScheduled = false;
      if (!touchActive && pendingDx === 0 && pendingDy === 0) return;

      const rawDx = pendingDx;
      const rawDy = pendingDy;
      pendingDx = 0;
      pendingDy = 0;

      const moveDist = Math.hypot(rawDx, rawDy);
      if (moveDist < 0.08) return;

      // Adaptive Dynamic Smoothing:
      // High responsiveness for real movements, strong damping for sub-pixel digitizer tremor
      const alpha = Math.min(1.0, Math.max(0.65, moveDist / 8.0));
      filteredDx = alpha * rawDx + (1.0 - alpha) * filteredDx;
      filteredDy = alpha * rawDy + (1.0 - alpha) * filteredDy;

      let sendDx = filteredDx * state.cursorSpeed * 1.35;
      let sendDy = filteredDy * state.cursorSpeed * 1.35;

      if (state.smoothAccel) {
        // Natural ballistic curve: 1.0x at low speed, accelerating smoothly up to 2.5x on rapid swipes
        let accelFactor = 1.0;
        if (moveDist > 2.0) {
          accelFactor = 1.0 + Math.min(1.6, (moveDist - 2.0) * 0.08);
        }
        sendDx *= accelFactor;
        sendDy *= accelFactor;
      }

      sendCommand(`m,${sendDx.toFixed(2)},${sendDy.toFixed(2)}`);
    }

    surface.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        touchActive = true;
        const t = e.touches[0];
        startX = lastX = t.clientX;
        startY = lastY = t.clientY;
        tapStartTime = Date.now();
        totalMoved = 0;
        filteredDx = 0;
        filteredDy = 0;
        pendingDx = 0;
        pendingDy = 0;
      } else if (e.touches.length === 2) {
        vibrate(20);
        sendCommand('c,right');
        touchActive = false;
      }
    }, { passive: false });

    surface.addEventListener('touchmove', (e) => {
      if (!touchActive || e.touches.length !== 1) return;
      const t = e.touches[0];
      const dx = t.clientX - lastX;
      const dy = t.clientY - lastY;
      lastX = t.clientX;
      lastY = t.clientY;

      totalMoved += Math.hypot(dx, dy);
      pendingDx += dx;
      pendingDy += dy;

      if (!rAfScheduled) {
        rAfScheduled = true;
        requestAnimationFrame(flushMovement);
      }
      e.preventDefault();
    }, { passive: false });

    surface.addEventListener('touchend', (e) => {
      if (touchActive) {
        touchActive = false;
        flushMovement();
        const tapDuration = Date.now() - tapStartTime;
        if (tapDuration < 220 && totalMoved < 8) {
          vibrate(18);
          sendCommand('c,left');
        }
      }
    }, { passive: false });

    // Scroll Strip Handler
    if (el.scrollStrip) {
      let scrollStartY = 0;
      let scrollActive = false;

      el.scrollStrip.addEventListener('touchstart', (e) => {
        scrollActive = true;
        scrollStartY = e.touches[0].clientY;
        vibrate(10);
      }, { passive: false });

      el.scrollStrip.addEventListener('touchmove', (e) => {
        if (!scrollActive) return;
        const currentY = e.touches[0].clientY;
        const dy = currentY - scrollStartY;
        scrollStartY = currentY;

        let scrollDelta = dy * 4.0 * state.scrollSpeed * (state.invertScroll ? -1 : 1);
        sendCommand(`s,0,${scrollDelta.toFixed(1)}`);
        e.preventDefault();
      }, { passive: false });

      el.scrollStrip.addEventListener('touchend', () => {
        scrollActive = false;
      }, { passive: false });
    }
  }

  // --- Global Navigation Tab Switching Function ---
  function switchTab(targetId) {
    if (!targetId) return;
    vibrate(15);
    state.activeTab = targetId;

    if (el.dockTabs) {
      el.dockTabs.forEach((t) => {
        if (t.dataset.target === targetId) {
          t.classList.add('active');
        } else {
          t.classList.remove('active');
        }
      });
    }

    if (el.tabViews) {
      el.tabViews.forEach((v) => {
        if (v.id === targetId) {
          v.classList.add('active');
        } else {
          v.classList.remove('active');
        }
      });
    }

    // If switched to Screen tab, verify screen stream liveness without destroying open sockets
    if (targetId === 'tab-screen') {
      if (state.connected) {
        if (!screenWs || screenWs.readyState === WebSocket.CLOSED || screenWs.readyState === WebSocket.CLOSING) {
          connectScreenWs();
        } else if (screenWs.readyState === WebSocket.OPEN) {
          sendStreamConfig();
        }
      }
    } else if (typeof window.closeScreenTypeBar === 'function') {
      // Leaving the screen view: don't leave the typing overlay open behind other tabs.
      window.closeScreenTypeBar();
    }

    // If switched to files tab, refresh directory listing
    if (targetId === 'tab-files') {
      loadFsPlaces();
      loadPhonePlaces();
      let targetPath = state.currentFsPath;
      try {
        const savedPath = localStorage.getItem('neontrack_last_fs_path');
        if (savedPath) targetPath = savedPath;
      } catch (e) {}
      browseFsDirectory(targetPath);

      let targetPhonePath = state.phoneFs.currentPath || 'default';
      try {
        const savedPhonePath = localStorage.getItem('neontrack_last_phone_fs_path');
        if (savedPhonePath) targetPhonePath = savedPhonePath;
      } catch (e) {}
      state.phoneFs.currentPath = targetPhonePath;
    }

    // Ensure Android hardware immersive fullscreen is applied
    if (window.AndroidApp && typeof window.AndroidApp.setImmersiveFullscreen === 'function') {
      window.AndroidApp.setImmersiveFullscreen(true);
    }
  }

  // --- Universal Virtual Keyboard & Live Typing Engine ---
  // Shared soft-keyboard interceptor: mirrors what is typed on the phone straight to
  // the PC. Used by the Keys tab and by the on-screen TYPE overlay in the screen view.
  function attachLiveTyping(inputEl, clearBtn) {
    if (!inputEl || inputEl.dataset.liveTypingBound === '1') return;
    inputEl.dataset.liveTypingBound = '1';

    let prevVal = '';
    let isComposing = false;

    function processInputDelta() {
      if (isComposing) return;
      const cur = inputEl.value;
      if (cur === prevVal) return;

      if (cur.startsWith(prevVal)) {
        // New characters added to end (typed or pasted)
        const added = cur.slice(prevVal.length);
        if (added) {
          sendCommand(`t,${added}`);
        }
      } else if (prevVal.startsWith(cur)) {
        // Characters deleted (backspace)
        const deletedCount = prevVal.length - cur.length;
        for (let i = 0; i < deletedCount; i++) {
          sendCommand('k,backspace');
        }
      } else {
        // Replacement / auto-correct / pasted text
        for (let i = 0; i < prevVal.length; i++) {
          sendCommand('k,backspace');
        }
        if (cur) {
          sendCommand(`t,${cur}`);
        }
      }

      prevVal = cur;

      // Reset buffer if getting long to prevent unbounded memory/length
      if (cur.length > 50) {
        inputEl.value = '';
        prevVal = '';
      }
    }

    inputEl.addEventListener('compositionstart', () => {
      isComposing = true;
    });

    inputEl.addEventListener('compositionend', () => {
      isComposing = false;
      processInputDelta();
    });

    inputEl.addEventListener('input', () => {
      processInputDelta();
    });

    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        vibrate(15);
        sendCommand('k,enter');
        inputEl.value = '';
        prevVal = '';
      } else if (e.key === 'Backspace' && inputEl.value === '') {
        vibrate(10);
        sendCommand('k,backspace');
      } else if (e.key === 'Tab') {
        e.preventDefault();
        vibrate(15);
        sendCommand('k,tab');
      } else if (e.key === 'Escape') {
        e.preventDefault();
        vibrate(15);
        sendCommand('k,escape');
        inputEl.blur();
      }
    });

    if (clearBtn) {
      clearBtn.onclick = () => {
        vibrate(15);
        inputEl.value = '';
        prevVal = '';
        inputEl.focus();
      };
    }

    // Lets callers reset the diff baseline when the field is shown/hidden.
    inputEl.resetLiveTyping = () => {
      inputEl.value = '';
      prevVal = '';
    };
  }

  // --- On-Screen Quick Typing Overlay (Screen Streaming View) ---
  function initScreenKeyboard() {
    const fab = document.getElementById('btn-screen-keyboard');
    const bar = document.getElementById('screen-type-bar');
    const input = document.getElementById('screen-typing-input');
    const btnClose = document.getElementById('btn-screen-type-close');
    const btnEnter = document.getElementById('btn-screen-type-enter');
    if (!fab || !bar || !input) return;

    attachLiveTyping(input, null);

    function openTypeBar() {
      bar.hidden = false;
      fab.classList.add('active');
      if (input.resetLiveTyping) input.resetLiveTyping();
      // Focus must happen in the same gesture or Android will not raise the keyboard.
      input.focus();
      showToast('Typing to PC — tap ✕ to close', 'success', '⌨️');
    }

    function closeTypeBar() {
      if (input.resetLiveTyping) input.resetLiveTyping();
      input.blur();
      bar.hidden = true;
      fab.classList.remove('active');
    }

    fab.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      vibrate(20);
      if (bar.hidden) {
        openTypeBar();
      } else {
        closeTypeBar();
      }
    });

    if (btnClose) {
      btnClose.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        vibrate(15);
        closeTypeBar();
      });
    }

    if (btnEnter) {
      btnEnter.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        vibrate(15);
        sendCommand('k,enter');
        if (input.resetLiveTyping) input.resetLiveTyping();
        input.focus();
      });
    }

    // Keep taps inside the bar from reaching the canvas gesture handlers underneath.
    ['touchstart', 'touchmove', 'touchend', 'click'].forEach((evt) => {
      bar.addEventListener(evt, (e) => e.stopPropagation());
    });

    // Leaving the screen tab should not strand an open keyboard bar.
    window.closeScreenTypeBar = closeTypeBar;
  }

  function initVirtualKeyboard() {
    const liveInput = document.getElementById('live-typing-input');
    const btnClearLive = document.getElementById('btn-clear-live-text');
    const batchInput = document.getElementById('text-input');
    const btnSendText = document.getElementById('btn-send-text');
    const btnKbdQuick = document.getElementById('btn-kbd-quick');

    if (btnKbdQuick) {
      btnKbdQuick.onclick = (e) => {
        e.preventDefault();
        vibrate(20);
        switchTab('tab-keyboard');
        setTimeout(() => {
          if (liveInput) liveInput.focus();
        }, 200);
        showToast('Keyboard & PC Typing Active', 'success', '⌨️');
      };
    }

    // 1. Live Real-Time Keystroke Interceptor for Phone Soft Keyboards (Gboard, Samsung, etc.)
    attachLiveTyping(liveInput, btnClearLive);
    function setKbdPanel(activeBtn, activePanel) {
      [el.btnTabQwerty, el.btnTabNumpad, el.btnTabFn].forEach(b => b && b.classList.remove('active'));
      [el.panelQwerty, el.panelNumpad, el.panelFn].forEach(p => p && p.classList.remove('active'));
      if (activeBtn) activeBtn.classList.add('active');
      if (activePanel) activePanel.classList.add('active');
      vibrate(15);
    }

    if (el.btnTabQwerty) el.btnTabQwerty.onclick = () => setKbdPanel(el.btnTabQwerty, el.panelQwerty);
    if (el.btnTabNumpad) el.btnTabNumpad.onclick = () => setKbdPanel(el.btnTabNumpad, el.panelNumpad);
    if (el.btnTabFn) el.btnTabFn.onclick = () => setKbdPanel(el.btnTabFn, el.panelFn);

    // Key Buttons Click Delegation
    document.querySelectorAll('.vk-key').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        vibrate(12);

        if (btn.id === 'vk-caps') {
          state.capsLock = !state.capsLock;
          btn.classList.toggle('active', state.capsLock);
          return;
        }
        if (btn.id === 'vk-shift') {
          state.shiftPressed = !state.shiftPressed;
          btn.classList.toggle('active', state.shiftPressed);
          return;
        }
        if (btn.id === 'vk-ctrl') {
          state.ctrlPressed = !state.ctrlPressed;
          btn.classList.toggle('active', state.ctrlPressed);
          return;
        }
        if (btn.id === 'vk-alt') {
          state.altPressed = !state.altPressed;
          btn.classList.toggle('active', state.altPressed);
          return;
        }

        const char = btn.dataset.typeChar;
        const text = btn.dataset.text;
        const key = btn.dataset.key;
        const hotkey = btn.dataset.hotkey;

        if (hotkey) {
          sendCommand(`h,${hotkey}`);
          showToast(`Hotkey: ${hotkey.toUpperCase()}`, 'success', '⌨️');
          return;
        }

        if (char) {
          let outChar = char;
          const isUpper = state.capsLock !== state.shiftPressed;
          outChar = isUpper ? char.toUpperCase() : char.toLowerCase();

          if (state.ctrlPressed) {
            sendCommand(`h,ctrl+${char.toLowerCase()}`);
          } else if (state.altPressed) {
            sendCommand(`h,alt+${char.toLowerCase()}`);
          } else {
            sendCommand(`t,${outChar}`);
          }

          if (state.shiftPressed) {
            state.shiftPressed = false;
            if (el.vkShift) el.vkShift.classList.remove('active');
          }
          return;
        }

        if (text) {
          sendCommand(`t,${text}`);
          return;
        }

        if (key) {
          let prefix = '';
          if (state.ctrlPressed) prefix += 'ctrl+';
          if (state.altPressed) prefix += 'alt+';
          if (state.shiftPressed) prefix += 'shift+';

          if (prefix) {
            sendCommand(`h,${prefix}${key}`);
          } else {
            sendCommand(`k,${key}`);
          }

          if (state.shiftPressed) {
            state.shiftPressed = false;
            if (el.vkShift) el.vkShift.classList.remove('active');
          }
        }
      });
    });
  }

  // --- In-Built PC File Manager & Explorer Module ---
  function updateBatchBar() {
    if (!el.fsBatchBar) return;
    const count = state.markedFsPaths.size;
    if (count > 0) {
      el.fsBatchBar.style.display = 'flex';
      if (el.fsBatchCountLabel) el.fsBatchCountLabel.textContent = `${count} marked`;
      if (el.fsBatchDlLabel) el.fsBatchDlLabel.textContent = `SAVE TO PHONE (${count})`;
      const allPaths = [...state.fsFolders.map(f => f.path), ...state.fsFiles.map(f => f.path)];
      const allSelected = allPaths.length > 0 && allPaths.every(p => state.markedFsPaths.has(p));
      if (el.fsBatchSelectAll) el.fsBatchSelectAll.checked = allSelected;
    } else {
      el.fsBatchBar.style.display = 'none';
      if (el.fsBatchSelectAll) el.fsBatchSelectAll.checked = false;
      if (el.fsBatchDlLabel) el.fsBatchDlLabel.textContent = 'SAVE TO PHONE';
    }
  }

  function initFileManager() {
    function setFilesMode(mode) {
      if (mode === 'pc') {
        if (el.btnFsModePc) el.btnFsModePc.classList.add('active');
        if (el.btnFsModePhone) el.btnFsModePhone.classList.remove('active');
        if (el.fsPcPanel) el.fsPcPanel.style.display = 'flex';
        if (el.fsPhonePanel) el.fsPhonePanel.style.display = 'none';
      } else {
        if (el.btnFsModePhone) el.btnFsModePhone.classList.add('active');
        if (el.btnFsModePc) el.btnFsModePc.classList.remove('active');
        if (el.fsPhonePanel) el.fsPhonePanel.style.display = 'flex';
        if (el.fsPcPanel) el.fsPcPanel.style.display = 'none';
        loadPhonePlaces();
        let targetPhonePath = state.phoneFs.currentPath || 'default';
        try {
          const saved = localStorage.getItem('neontrack_last_phone_fs_path');
          if (saved) targetPhonePath = saved;
        } catch (e) {}
        browsePhoneDirectory(targetPhonePath);
      }
    }

    if (el.btnFsModePc) {
      el.btnFsModePc.onclick = () => {
        vibrate(15);
        setFilesMode('pc');
      };
    }

    if (el.btnFsModePhone) {
      el.btnFsModePhone.onclick = () => {
        vibrate(15);
        setFilesMode('phone');
      };
    }

    const btnGrantStorage = document.getElementById('btn-grant-storage');
    if (btnGrantStorage) {
      btnGrantStorage.onclick = () => {
        vibrate(20);
        if (window.AndroidApp && typeof window.AndroidApp.requestStoragePermission === 'function') {
          window.AndroidApp.requestStoragePermission();
        } else {
          showToast('Storage permission granted', 'info', '📁');
        }
      };
    }

    if (el.btnPhoneFsUp) {
      el.btnPhoneFsUp.onclick = () => {
        if (state.phoneFs.parentPath) {
          vibrate(15);
          browsePhoneDirectory(state.phoneFs.parentPath);
        }
      };
    }

    if (el.btnPhoneFsRefresh) {
      el.btnPhoneFsRefresh.onclick = () => {
        vibrate(15);
        browsePhoneDirectory(state.phoneFs.currentPath);
      };
    }

    if (el.btnPhoneFsNewFolder) {
      el.btnPhoneFsNewFolder.onclick = () => {
        const folderName = prompt('Enter new phone folder name:');
        if (folderName && folderName.trim()) {
          vibrate(20);
          if (window.AndroidApp && typeof window.AndroidApp.createPhoneFolder === 'function') {
            const success = window.AndroidApp.createPhoneFolder(state.phoneFs.currentPath, folderName.trim());
            if (success) {
              showToast(`Folder "${folderName}" created on phone!`, 'success', '📁');
              browsePhoneDirectory(state.phoneFs.currentPath);
            } else {
              showToast('Failed to create folder on phone', 'error', '❌');
            }
          }
        }
      };
    }

    if (el.btnPhoneFsUploadToPc && el.filePicker) {
      el.btnPhoneFsUploadToPc.onclick = () => {
        vibrate(18);
        el.filePicker.accept = '*/*';
        el.filePicker.click();
      };
    }

    if (el.phoneFsSearchInput) {
      el.phoneFsSearchInput.addEventListener('input', (e) => {
        state.phoneFs.filterText = e.target.value.toLowerCase().trim();
        renderFilteredPhoneFsItems();
      });
    }

    if (el.phoneFsBatchSelectAll) {
      el.phoneFsBatchSelectAll.onchange = () => {
        vibrate(15);
        const shouldSelect = el.phoneFsBatchSelectAll.checked;
        const allItems = [...state.phoneFs.folders, ...state.phoneFs.files];
        if (shouldSelect) {
          allItems.forEach(item => state.phoneFs.markedPaths.add(item.path));
        } else {
          state.phoneFs.markedPaths.clear();
        }
        updatePhoneBatchBar();
        renderFilteredPhoneFsItems();
      };
    }

    if (el.btnPhoneFsBatchClear) {
      el.btnPhoneFsBatchClear.onclick = () => {
        state.phoneFs.markedPaths.clear();
        updatePhoneBatchBar();
        renderFilteredPhoneFsItems();
      };
    }

    if (el.btnPhoneFsBatchDelete) {
      el.btnPhoneFsBatchDelete.onclick = () => {
        const count = state.phoneFs.markedPaths.size;
        if (count === 0) return;
        if (confirm(`Delete ${count} marked item(s) on phone?`)) {
          vibrate(25);
          if (window.AndroidApp && typeof window.AndroidApp.deletePhoneFile === 'function') {
            state.phoneFs.markedPaths.forEach(path => window.AndroidApp.deletePhoneFile(path));
            showToast(`${count} item(s) deleted on phone`, 'warn', '🗑️');
            state.phoneFs.markedPaths.clear();
            updatePhoneBatchBar();
            browsePhoneDirectory(state.phoneFs.currentPath);
          }
        }
      };
    }

    if (el.btnPhoneFsBatchSendPc) {
      el.btnPhoneFsBatchSendPc.onclick = () => {
        const paths = Array.from(state.phoneFs.markedPaths);
        if (paths.length === 0) {
          showToast('No phone files marked', 'warn', '⚠️');
          return;
        }
        vibrate(20);
        uploadMarkedPhoneFilesToPc(paths);
      };
    }

    if (el.btnFsUploadHere && el.filePicker) {
      el.btnFsUploadHere.onclick = () => {
        vibrate(18);
        el.filePicker.accept = '*/*';
        el.filePicker.click();
      };

      el.filePicker.onchange = () => {
        if (el.filePicker.files && el.filePicker.files.length > 0) {
          uploadFilesToCurrentDir(el.filePicker.files);
        }
      };
    }

    if (el.btnFsRefresh) {
      el.btnFsRefresh.onclick = () => {
        vibrate(15);
        browseFsDirectory(state.currentFsPath);
      };
    }

    if (el.btnFsUp) {
      el.btnFsUp.onclick = () => {
        if (state.fsParentPath) {
          vibrate(15);
          browseFsDirectory(state.fsParentPath);
        }
      };
    }

    if (el.btnFsNewFolder) {
      el.btnFsNewFolder.onclick = () => {
        const folderName = prompt('Enter new folder name:');
        if (folderName && folderName.trim()) {
          vibrate(20);
          fetch(`http://${state.serverHost}:${state.serverPort}/api/fs/mkdir?parent_dir=${encodeURIComponent(state.currentFsPath)}&folder_name=${encodeURIComponent(folderName.trim())}`, { method: 'POST' })
            .then(r => r.json())
            .then(data => {
              if (data.status === 'created') {
                showToast(`Folder "${folderName}" created!`, 'success', '📁');
                browseFsDirectory(state.currentFsPath);
              } else {
                showToast('Failed to create folder', 'error', '❌');
              }
            })
            .catch(() => showToast('Error creating folder', 'error', '❌'));
        }
      };
    }

    if (el.fsSearchInput) {
      el.fsSearchInput.addEventListener('input', (e) => {
        state.fsFilterText = e.target.value.toLowerCase().trim();
        renderFilteredFsItems();
      });
    }

    // Dismissible Tip Strips
    const fsTipStrip = document.getElementById('fs-tip-strip');
    const btnFsDismissTip = document.getElementById('btn-fs-dismiss-tip');
    if (localStorage.getItem('pcdeck_fs_tip_dismissed') === '1' && fsTipStrip) {
      fsTipStrip.style.display = 'none';
    }
    if (btnFsDismissTip && fsTipStrip) {
      btnFsDismissTip.onclick = () => {
        vibrate(10);
        fsTipStrip.style.display = 'none';
        localStorage.setItem('pcdeck_fs_tip_dismissed', '1');
      };
    }

    const phoneFsTipStrip = document.getElementById('phone-fs-tip-strip');
    const btnPhoneDismissTip = document.getElementById('btn-phone-dismiss-tip');
    if (localStorage.getItem('pcdeck_phone_tip_dismissed') === '1' && phoneFsTipStrip) {
      phoneFsTipStrip.style.display = 'none';
    }
    if (btnPhoneDismissTip && phoneFsTipStrip) {
      btnPhoneDismissTip.onclick = () => {
        vibrate(10);
        phoneFsTipStrip.style.display = 'none';
        localStorage.setItem('pcdeck_phone_tip_dismissed', '1');
      };
    }

    // Batch Actions Event Handlers
    if (el.fsBatchSelectAll) {
      el.fsBatchSelectAll.onchange = () => {
        vibrate(15);
        const shouldSelect = el.fsBatchSelectAll.checked;
        const allItems = [...state.fsFolders, ...state.fsFiles];
        if (shouldSelect) {
          allItems.forEach(item => state.markedFsPaths.add(item.path));
        } else {
          state.markedFsPaths.clear();
        }
        updateBatchBar();
        renderFilteredFsItems();
      };
    }

    if (el.btnFsBatchDownload) {
      el.btnFsBatchDownload.onclick = () => {
        if (state.markedFsPaths.size === 0) {
          showToast('No files marked for download', 'warn', '⚠️');
          return;
        }
        vibrate(20);
        downloadMarkedFilesSequentially(Array.from(state.markedFsPaths));
      };
    }

    if (el.btnFsBatchDelete) {
      el.btnFsBatchDelete.onclick = () => {
        const count = state.markedFsPaths.size;
        if (count === 0) return;
        if (confirm(`Delete ${count} marked item(s) on PC?`)) {
          vibrate(25);
          fetch(`http://${state.serverHost}:${state.serverPort}/api/fs/delete-batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(Array.from(state.markedFsPaths)),
          })
            .then(r => r.json())
            .then(data => {
              showToast(`Deleted ${data.deleted || count} items from PC`, 'warn', '🗑️');
              state.markedFsPaths.clear();
              updateBatchBar();
              browseFsDirectory(state.currentFsPath);
            })
            .catch(() => showToast('Batch delete failed', 'error', '❌'));
        }
      };
    }

    if (el.btnFsBatchClear) {
      el.btnFsBatchClear.onclick = () => {
        vibrate(10);
        state.markedFsPaths.clear();
        updateBatchBar();
        renderFilteredFsItems();
      };
    }
  }

  function loadFsPlaces() {
    fetch(`http://${state.serverHost}:${state.serverPort}/api/fs/places`)
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok' && el.fsPlacesStrip) {
          el.fsPlacesStrip.innerHTML = '';

          // Add Places
          (data.places || []).forEach(p => {
            const btn = document.createElement('button');
            btn.className = 'fs-place-chip';
            if (p.path === state.currentFsPath || (!state.currentFsPath && p.path.toLowerCase().includes('pcdeck_transfers'))) {
              btn.classList.add('active');
            }
            btn.textContent = `${p.icon} ${p.name.replace(/^[^\s]+\s/, '')}`;
            btn.onclick = () => {
              vibrate(15);
              document.querySelectorAll('.fs-place-chip').forEach(c => c.classList.remove('active'));
              btn.classList.add('active');
              browseFsDirectory(p.path);
            };
            el.fsPlacesStrip.appendChild(btn);
          });

          // Add Drives
          (data.drives || []).forEach(d => {
            const btn = document.createElement('button');
            btn.className = 'fs-place-chip';
            btn.style.borderColor = 'var(--neo-yellow)';
            btn.textContent = `💾 ${d.name}`;
            btn.onclick = () => {
              vibrate(15);
              document.querySelectorAll('.fs-place-chip').forEach(c => c.classList.remove('active'));
              btn.classList.add('active');
              browseFsDirectory(d.path);
            };
            el.fsPlacesStrip.appendChild(btn);
          });

          // Add Phone Downloads Chip
          const phoneBtn = document.createElement('button');
          phoneBtn.className = 'fs-place-chip';
          phoneBtn.style.background = 'rgba(0, 255, 102, 0.15)';
          phoneBtn.style.borderColor = 'var(--neo-lime)';
          phoneBtn.style.color = 'var(--neo-lime)';
          phoneBtn.style.fontWeight = '800';
          phoneBtn.textContent = '📱 Received from PC';
          phoneBtn.onclick = () => {
            vibrate(15);
            revealInPhoneFiles('default');
          };
          el.fsPlacesStrip.appendChild(phoneBtn);
        }
      })
      .catch(() => {});
  }

  function browseFsDirectory(path) {
    if (!el.fsBrowserItems) return;
    el.fsBrowserItems.innerHTML = `
      <div class="empty-files-placeholder">
        <span>📂</span>
        <p>Loading directory...</p>
      </div>
    `;

    fetch(`http://${state.serverHost}:${state.serverPort}/api/fs/browse?path=${encodeURIComponent(path || '')}`)
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          state.currentFsPath = data.current_path;
          state.fsParentPath = data.parent_path;
          state.fsFolders = data.folders || [];
          state.fsFiles = data.files || [];

          try {
            localStorage.setItem('neontrack_last_fs_path', data.current_path);
          } catch (e) {}

          if (el.fsCurrentPath) {
            const isTransfers = data.current_path.replace(/\\/g, '/').toLowerCase().endsWith('downloads/pcdeck_transfers') || data.current_path.replace(/\\/g, '/').toLowerCase().endsWith('pcdeck_transfers');
            el.fsCurrentPath.textContent = isTransfers ? '💻 Received from Phone' : '💻 ' + data.current_path;
            el.fsCurrentPath.title = data.current_path;
          }
          if (el.fsItemCount) el.fsItemCount.textContent = `${data.total_items} items`;
          if (el.btnFsUp) el.btnFsUp.disabled = data.is_root;

          updateBatchBar();
          renderFilteredFsItems();
        } else {
          el.fsBrowserItems.innerHTML = `
            <div class="empty-files-placeholder">
              <span>⚠️</span>
              <p>${data.error || 'Could not open folder'}</p>
            </div>
          `;
        }
      })
      .catch(() => {
        el.fsBrowserItems.innerHTML = `
          <div class="empty-files-placeholder">
            <span>⚠️</span>
            <p>Connect to PC to explore directories & files.</p>
          </div>
        `;
      });
  }

  function getFolderIcon(name) {
    const n = (name || '').toLowerCase().trim();
    if (n.includes('download')) return '⬇️';
    if (n.includes('desktop')) return '🖥️';
    if (n.includes('picture') || n.includes('photo') || n.includes('dcim') || n.includes('camera')) return '📸';
    if (n.includes('music') || n.includes('audio') || n.includes('sound')) return '🎵';
    if (n.includes('video') || n.includes('movie')) return '🎬';
    if (n.includes('doc') || n.includes('document')) return '📁';
    if (n.includes('pcdeck') || n.includes('transfer')) return '📥';
    return '📁';
  }

  function getFileIcon(ext) {
    ext = (ext || '').toLowerCase().trim();
    // Images & Graphics
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'heic', 'tiff'].includes(ext)) return '🖼️';
    if (['svg', 'ai', 'psd', 'eps', 'drawio'].includes(ext)) return '🎨';
    if (['ico', 'cur'].includes(ext)) return '💠';

    // Videos
    if (['mp4', 'mkv', 'webm', 'mov', 'avi', 'wmv', 'flv', 'm4v', '3gp', 'ts'].includes(ext)) return '🎬';

    // Audio & Music
    if (['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma', 'opus', 'mid', 'midi', 'aiff'].includes(ext)) return '🎵';

    // Documents & Office
    if (['pdf'].includes(ext)) return '📕';
    if (['doc', 'docx', 'odt', 'rtf', 'pages'].includes(ext)) return '📘';
    if (['xls', 'xlsx', 'csv', 'tsv', 'ods', 'numbers'].includes(ext)) return '📊';
    if (['ppt', 'pptx', 'odp', 'key'].includes(ext)) return '📽️';
    if (['txt', 'log', 'md', 'markdown', 'rst', 'nfo'].includes(ext)) return '📝';

    // Code & Developer
    if (['py', 'pyw', 'ipynb'].includes(ext)) return '🐍';
    if (['js', 'mjs', 'cjs'].includes(ext)) return '🟨';
    if (['ts', 'tsx'].includes(ext)) return '🔷';
    if (['html', 'htm'].includes(ext)) return '🌐';
    if (['css', 'scss', 'sass', 'less'].includes(ext)) return '🎨';
    if (['json', 'yaml', 'yml', 'xml', 'toml', 'ini', 'cfg', 'conf', 'env'].includes(ext)) return '⚙️';
    if (['java', 'kt', 'kts', 'class', 'jar'].includes(ext)) return '☕';
    if (['c', 'cpp', 'cc', 'cxx', 'h', 'hpp', 'cs', 'go', 'rs', 'swift'].includes(ext)) return '💻';
    if (['sh', 'bat', 'cmd', 'ps1', 'bash', 'zsh'].includes(ext)) return '📜';
    if (['sql', 'db', 'sqlite', 'sqlite3', 'mdb'].includes(ext)) return '🗄️';

    // Apps & Executables
    if (['apk', 'xapk', 'apks'].includes(ext)) return '📱';
    if (['exe', 'msi'].includes(ext)) return '💻';
    if (['iso', 'img', 'vmdk', 'dmg'].includes(ext)) return '💿';

    // Archives & Compressed
    if (['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'tgz'].includes(ext)) return '📦';

    // Fonts
    if (['ttf', 'otf', 'woff', 'woff2', 'eot'].includes(ext)) return '🔤';

    // Generic Default
    return '📄';
  }

  function renderFilteredFsItems() {
    if (!el.fsBrowserItems) return;
    el.fsBrowserItems.innerHTML = '';

    const filter = state.fsFilterText;
    const filteredFolders = state.fsFolders.filter(f => !filter || f.name.toLowerCase().includes(filter));
    const filteredFiles = state.fsFiles.filter(f => !filter || f.name.toLowerCase().includes(filter));

    if (filteredFolders.length === 0 && filteredFiles.length === 0) {
      el.fsBrowserItems.innerHTML = `
        <div class="empty-files-placeholder">
          <span>📂</span>
          <p>Folder is empty.<br>Tap Send Files above to transfer to PC!</p>
        </div>
      `;
      return;
    }

    // Render Folders First
    filteredFolders.forEach(folder => {
      const card = document.createElement('div');
      const isMarked = state.markedFsPaths.has(folder.path);
      card.className = `fs-item-card is-folder ${isMarked ? 'is-marked' : ''}`;
      const folderIcon = getFolderIcon(folder.name);
      card.innerHTML = `
        <div class="fs-item-info">
          <input type="checkbox" class="fs-item-checkbox" data-path="${folder.path}" ${isMarked ? 'checked' : ''}>
          <span class="fs-icon-badge">${folderIcon}</span>
          <div class="fs-item-details">
            <span class="fs-item-name" title="${folder.name}">${folder.name}</span>
            <span class="fs-item-meta">${folder.item_count !== undefined ? folder.item_count + ' items' : 'Folder'}</span>
          </div>
        </div>
        <div class="fs-actions-row">
          <button class="fs-btn fs-btn-open" data-action="open-folder" title="Open Folder">📂 Open</button>
          <button class="fs-btn fs-btn-locate fs-btn-icon-only" data-action="locate-folder-pc" title="Open this folder on PC in Windows File Explorer">🖥️</button>
          <button class="fs-btn fs-btn-del fs-btn-icon-only" data-action="del-folder" title="Delete Folder">🗑️</button>
        </div>
      `;

      const cb = card.querySelector('.fs-item-checkbox');
      const toggleMark = () => {
        vibrate(10);
        if (state.markedFsPaths.has(folder.path)) {
          state.markedFsPaths.delete(folder.path);
          card.classList.remove('is-marked');
          cb.checked = false;
        } else {
          state.markedFsPaths.add(folder.path);
          card.classList.add('is-marked');
          cb.checked = true;
        }
        updateBatchBar();
      };

      cb.onclick = (e) => {
        e.stopPropagation();
        toggleMark();
      };

      // Tapping folder opens it directly
      const itemInfo = card.querySelector('.fs-item-info');
      itemInfo.onclick = (e) => {
        if (e.target === cb) return;
        vibrate(15);
        browseFsDirectory(folder.path);
      };

      card.querySelector('[data-action="open-folder"]').onclick = (e) => {
        e.stopPropagation();
        vibrate(15);
        browseFsDirectory(folder.path);
      };

      card.querySelector('[data-action="locate-folder-pc"]').onclick = (e) => {
        e.stopPropagation();
        vibrate(15);
        openLocationOnPc(folder.path);
      };

      card.querySelector('[data-action="del-folder"]').onclick = (e) => {
        e.stopPropagation();
        if (confirm(`Delete folder "${folder.name}" and all its contents on PC?`)) {
          vibrate(25);
          fetch(`http://${state.serverHost}:${state.serverPort}/api/fs/delete?path=${encodeURIComponent(folder.path)}`, { method: 'POST' })
            .then(r => r.json())
            .then(() => {
              showToast('Folder deleted', 'warn', '🗑️');
              state.markedFsPaths.delete(folder.path);
              updateBatchBar();
              browseFsDirectory(state.currentFsPath);
            });
        }
      };

      el.fsBrowserItems.appendChild(card);
    });

    // Render Files
    filteredFiles.forEach(file => {
      const card = document.createElement('div');
      const isMarked = state.markedFsPaths.has(file.path);
      card.className = `fs-item-card is-file ${isMarked ? 'is-marked' : ''}`;
      const icon = getFileIcon(file.ext);

      card.innerHTML = `
        <div class="fs-item-info">
          <input type="checkbox" class="fs-item-checkbox" data-path="${file.path}" ${isMarked ? 'checked' : ''}>
          <span class="fs-icon-badge">${icon}</span>
          <div class="fs-item-details">
            <span class="fs-item-name" title="${file.name}">${file.name}</span>
            <span class="fs-item-meta">${file.size_formatted}${file.ext ? ' • ' + file.ext.toUpperCase() : ''}</span>
          </div>
        </div>
        <div class="fs-actions-row">
          <button class="fs-btn fs-btn-save" data-action="save" title="Download to phone">📥 Save</button>
          <button class="fs-btn fs-btn-open fs-btn-icon-only" data-action="open-pc" title="Open / Launch file on PC">🖥️</button>
          <button class="fs-btn fs-btn-locate fs-btn-icon-only" data-action="locate-pc" title="Show file in Windows File Explorer on PC">📂</button>
          <button class="fs-btn fs-btn-del fs-btn-icon-only" data-action="del" title="Delete on PC">🗑️</button>
        </div>
      `;

      const cb = card.querySelector('.fs-item-checkbox');
      const toggleMark = () => {
        vibrate(10);
        if (state.markedFsPaths.has(file.path)) {
          state.markedFsPaths.delete(file.path);
          card.classList.remove('is-marked');
          cb.checked = false;
        } else {
          state.markedFsPaths.add(file.path);
          card.classList.add('is-marked');
          cb.checked = true;
        }
        updateBatchBar();
      };

      cb.onclick = (e) => {
        e.stopPropagation();
        toggleMark();
      };

      // Tapping file row checks/unchecks without triggering download
      const fileInfo = card.querySelector('.fs-item-info');
      fileInfo.onclick = (e) => {
        if (e.target === cb) return;
        toggleMark();
      };

      // Explicit Download Action
      card.querySelector('[data-action="save"]').onclick = (e) => {
        e.stopPropagation();
        vibrate(15);
        downloadFileFromPC(file.path, file.name, file.size_formatted);
      };

      // Open on PC Action
      card.querySelector('[data-action="open-pc"]').onclick = (e) => {
        e.stopPropagation();
        vibrate(15);
        fetch(`http://${state.serverHost}:${state.serverPort}/api/fs/open?path=${encodeURIComponent(file.path)}`, { method: 'POST' })
          .then(r => r.json())
          .then(() => showToast(`Opened "${file.name}" on PC!`, 'success', '🖥️'))
          .catch(() => showToast('Could not open on PC', 'error', '❌'));
      };

      // Locate on PC Action (Reveal & Select in Explorer)
      card.querySelector('[data-action="locate-pc"]').onclick = (e) => {
        e.stopPropagation();
        vibrate(15);
        openLocationOnPc(file.path);
      };

      // Delete Action
      card.querySelector('[data-action="del"]').onclick = (e) => {
        e.stopPropagation();
        if (confirm(`Delete "${file.name}" on PC?`)) {
          vibrate(20);
          fetch(`http://${state.serverHost}:${state.serverPort}/api/fs/delete?path=${encodeURIComponent(file.path)}`, { method: 'POST' })
            .then(r => r.json())
            .then(() => {
              showToast('File deleted', 'warn', '🗑️');
              state.markedFsPaths.delete(file.path);
              updateBatchBar();
              browseFsDirectory(state.currentFsPath);
            });
        }
      };

      el.fsBrowserItems.appendChild(card);
    });
  }

  // --- Phone In-App File Explorer Logic ---
  function loadPhonePlaces() {
    const defaultPlaces = [
      { name: 'Received from PC', path: 'default', icon: '📥' },
      { name: 'Internal Storage', path: 'root', icon: '📱' },
      { name: 'Camera / DCIM', path: 'dcim', icon: '📸' },
      { name: 'Pictures', path: 'pictures', icon: '🖼️' },
      { name: 'Videos & Movies', path: 'movies', icon: '🎬' },
      { name: 'Downloads', path: 'downloads', icon: '⬇️' },
      { name: 'Documents', path: 'documents', icon: '📄' },
      { name: 'Music', path: 'music', icon: '🎵' },
    ];

    let places = defaultPlaces;
    if (window.AndroidApp && typeof window.AndroidApp.getPhonePlaces === 'function') {
      try {
        const pStr = window.AndroidApp.getPhonePlaces();
        const pArr = JSON.parse(pStr);
        if (Array.isArray(pArr) && pArr.length > 0) {
          places = pArr;
        }
      } catch (e) {}
    }

    if (el.phoneFsPlacesStrip) {
      el.phoneFsPlacesStrip.innerHTML = '';
      places.forEach(p => {
        const btn = document.createElement('button');
        btn.className = 'fs-place-chip phone-place-chip';
        const cur = state.phoneFs.currentPath || 'default';
        if (p.path === cur || (p.path === 'default' && cur === 'transfers')) {
          btn.classList.add('active');
        }
        btn.dataset.phonePath = p.path;
        btn.textContent = `${p.icon} ${p.name}`;
        btn.onclick = () => {
          vibrate(15);
          document.querySelectorAll('.phone-place-chip').forEach(c => c.classList.remove('active'));
          btn.classList.add('active');
          browsePhoneDirectory(p.path);
        };
        el.phoneFsPlacesStrip.appendChild(btn);
      });
    }

    const btnGrantStorage = document.getElementById('btn-grant-storage');
    if (btnGrantStorage && !btnGrantStorage.dataset.bound) {
      btnGrantStorage.dataset.bound = 'true';
      btnGrantStorage.onclick = () => {
        vibrate(20);
        if (window.AndroidApp && typeof window.AndroidApp.requestStoragePermission === 'function') {
          window.AndroidApp.requestStoragePermission();
        } else {
          showToast('Grant Full Storage access in Android App Settings', 'info', '📱');
        }
      };
    }
  }

  function updatePhoneBatchBar() {
    if (!el.phoneFsBatchBar) return;
    const count = state.phoneFs.markedPaths.size;
    if (count > 0) {
      el.phoneFsBatchBar.style.display = 'flex';
      if (el.phoneFsBatchCountLabel) el.phoneFsBatchCountLabel.textContent = `${count} marked`;
      if (el.phoneFsBatchSendLabel) el.phoneFsBatchSendLabel.textContent = `SEND TO PC (${count})`;
      const allPaths = [...state.phoneFs.folders.map(f => f.path), ...state.phoneFs.files.map(f => f.path)];
      const allSelected = allPaths.length > 0 && allPaths.every(p => state.phoneFs.markedPaths.has(p));
      if (el.phoneFsBatchSelectAll) el.phoneFsBatchSelectAll.checked = allSelected;
    } else {
      el.phoneFsBatchBar.style.display = 'none';
      if (el.phoneFsBatchSelectAll) el.phoneFsBatchSelectAll.checked = false;
      if (el.phoneFsBatchSendLabel) el.phoneFsBatchSendLabel.textContent = 'SEND TO PC';
    }
  }

  function browsePhoneDirectory(reqPath, highlightTarget = '') {
    state.phoneFs.currentPath = reqPath || 'default';
    try {
      localStorage.setItem('neontrack_last_phone_fs_path', state.phoneFs.currentPath);
    } catch (e) {}

    if (el.phoneFsBrowserItems) {
      el.phoneFsBrowserItems.innerHTML = `
        <div class="empty-files-placeholder">
          <span>📱</span>
          <p>Loading phone storage & files...</p>
        </div>
      `;
    }

    if (window.AndroidApp && typeof window.AndroidApp.listPhoneDirectory === 'function') {
      try {
        const jsonStr = window.AndroidApp.listPhoneDirectory(reqPath || 'default');
        const data = JSON.parse(jsonStr);
        if (data.status === 'ok') {
          state.phoneFs.currentPath = data.current_path;
          state.phoneFs.parentPath = data.parent_path || '';
          state.phoneFs.folders = data.folders || [];
          state.phoneFs.files = data.files || [];
          state.phoneFs.markedPaths.clear();

          try {
            localStorage.setItem('neontrack_last_phone_fs_path', data.current_path);
          } catch (e) {}

          if (el.phoneFsCurrentPath) {
            el.phoneFsCurrentPath.textContent = '📱 ' + (data.name || data.current_path);
            el.phoneFsCurrentPath.title = data.current_path;
          }
          if (el.btnPhoneFsUp) {
            el.btnPhoneFsUp.disabled = !data.parent_path;
          }

          // Check if storage permission banner needs to be shown
          const banner = document.getElementById('phone-fs-permission-banner');
          if (banner) {
            if (data.has_permission === false) {
              banner.style.display = 'flex';
            } else {
              banner.style.display = 'none';
            }
          }

          updatePhoneBatchBar();
          renderFilteredPhoneFsItems(highlightTarget);
          return;
        }
      } catch (e) {
        console.error('Error in listPhoneDirectory:', e);
      }
    }

    // Web Fallback (Simulated Phone Storage)
    state.phoneFs.parentPath = '';
    state.phoneFs.folders = [];
    state.phoneFs.files = [];
    if (el.phoneFsCurrentPath) el.phoneFsCurrentPath.textContent = '📱 Phone Storage / Downloads';
    if (el.btnPhoneFsUp) el.btnPhoneFsUp.disabled = true;
    updatePhoneBatchBar();
    renderFilteredPhoneFsItems(highlightTarget);
  }

  function renderFilteredPhoneFsItems(highlightTarget = '') {
    if (!el.phoneFsBrowserItems) return;
    el.phoneFsBrowserItems.innerHTML = '';

    const filter = (state.phoneFs.filterText || '').toLowerCase();
    const filteredFolders = state.phoneFs.folders.filter(f => f.name.toLowerCase().includes(filter));
    const filteredFiles = state.phoneFs.files.filter(f => f.name.toLowerCase().includes(filter));

    if (el.phoneFsItemCount) {
      const total = filteredFolders.length + filteredFiles.length;
      el.phoneFsItemCount.textContent = `${total} item${total === 1 ? '' : 's'}`;
    }

    if (filteredFolders.length === 0 && filteredFiles.length === 0) {
      el.phoneFsBrowserItems.innerHTML = `
        <div class="empty-files-placeholder">
          <span>📱</span>
          <p>${filter ? 'No matching phone files found' : 'This phone folder is empty'}</p>
          <button class="neo-btn btn-cyan" style="margin-top: 10px; height: 36px; font-size: 0.75rem;" onclick="if(document.getElementById('file-picker')) document.getElementById('file-picker').click()">
            📤 SELECT & SEND FILES TO PC
          </button>
        </div>
      `;
      return;
    }

    // Render Folders
    filteredFolders.forEach(folder => {
      const card = document.createElement('div');
      card.className = 'fs-item-card is-folder';
      const folderIcon = getFolderIcon(folder.name);
      card.innerHTML = `
        <div class="fs-item-info">
          <span class="fs-icon-badge">${folderIcon}</span>
          <div class="fs-item-details">
            <span class="fs-item-name" title="${folder.name}">${folder.name}</span>
            <span class="fs-item-meta">${folder.item_count} items</span>
          </div>
        </div>
        <div class="fs-actions-row">
          <button class="fs-btn fs-btn-open" data-action="open" title="Open Folder">📂 Open</button>
          <button class="fs-btn fs-btn-del" data-action="del" title="Delete Folder">🗑️</button>
        </div>
      `;

      card.querySelector('.fs-item-info').onclick = () => {
        vibrate(15);
        browsePhoneDirectory(folder.path);
      };

      card.querySelector('[data-action="open"]').onclick = (e) => {
        e.stopPropagation();
        vibrate(15);
        browsePhoneDirectory(folder.path);
      };

      card.querySelector('[data-action="del"]').onclick = (e) => {
        e.stopPropagation();
        if (confirm(`Delete folder "${folder.name}" on phone?`)) {
          vibrate(20);
          if (window.AndroidApp && typeof window.AndroidApp.deletePhoneFile === 'function') {
            window.AndroidApp.deletePhoneFile(folder.path);
            showToast('Folder deleted on phone', 'warn', '🗑️');
            browsePhoneDirectory(state.phoneFs.currentPath);
          }
        }
      };

      el.phoneFsBrowserItems.appendChild(card);
    });

    // Render Files
    filteredFiles.forEach(file => {
      const card = document.createElement('div');
      const isMarked = state.phoneFs.markedPaths.has(file.path);
      const isHighlight = highlightTarget && (file.name.toLowerCase() === highlightTarget.toLowerCase() || file.path.toLowerCase().endsWith(highlightTarget.toLowerCase()));

      card.className = `fs-item-card is-file ${isMarked ? 'is-marked' : ''} ${isHighlight ? 'is-highlighted' : ''}`;
      const icon = getFileIcon(file.ext);

      card.innerHTML = `
        <div class="fs-item-info">
          <input type="checkbox" class="fs-item-checkbox" data-path="${file.path}" ${isMarked ? 'checked' : ''}>
          <span class="fs-icon-badge">${icon}</span>
          <div class="fs-item-details">
            <span class="fs-item-name" title="${file.name}">${file.name}</span>
            <span class="fs-item-meta">${file.size_formatted}${file.ext ? ' • ' + file.ext.toUpperCase() : ''}</span>
          </div>
        </div>
        <div class="fs-actions-row">
          <button class="fs-btn fs-btn-save" data-action="send-pc" title="Upload directly to PC">📤 PC</button>
          <button class="fs-btn fs-btn-open" data-action="open-phone" title="View / Play on Phone">📱 Open</button>
          <button class="fs-btn fs-btn-del fs-btn-icon-only" data-action="del" title="Delete on Phone">🗑️</button>
        </div>
      `;

      const cb = card.querySelector('.fs-item-checkbox');
      const toggleMark = () => {
        vibrate(10);
        if (state.phoneFs.markedPaths.has(file.path)) {
          state.phoneFs.markedPaths.delete(file.path);
          card.classList.remove('is-marked');
          cb.checked = false;
        } else {
          state.phoneFs.markedPaths.add(file.path);
          card.classList.add('is-marked');
          cb.checked = true;
        }
        updatePhoneBatchBar();
      };

      cb.onclick = (e) => {
        e.stopPropagation();
        toggleMark();
      };

      card.querySelector('.fs-item-info').onclick = (e) => {
        if (e.target === cb) return;
        toggleMark();
      };

      // Direct Upload to PC
      card.querySelector('[data-action="send-pc"]').onclick = (e) => {
        e.stopPropagation();
        vibrate(15);
        if (window.AndroidApp && typeof window.AndroidApp.uploadPhoneFileToPc === 'function') {
          phoneUploadStartTime = Date.now();
          showTransferProgress({
            badge: '📤 UPLOADING TO PC',
            badgeClass: 'badge-upload',
            filename: file.name,
            percent: 0,
            status: 'Connecting to PC...',
            speed: '-- MB/s',
            isDownload: false
          });

          showToast(`Sending "${file.name}" to PC...`, 'info', '📤');
          window.AndroidApp.uploadPhoneFileToPc(file.path, state.currentFsPath || '', `http://${state.serverHost}:${state.serverPort}`);
        } else if (el.filePicker) {
          el.filePicker.accept = '*/*';
          el.filePicker.click();
        }
      };

      // Open on Phone
      card.querySelector('[data-action="open-phone"]').onclick = (e) => {
        e.stopPropagation();
        vibrate(15);
        if (window.AndroidApp && typeof window.AndroidApp.openPhoneFile === 'function') {
          window.AndroidApp.openPhoneFile(file.path);
        } else {
          showToast(`Opening ${file.name}`, 'info', '📱');
        }
      };

      // Delete on Phone
      card.querySelector('[data-action="del"]').onclick = (e) => {
        e.stopPropagation();
        if (confirm(`Delete "${file.name}" on phone?`)) {
          vibrate(20);
          if (window.AndroidApp && typeof window.AndroidApp.deletePhoneFile === 'function') {
            window.AndroidApp.deletePhoneFile(file.path);
            showToast('File deleted on phone', 'warn', '🗑️');
            state.phoneFs.markedPaths.delete(file.path);
            updatePhoneBatchBar();
            browsePhoneDirectory(state.phoneFs.currentPath);
          }
        }
      };

      el.phoneFsBrowserItems.appendChild(card);

      if (isHighlight) {
        setTimeout(() => {
          card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 150);
      }
    });
  }

  function revealInPhoneFiles(targetFolder = 'default', targetFileName = '') {
    vibrate(20);
    switchTab('tab-files');
    if (el.btnFsModePhone) {
      el.btnFsModePhone.click();
    }
    loadPhonePlaces();
    browsePhoneDirectory(targetFolder || 'default', targetFileName);
  }

  window.onStoragePermissionChanged = function() {
    loadPhonePlaces();
    browsePhoneDirectory(state.phoneFs.currentPath || 'default');
  };

  // --- Unified Transfer Progress Controller (Syncs PC & Phone Transfer Cards) ---
  let hideTransferTimeout = null;

  function showTransferProgress({
    badge = '📤 UPLOAD',
    badgeClass = 'badge-upload',
    filename = '',
    percent = 0,
    status = 'Transferring...',
    speed = '-- MB/s',
    showOpenPc = false,
    showOpenPhone = false,
    onOpenPc = null,
    onOpenPhone = null,
    isDownload = false
  }) {
    if (hideTransferTimeout) {
      clearTimeout(hideTransferTimeout);
      hideTransferTimeout = null;
    }
    const boxes = document.querySelectorAll('.file-transfer-card');
    const safePercent = Math.max(0, Math.min(100, Math.round(percent)));
    boxes.forEach(box => {
      box.style.display = 'flex';
      const badgeEl = box.querySelector('.transfer-badge');
      if (badgeEl) {
        badgeEl.textContent = badge;
        badgeEl.className = `transfer-badge ${badgeClass}`;
      }
      const filenameEl = box.querySelector('.transfer-filename');
      if (filenameEl && filename) filenameEl.textContent = filename;
      const percentEl = box.querySelector('.transfer-percent');
      if (percentEl) percentEl.textContent = `${safePercent}%`;
      const barEl = box.querySelector('.transfer-bar');
      if (barEl) {
        barEl.style.width = `${safePercent}%`;
        if (isDownload) barEl.classList.add('downloading');
        else barEl.classList.remove('downloading');
      }
      const statusEl = box.querySelector('.transfer-status');
      if (statusEl) statusEl.textContent = status;
      const speedEl = box.querySelector('.transfer-speed');
      if (speedEl) speedEl.textContent = speed;

      const btnOpenPc = box.querySelector('[data-transfer-action="open-pc"]') || box.querySelector('#btn-transfer-open-pc');
      if (btnOpenPc) {
        btnOpenPc.style.display = showOpenPc ? 'inline-flex' : 'none';
        if (onOpenPc) {
          btnOpenPc.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            onOpenPc();
            hideTransferProgress(1000);
          };
        }
      }

      const btnOpenPhone = box.querySelector('[data-transfer-action="open-phone"]') || box.querySelector('#btn-transfer-open-phone');
      if (btnOpenPhone) {
        btnOpenPhone.style.display = showOpenPhone ? 'inline-flex' : 'none';
        if (onOpenPhone) {
          btnOpenPhone.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            onOpenPhone();
            hideTransferProgress(1000);
          };
        }
      }

      const btnClose = box.querySelector('.transfer-close-btn') || box.querySelector('#btn-transfer-close');
      if (btnClose) {
        btnClose.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          hideTransferProgress(0);
        };
      }
    });
  }

  function hideTransferProgress(delay = 0) {
    if (hideTransferTimeout) {
      clearTimeout(hideTransferTimeout);
      hideTransferTimeout = null;
    }
    if (delay === 0) {
      const boxes = document.querySelectorAll('.file-transfer-card');
      boxes.forEach(box => { box.style.display = 'none'; });
    } else {
      hideTransferTimeout = setTimeout(() => {
        const boxes = document.querySelectorAll('.file-transfer-card');
        boxes.forEach(box => { box.style.display = 'none'; });
      }, delay);
    }
  }

  // --- Phone -> PC File Upload Handler & Batch Operations ---
  let phoneUploadStartTime = 0;
  let activeBatchTransfer = {
    active: false,
    total: 0,
    current: 0,
    successCount: 0,
    failCount: 0
  };

  window.onPhoneUploadProgress = function(percent, loaded, total, filename) {
    if (!phoneUploadStartTime) phoneUploadStartTime = Date.now();
    const isPro = typeof window.isProUnlocked === 'function' ? window.isProUnlocked() : false;
    const safePercent = Math.max(0, Math.min(100, Math.round(percent)));
    const loadedMB = (loaded / (1024 * 1024)).toFixed(1);
    const totalMB = total > 0 ? (total / (1024 * 1024)).toFixed(1) : '?';
    const duration = (Date.now() - phoneUploadStartTime) / 1000;
    const speedMB = duration > 0.2 ? (loaded / (1024 * 1024) / duration) : 0;
    const speedText = speedMB > 0 ? `${speedMB.toFixed(1)} MB/s` : '-- MB/s';

    let etaText = '';
    if (speedMB > 0.1 && total > loaded) {
      const remainingMB = (total - loaded) / (1024 * 1024);
      const etaSec = Math.ceil(remainingMB / speedMB);
      if (etaSec > 60) {
        etaText = ` • ETA: ${Math.floor(etaSec / 60)}m ${etaSec % 60}s`;
      } else {
        etaText = ` • ETA: ${etaSec}s`;
      }
    }

    const tierLabel = isPro ? 'PRO UNLIMITED' : 'STANDARD (10 MB/s)';
    const isBatch = activeBatchTransfer.active && activeBatchTransfer.total > 1;
    const remainingInQueue = isBatch ? (activeBatchTransfer.total - activeBatchTransfer.current) : 0;
    const queueNotice = remainingInQueue > 0 ? ` • ${remainingInQueue} in queue` : '';

    const badgeText = isBatch ? `📤 [${activeBatchTransfer.current}/${activeBatchTransfer.total}] ${tierLabel}` : `📤 ${tierLabel}`;
    const statusText = isBatch
      ? `[${activeBatchTransfer.current}/${activeBatchTransfer.total}] ${filename}: ${loadedMB}/${totalMB} MB (${safePercent}%)${etaText}${queueNotice}`
      : `Uploading ${loadedMB} MB of ${totalMB} MB (${safePercent}%)${etaText}`;

    showTransferProgress({
      badge: badgeText,
      badgeClass: 'badge-upload',
      filename: filename || 'Uploading...',
      percent: safePercent,
      status: statusText,
      speed: speedText,
      isDownload: false
    });
  };

  let onPhoneUploadQueueDone = null;

  window.onPhoneUploadComplete = function(filename, verified = true) {
    phoneUploadStartTime = 0;
    vibrate(20);

    const isBatch = activeBatchTransfer.active && activeBatchTransfer.total > 1;
    if (isBatch && activeBatchTransfer.current < activeBatchTransfer.total) {
      activeBatchTransfer.successCount++;
      showTransferProgress({
        badge: `✅ [${activeBatchTransfer.current}/${activeBatchTransfer.total}]`,
        badgeClass: 'badge-download',
        filename: filename,
        percent: 100,
        status: `Saved "${filename}" on PC. Preparing next file...`,
        speed: 'Saved to PC',
        isDownload: false
      });
    } else {
      const totalUploaded = isBatch ? activeBatchTransfer.total : 1;
      showToast(`"${filename}" uploaded to PC! ${verified ? '✅ Verified' : ''}`, 'success', '📤');
      showTransferProgress({
        badge: verified ? '✅ ALL SAVED' : '✅ UPLOADED',
        badgeClass: 'badge-download',
        filename: isBatch ? `${totalUploaded} file(s)` : filename,
        percent: 100,
        status: verified ? `✅ 100% Verified! Saved ${totalUploaded} file(s) intact on PC` : `Saved ${totalUploaded} file(s) on PC`,
        speed: 'Saved to PC',
        showOpenPc: true,
        onOpenPc: () => openLocationOnPc(state.currentFsPath),
        isDownload: false
      });
      hideTransferProgress(15000);
      activeBatchTransfer.active = false;
    }

    if (state.currentFsPath !== undefined) {
      browseFsDirectory(state.currentFsPath);
    }

    if (typeof onPhoneUploadQueueDone === 'function') {
      const cb = onPhoneUploadQueueDone;
      onPhoneUploadQueueDone = null;
      cb(true);
    }
  };

  window.onPhoneUploadError = function(filename, error) {
    phoneUploadStartTime = 0;
    showToast(`Upload error: ${error}`, 'error', '❌');
    const isBatch = activeBatchTransfer.active && activeBatchTransfer.total > 1;
    if (isBatch) activeBatchTransfer.failCount++;

    showTransferProgress({
      badge: '❌ ERROR',
      badgeClass: 'badge-upload',
      filename: filename,
      percent: 0,
      status: `Error: ${error}`,
      speed: 'Failed',
      isDownload: false
    });

    if (!isBatch || activeBatchTransfer.current >= activeBatchTransfer.total) {
      hideTransferProgress(8000);
      activeBatchTransfer.active = false;
    }

    if (typeof onPhoneUploadQueueDone === 'function') {
      const cb = onPhoneUploadQueueDone;
      onPhoneUploadQueueDone = null;
      cb(false);
    }
  };

  function uploadMarkedPhoneFilesToPc(paths) {
    if (!paths || paths.length === 0) return;
    if (window.AndroidApp && typeof window.AndroidApp.uploadPhoneFileToPc === 'function') {
      let currentIndex = 0;
      let errorOccurred = false;
      const totalCount = paths.length;
      const serverUrl = `http://${state.serverHost}:${state.serverPort}`;
      const destDir = ''; // Strictly route all uploads to PCDeck_Transfers on PC

      activeBatchTransfer = {
        active: true,
        total: totalCount,
        current: 0,
        successCount: 0,
        failCount: 0
      };

      function uploadNext() {
        if (currentIndex >= totalCount) {
          vibrate(30);
          activeBatchTransfer.active = false;
          const anySuccess = activeBatchTransfer.successCount > 0;
          if (!anySuccess) {
            showToast(`Upload failed. Check storage access.`, 'error', '❌');
            showTransferProgress({
              badge: '❌ UPLOAD FAILED',
              badgeClass: 'badge-upload',
              filename: `${totalCount} file(s)`,
              percent: 0,
              status: 'Upload failed or access denied',
              speed: 'Failed',
              isDownload: false
            });
            hideTransferProgress(8000);
          } else if (errorOccurred) {
            showToast(`Uploaded with some errors (${activeBatchTransfer.successCount}/${totalCount})`, 'warn', '⚠️');
            showTransferProgress({
              badge: '⚠️ PARTIAL SUCCESS',
              badgeClass: 'badge-download',
              filename: `${activeBatchTransfer.successCount}/${totalCount} file(s)`,
              percent: 100,
              status: `Saved ${activeBatchTransfer.successCount} of ${totalCount} files to PCDeck_Transfers`,
              speed: 'Saved to PC',
              showOpenPc: true,
              onOpenPc: () => openLocationOnPc(''),
              isDownload: false
            });
            hideTransferProgress(15000);
          } else {
            showToast(`✅ Uploaded ${totalCount} file(s) to PC!`, 'success', '🎉');
            showTransferProgress({
              badge: '✅ ALL UPLOADED',
              badgeClass: 'badge-download',
              filename: `${totalCount} file(s)`,
              percent: 100,
              status: '✅ All Transfers Complete & Verified in PCDeck_Transfers',
              speed: 'Saved to PC',
              showOpenPc: true,
              onOpenPc: () => openLocationOnPc(''),
              isDownload: false
            });
            hideTransferProgress(15000);
          }

          state.phoneFs.markedPaths.clear();
          updatePhoneBatchBar();
          renderFilteredPhoneFsItems();
          browseFsDirectory(state.currentFsPath);
          return;
        }

        const path = paths[currentIndex];
        const filename = path.split('/').pop().split('\\').pop();
        currentIndex++;
        activeBatchTransfer.current = currentIndex;
        phoneUploadStartTime = Date.now();
        let lastActivityTime = Date.now();

        showTransferProgress({
          badge: `📤 [${currentIndex}/${totalCount}]`,
          badgeClass: 'badge-upload',
          filename: filename,
          percent: 0,
          status: `[${currentIndex}/${totalCount}] Starting ${filename}...`,
          speed: '-- MB/s',
          isDownload: false
        });

        let completed = false;
        // Watchdog: only timeout if ZERO bytes / progress events occurred for 180 consecutive seconds
        const watchdog = setInterval(() => {
          if (Date.now() - lastActivityTime > 180000) {
            console.warn(`Upload stalled on ${filename}, advancing queue`);
            showToast(`Stalled transfer on ${filename}`, 'warn', '⚠️');
            onDoneOnce(false);
          }
        }, 15000);

        const onDoneOnce = (success = true) => {
          if (completed) return;
          completed = true;
          clearInterval(watchdog);
          if (!success) errorOccurred = true;
          setTimeout(uploadNext, 200);
        };

        const originalProgress = window.onPhoneUploadProgress;
        window.onPhoneUploadProgress = function(percent, loaded, total, fname) {
          lastActivityTime = Date.now();
          if (typeof originalProgress === 'function') {
            originalProgress(percent, loaded, total, fname);
          }
        };

        onPhoneUploadQueueDone = (success) => {
          onDoneOnce(success);
        };

        window.AndroidApp.uploadPhoneFileToPc(path, destDir, serverUrl);
      }

      uploadNext();
    } else {
      if (el.filePicker) el.filePicker.click();
    }
  }

  // --- Sequential Queue Download (Strict 1-by-1 FIFO Queue, NO ZIP) ---
  let nativeDownloadStartTime = 0;
  let onNativeDownloadDoneCallback = null;
  let activeDownloadBatch = {
    active: false,
    total: 0,
    current: 0,
    successCount: 0
  };

  window.onNativeDownloadProgress = function(percent, loaded, total) {
    if (!nativeDownloadStartTime) nativeDownloadStartTime = Date.now();
    const isPro = typeof window.isProUnlocked === 'function' ? window.isProUnlocked() : false;
    const safePercent = Math.max(0, Math.min(100, Math.round(percent)));
    const loadedMB = (loaded / (1024 * 1024)).toFixed(1);
    const totalMB = total > 0 ? (total / (1024 * 1024)).toFixed(1) : '?';
    const duration = (Date.now() - nativeDownloadStartTime) / 1000;
    const speedMB = duration > 0.2 ? (loaded / (1024 * 1024) / duration) : 0;
    const speedText = speedMB > 0 ? `${speedMB.toFixed(1)} MB/s` : '-- MB/s';

    let etaText = '';
    if (speedMB > 0.1 && total > loaded) {
      const remainingMB = (total - loaded) / (1024 * 1024);
      const etaSec = Math.ceil(remainingMB / speedMB);
      if (etaSec > 60) {
        etaText = ` • ETA: ${Math.floor(etaSec / 60)}m ${etaSec % 60}s`;
      } else {
        etaText = ` • ETA: ${etaSec}s`;
      }
    }

    const tierLabel = isPro ? 'PRO UNLIMITED' : 'STANDARD (10 MB/s)';
    const isBatch = activeDownloadBatch.active && activeDownloadBatch.total > 1;
    const remainingInQueue = isBatch ? (activeDownloadBatch.total - activeDownloadBatch.current) : 0;
    const queueNotice = remainingInQueue > 0 ? ` • ${remainingInQueue} in queue` : '';

    const badgeText = isBatch ? `📥 [${activeDownloadBatch.current}/${activeDownloadBatch.total}] ${tierLabel}` : `📥 ${tierLabel}`;
    const statusText = isBatch
      ? `[${activeDownloadBatch.current}/${activeDownloadBatch.total}] Downloading ${loadedMB} MB of ${totalMB} MB (${safePercent}%)${etaText}${queueNotice}`
      : `Downloading ${loadedMB} MB of ${totalMB} MB (${safePercent}%)${etaText}`;

    showTransferProgress({
      badge: badgeText,
      badgeClass: 'badge-download',
      percent: safePercent,
      status: statusText,
      speed: speedText,
      isDownload: true
    });
  };

  window.onNativeDownloadComplete = function(fileName, verified = true) {
    vibrate(25);
    nativeDownloadStartTime = 0;
    const isBatch = activeDownloadBatch.active && activeDownloadBatch.total > 1;

    if (isBatch && activeDownloadBatch.current < activeDownloadBatch.total) {
      activeDownloadBatch.successCount++;
      showTransferProgress({
        badge: `✅ [${activeDownloadBatch.current}/${activeDownloadBatch.total}]`,
        badgeClass: 'badge-download',
        filename: fileName,
        percent: 100,
        status: `Saved "${fileName}" to Downloads/PCDeck. Next in queue starting...`,
        speed: 'Saved to Phone',
        isDownload: true
      });
    } else {
      const totalCount = isBatch ? activeDownloadBatch.total : 1;
      showTransferProgress({
        badge: verified ? '✅ ALL SAVED' : '✅ DOWNLOADED',
        badgeClass: 'badge-download',
        filename: isBatch ? `${totalCount} file(s)` : fileName,
        percent: 100,
        status: verified ? `✅ 100% Verified! Saved ${totalCount} file(s) in Downloads/PCDeck` : `Saved ${totalCount} file(s) in Downloads/PCDeck`,
        speed: 'Saved to Phone',
        showOpenPhone: true,
        onOpenPhone: () => {
          revealInPhoneFiles('default', fileName);
          showToast(`Locating "${fileName}" in Phone Files`, 'success', '📱');
        },
        isDownload: true
      });

      hideTransferProgress(15000);
      activeDownloadBatch.active = false;
    }

    if (typeof onNativeDownloadDoneCallback === 'function') {
      const cb = onNativeDownloadDoneCallback;
      onNativeDownloadDoneCallback = null;
      cb();
    }
  };

  window.onNativeDownloadError = function(errMsg) {
    nativeDownloadStartTime = 0;
    showToast('Download error: ' + errMsg, 'error', '❌');
    const isBatch = activeDownloadBatch.active && activeDownloadBatch.total > 1;

    showTransferProgress({
      badge: '❌ ERROR',
      badgeClass: 'badge-upload',
      filename: 'Download Failed',
      percent: 0,
      status: '❌ ' + (errMsg || 'Network / Storage Error'),
      speed: 'Failed',
      isDownload: true
    });

    if (!isBatch || activeDownloadBatch.current >= activeDownloadBatch.total) {
      hideTransferProgress(8000);
      activeDownloadBatch.active = false;
    }

    if (typeof onNativeDownloadDoneCallback === 'function') {
      const cb = onNativeDownloadDoneCallback;
      onNativeDownloadDoneCallback = null;
      cb();
    }
  };

  function downloadSingleFileWithProgress(filePath, fileName, fileSizeFormatted, fileIndex, totalFiles, onDone) {
    const isBatch = totalFiles > 1;
    showTransferProgress({
      badge: isBatch ? `📥 [${fileIndex}/${totalFiles}]` : '📥 DOWNLOADING',
      badgeClass: 'badge-download',
      filename: fileName,
      percent: 0,
      status: isBatch ? `[${fileIndex}/${totalFiles}] Starting "${fileName}" (${fileSizeFormatted || ''})...` : `Starting "${fileName}" (${fileSizeFormatted || ''})...`,
      speed: '-- MB/s',
      isDownload: true
    });

    const downloadUrl = `http://${state.serverHost}:${state.serverPort}/api/fs/download?path=${encodeURIComponent(filePath)}`;

    // If running in Android App, use Native MediaStore Downloader directly into Downloads/PCDeck/
    if (window.AndroidApp && typeof window.AndroidApp.saveFileToDownloads === 'function') {
      nativeDownloadStartTime = Date.now();
      onNativeDownloadDoneCallback = onDone;
      window.AndroidApp.saveFileToDownloads(downloadUrl, fileName);
      return;
    }

    // Direct Browser Download Stream (bypasses RAM Blob limit to allow 5GB+ downloads)
    try {
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = downloadUrl;
      a.setAttribute('download', fileName);
      a.setAttribute('target', '_blank');
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        if (a.parentNode) document.body.removeChild(a);
      }, 2000);

      showTransferProgress({
        badge: '✅ DOWNLOADING',
        badgeClass: 'badge-download',
        filename: fileName,
        percent: 100,
        status: `Browser downloading "${fileName}"...`,
        speed: 'Streaming',
        showOpenPhone: false,
        isDownload: true
      });
      hideTransferProgress(8000);
      if (onDone) onDone();
    } catch (err) {
      window.open(downloadUrl, '_blank');
      if (onDone) onDone();
    }
  }

  function downloadMarkedFilesSequentially(paths) {
    if (!paths || paths.length === 0) return;
    if (activeDownloadBatch.active) {
      showToast(`Download queue active (${activeDownloadBatch.total - activeDownloadBatch.current + 1} remaining)`, 'info');
      return;
    }

    const norm = p => (p || '').replace(/[\/\\]+/g, '/').toLowerCase();
    const markedSet = new Set(paths.map(norm));
    const fileItems = state.fsFiles.filter(f => markedSet.has(norm(f.path)));
    if (fileItems.length === 0) {
      showToast('No downloadable files marked (select individual files to save)', 'warn', '⚠️');
      return;
    }

    let currentIndex = 0;
    const total = fileItems.length;
    activeDownloadBatch = {
      active: true,
      total: total,
      current: 0,
      successCount: 0
    };

    showToast(`Queued ${total} files for sequential download...`, 'success', '📥');

    function downloadNext() {
      if (currentIndex >= total) {
        vibrate(30);
        activeDownloadBatch.active = false;
        showToast(`Saved ${total} file(s) to Downloads/PCDeck!`, 'success');
        if (el.btnTransferOpenPhone) {
          el.btnTransferOpenPhone.textContent = 'SHOW IN PHONE FILES';
          el.btnTransferOpenPhone.style.display = 'inline-flex';
          el.btnTransferOpenPhone.onclick = () => {
            revealInPhoneFiles('default');
          };
        }
        state.markedFsPaths.clear();
        updateBatchBar();
        renderFilteredFsItems();
        return;
      }

      const file = fileItems[currentIndex];
      currentIndex++;
      activeDownloadBatch.current = currentIndex;

      let completed = false;
      let lastActivityTime = Date.now();

      // Watchdog: only timeout if ZERO bytes occurred for 180 consecutive seconds
      const watchdog = setInterval(() => {
        if (Date.now() - lastActivityTime > 180000) {
          console.warn(`Download stalled on ${file.name}, advancing queue`);
          showToast(`Stalled download on ${file.name}`, 'warn', '⚠️');
          onDoneOnce();
        }
      }, 15000);

      const onDoneOnce = () => {
        if (completed) return;
        completed = true;
        clearInterval(watchdog);
        setTimeout(downloadNext, 300);
      };

      const origNativeProgress = window.onNativeDownloadProgress;
      window.onNativeDownloadProgress = function(percent, loaded, totalBytes) {
        lastActivityTime = Date.now();
        if (typeof origNativeProgress === 'function') {
          origNativeProgress(percent, loaded, totalBytes);
        }
      };

      downloadSingleFileWithProgress(file.path, file.name, file.size_formatted, currentIndex, total, onDoneOnce);
    }
    downloadNext();
  }

  function downloadFileFromPC(filePath, fileName, fileSizeFormatted) {
    if (!filePath) return;
    vibrate(15);
    downloadSingleFileWithProgress(filePath, fileName, fileSizeFormatted, 1, 1, () => {
      showToast(`Saved "${fileName}" to Downloads!`, 'success', '🎉');
      if (el.btnTransferOpenPhone) {
        el.btnTransferOpenPhone.textContent = '📂 SHOW IN PHONE FILES';
        el.btnTransferOpenPhone.style.display = 'inline-flex';
        el.btnTransferOpenPhone.onclick = () => {
          revealInPhoneFiles('default', fileName);
        };
      }
    });
  }

  function openLocationOnPc(targetPath) {
    vibrate(25);
    const target = targetPath || state.currentFsPath || '';
    fetch(`http://${state.serverHost}:${state.serverPort}/api/fs/open-location`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: target })
    })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'ok') {
        showToast('Opened in Windows Explorer on PC 📂', 'success', '💻');
      } else {
        showToast(`PC Error: ${data.error || 'Failed to open'}`, 'error', '⚠️');
      }
    })
    .catch(() => {
      showToast('Could not reach PC to open folder', 'error', '🔌');
    });
  }

  function uploadFilesToCurrentDir(fileList) {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);
    let currentIndex = 0;
    let errorOccurred = false;

    function uploadNext() {
      if (currentIndex >= files.length) {
        vibrate(30);
        if (errorOccurred) {
          showToast(`Completed upload with some errors`, 'warn', '⚠️');
        } else {
          showToast(`Uploaded ${files.length} file(s) to PC!`, 'success', '🎉');
        }
        showTransferProgress({
          badge: errorOccurred ? '⚠️ COMPLETED' : '✅ ALL UPLOADED',
          badgeClass: 'badge-download',
          filename: `${files.length} file(s)`,
          percent: 100,
          status: errorOccurred ? 'Completed with warnings/errors' : '✅ All Transfers Complete! Saved on PC',
          speed: 'Saved to PC',
          showOpenPc: true,
          onOpenPc: () => openLocationOnPc(state.currentFsPath),
          isDownload: false
        });
        hideTransferProgress(15000);
        // Refresh directory listing immediately so new files show up in file browser!
        browseFsDirectory(state.currentFsPath);
        return;
      }

      const file = files[currentIndex];
      currentIndex++;
      const startTime = Date.now();
      let lastProgressTime = Date.now();

      showTransferProgress({
        badge: `📤 ${currentIndex}/${files.length}`,
        badgeClass: 'badge-upload',
        filename: file.name,
        percent: 0,
        status: `Sending ${currentIndex} of ${files.length}...`,
        speed: '-- MB/s',
        isDownload: false
      });

      const uploadUrl = `http://${state.serverHost}:${state.serverPort}/api/fs/upload-stream?filename=${encodeURIComponent(file.name)}&dest_dir=${encodeURIComponent(state.currentFsPath || '')}`;
      const xhr = new XMLHttpRequest();
      xhr.open('POST', uploadUrl, true);
      xhr.setRequestHeader('Content-Type', 'application/octet-stream');
      xhr.setRequestHeader('X-File-Name', encodeURIComponent(file.name));
      xhr.setRequestHeader('X-Dest-Dir', encodeURIComponent(state.currentFsPath || ''));
      xhr.timeout = 0; // 0 = Infinite timeout for large multi-gigabyte files

      let done = false;
      const watchdog = setInterval(() => {
        if (Date.now() - lastProgressTime > 60000) {
          clearInterval(watchdog);
          if (!done) {
            done = true;
            errorOccurred = true;
            showToast(`Upload stalled on "${file.name}"`, 'warn', '⚠️');
            xhr.abort();
            uploadNext();
          }
        }
      }, 10000);

      const finishUpload = (success) => {
        if (done) return;
        done = true;
        clearInterval(watchdog);
        if (!success) errorOccurred = true;
        uploadNext();
      };

      xhr.upload.onprogress = (e) => {
        lastProgressTime = Date.now();
        if (e.lengthComputable && e.total > 0) {
          const percent = Math.min(100, Math.round((e.loaded / e.total) * 100));
          const loadedMB = (e.loaded / (1024 * 1024)).toFixed(1);
          const totalMB = (e.total / (1024 * 1024)).toFixed(1);
          const duration = (Date.now() - startTime) / 1000;
          const speedMB = duration > 0.1 ? (e.loaded / (1024 * 1024) / duration).toFixed(1) : '--';
          showTransferProgress({
            badge: `📤 ${currentIndex}/${files.length}`,
            badgeClass: 'badge-upload',
            filename: file.name,
            percent: percent,
            status: `Uploading ${loadedMB} MB of ${totalMB} MB (${percent}%)`,
            speed: `${speedMB} MB/s`,
            isDownload: false
          });
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          finishUpload(true);
        } else {
          showToast(`Error uploading "${file.name}" (HTTP ${xhr.status})`, 'error', '❌');
          finishUpload(false);
        }
      };

      xhr.onerror = () => {
        showToast(`Network error uploading "${file.name}"`, 'error', '❌');
        finishUpload(false);
      };

      xhr.send(file);
    }

    uploadNext();
  }

  // --- Quick Tools Drawer Sheet ---
  function updateQuickToolsUi() {
    // 1. Touch Mode (Direct Touch vs Virtual Cursor)
    if (el.toolTouchMode) {
      const isTouch = state.screenMode === 'touch';
      const isMouse = state.screenMode === 'mouse';
      const isRclick = state.screenMode === 'rclick';

      el.toolTouchMode.classList.remove('active-cyan', 'active-purple', 'active-pink');
      if (isTouch) {
        el.toolTouchMode.classList.add('active-cyan');
        if (el.toolTouchStatus) el.toolTouchStatus.textContent = '● Direct Tap Active';
      } else if (isMouse) {
        el.toolTouchMode.classList.add('active-purple');
        if (el.toolTouchStatus) el.toolTouchStatus.textContent = '● Virtual Cursor Active';
      } else if (isRclick) {
        el.toolTouchMode.classList.add('active-pink');
        if (el.toolTouchStatus) el.toolTouchStatus.textContent = '● Next Tap: Right-Click!';
      }
    }

    // 2. Right Click
    if (el.toolRclick) {
      const isRclickArmed = state.screenMode === 'rclick';
      el.toolRclick.classList.toggle('active-pink', isRclickArmed);
      if (el.toolRclickStatus) {
        el.toolRclickStatus.textContent = isRclickArmed ? '● Armed: Next Tap Right-Click!' : 'Instant / Next Tap';
      }
    }

    // 3. Zoom Reset
    if (el.toolZoomReset) {
      const isZoomed = Math.abs(state.zoomScale - 1.0) > 0.05;
      el.toolZoomReset.classList.toggle('active-yellow', isZoomed);
      const sub = el.toolZoomReset.querySelector('.tool-tile-sub');
      if (sub) {
        sub.textContent = isZoomed ? `● ${Math.round(state.zoomScale * 100)}% (Tap to 100%)` : 'Fit to Screen (100%)';
      }
    }

    // 4. Keep Awake
    if (el.toolWakelock) {
      el.toolWakelock.classList.toggle('active-yellow', state.wakelockEnabled);
      if (el.toolWakelockStatus) {
        el.toolWakelockStatus.textContent = state.wakelockEnabled ? '● Enabled (Screen Awake)' : 'Disabled';
      }
    }

    // 5. Fullscreen
    if (el.toolFullscreen) {
      const isFull = !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
      el.toolFullscreen.classList.toggle('active-lime', isFull);
      const sub = el.toolFullscreen.querySelector('.tool-tile-sub');
      if (sub) {
        sub.textContent = isFull ? '● Fullscreen (Tap to Exit)' : 'Immersive View';
      }
    }

    // 6. Screen Orientation
    if (el.toolRotate) {
      const isPortrait = window.innerHeight > window.innerWidth;
      const sub = el.toolRotate.querySelector('.tool-tile-sub');
      if (sub) {
        sub.textContent = isPortrait ? 'Portrait (Tap for Landscape)' : 'Landscape (Tap for Portrait)';
      }
    }
  }

  function initQuickTools() {
    function toggleQuickTools(show) {
      if (!el.quickToolsModal) return;
      if (show === undefined) {
        el.quickToolsModal.classList.toggle('show');
      } else {
        el.quickToolsModal.classList.toggle('show', show);
      }
      if (el.quickToolsModal.classList.contains('show')) {
        vibrate(20);
        updateQuickToolsUi();
      }
    }

    if (el.btnQuickToolsToggle) {
      el.btnQuickToolsToggle.onclick = (e) => {
        e.stopPropagation();
        toggleQuickTools();
      };
    }

    if (el.btnCloseTools) {
      el.btnCloseTools.onclick = (e) => {
        e.stopPropagation();
        toggleQuickTools(false);
      };
    }

    if (el.quickToolsModal) {
      el.quickToolsModal.onclick = (e) => {
        if (e.target === el.quickToolsModal) toggleQuickTools(false);
      };
    }

    if (el.toolRotate) {
      el.toolRotate.onclick = (e) => {
        e.stopPropagation();
        toggleScreenOrientation();
        updateQuickToolsUi();
        toggleQuickTools(false);
      };
    }

    if (el.toolTouchMode) {
      el.toolTouchMode.onclick = (e) => {
        e.stopPropagation();
        vibrate(20);
        state.screenMode = state.screenMode === 'touch' ? 'mouse' : 'touch';
        updateQuickToolsUi();
        showToast(
          state.screenMode === 'touch'
            ? 'Direct Touch: Tap screen to click directly'
            : 'Virtual Cursor: Glide finger to glide mouse',
          'success',
          state.screenMode === 'touch' ? '👆' : '🖱️'
        );
        toggleQuickTools(false);
      };
    }

    if (el.toolRclick) {
      el.toolRclick.onclick = (e) => {
        e.stopPropagation();
        vibrate(25);
        // 1. Send immediate Right Click to PC
        sendCommand('c,right');
        // 2. Also arm screen canvas for next tap
        state.screenMode = 'rclick';
        updateQuickToolsUi();
        showToast('Right-Click Sent & Armed for next tap 🖱️', 'success', '🖱️');
        toggleQuickTools(false);
      };
    }

    if (el.toolZoomReset) {
      el.toolZoomReset.onclick = (e) => {
        e.stopPropagation();
        vibrate(18);
        resetPinchZoom();
        updateQuickToolsUi();
        toggleQuickTools(false);
      };
    }

    if (el.toolWakelock) {
      el.toolWakelock.onclick = (e) => {
        e.stopPropagation();
        state.wakelockEnabled = !state.wakelockEnabled;
        if (state.wakelockEnabled) {
          requestWakeLock();
          showToast('Keep Awake Enabled', 'success', '💡');
        } else {
          releaseWakeLock();
          showToast('Keep Awake Disabled', 'warn', '💤');
        }
        updateQuickToolsUi();
        saveAllSettings(false);
        toggleQuickTools(false);
      };
    }

    if (el.toolFullscreen) {
      el.toolFullscreen.onclick = (e) => {
        e.stopPropagation();
        vibrate(20);
        toggleQuickTools(false);

        if (window.AndroidApp && typeof window.AndroidApp.requestFullscreen === 'function') {
          window.AndroidApp.requestFullscreen();
          showToast('Fullscreen Mode (App)', 'success', '📺');
          setTimeout(updateQuickToolsUi, 100);
          return;
        }

        const isFull = !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
        if (!isFull) {
          const docEl = document.documentElement;
          const req = docEl.requestFullscreen || docEl.webkitRequestFullscreen || docEl.mozRequestFullScreen || docEl.msRequestFullscreen;
          if (req) {
            req.call(docEl).then(() => {
              showToast('Fullscreen Mode Enabled', 'success', '📺');
              updateQuickToolsUi();
            }).catch(() => {
              showToast('Fullscreen mode active', 'info', '📺');
            });
          } else {
            showToast('Fullscreen not supported in this browser', 'warn', '📺');
          }
        } else {
          const exit = document.exitFullscreen || document.webkitExitFullscreen || document.mozCancelFullScreen || document.msExitFullscreen;
          if (exit) {
            exit.call(document).then(() => {
              showToast('Fullscreen Exited', 'info', '📺');
              updateQuickToolsUi();
            }).catch(() => {});
          }
        }
      };
    }

  }

  function toggleTitleBar(forceHide) {
    vibrate(18);
    const shouldHide = forceHide !== undefined ? forceHide : !state.titleBarHidden;
    state.titleBarHidden = shouldHide;

    if (el.topNav) {
      if (shouldHide) {
        el.topNav.classList.add('hidden-bar');
      } else {
        el.topNav.classList.remove('hidden-bar');
      }
    }

    if (el.btnUnhideTitlebar) {
      el.btnUnhideTitlebar.style.display = shouldHide ? 'inline-flex' : 'none';
    }

    updateQuickToolsUi();

    showToast(shouldHide ? 'Title Bar Hidden (Gaming Mode)' : 'Title Bar Restored', 'success', shouldHide ? '📺' : '👁️');
    try {
      localStorage.setItem('neontrack_titlebar_hidden', shouldHide.toString());
    } catch (e) {}
  }

  function toggleScreenOrientation() {
    vibrate(20);
    if (window.AndroidApp && typeof window.AndroidApp.toggleOrientation === 'function') {
      window.AndroidApp.toggleOrientation();
      showToast('Screen Orientation Toggled', 'success', '🔄');
      return;
    }
    try {
      if (screen.orientation && screen.orientation.lock) {
        const isPortrait = window.innerHeight > window.innerWidth;
        const target = isPortrait ? 'landscape' : 'portrait';
        screen.orientation.lock(target).then(() => {
          showToast(`Screen locked to ${target}`, 'success', '🔄');
        }).catch(() => {
          showToast(`Rotate device ${target} physically`, 'warn', '🔄');
        });
      } else {
        showToast('Rotate your device physically', 'warn', '🔄');
      }
    } catch (e) {
      showToast('Rotate your device physically', 'warn', '🔄');
    }
  }

  window.onScreenOrientationChange = function(orientation) {
    if (window.AndroidApp && typeof window.AndroidApp.setImmersiveFullscreen === 'function') {
      window.AndroidApp.setImmersiveFullscreen(true);
    }
  };

  // --- High-Performance Multi-Engine QR Scanner ---
  let nativeBarcodeDetector = null;
  if ('BarcodeDetector' in window) {
    try {
      nativeBarcodeDetector = new BarcodeDetector({ formats: ['qr_code'] });
    } catch (e) {
      nativeBarcodeDetector = null;
    }
  }

  function startQrScanner() {
    if (!el.qrScannerModal || !el.qrVideo) return;
    el.qrScannerModal.classList.add('show');
    vibrate(25);

    const constraints = {
      video: {
        facingMode: state.currentFacingMode,
        width: { ideal: 1280, max: 1920 },
        height: { ideal: 720, max: 1080 }
      },
      audio: false
    };

    navigator.mediaDevices.getUserMedia(constraints).then((stream) => {
      state.qrStream = stream;
      el.qrVideo.srcObject = stream;
      el.qrVideo.setAttribute('playsinline', 'true');
      el.qrVideo.play().then(() => {
        qrScanAnimationId = requestAnimationFrame(scanQrFrame);
      }).catch(() => {
        qrScanAnimationId = requestAnimationFrame(scanQrFrame);
      });
    }).catch((err) => {
      console.warn('Camera 720p constraints failed, trying default stream:', err);
      navigator.mediaDevices.getUserMedia({ video: { facingMode: state.currentFacingMode } }).then((stream) => {
        state.qrStream = stream;
        el.qrVideo.srcObject = stream;
        el.qrVideo.setAttribute('playsinline', 'true');
        el.qrVideo.play();
        qrScanAnimationId = requestAnimationFrame(scanQrFrame);
      }).catch((e2) => {
        console.error('Camera access error:', e2);
        showToast('Camera permission required to scan QR', 'error', '📷');
        stopQrScanner();
      });
    });
  }

  function stopQrScanner() {
    if (qrScanAnimationId) {
      cancelAnimationFrame(qrScanAnimationId);
      qrScanAnimationId = null;
    }
    if (state.qrStream) {
      state.qrStream.getTracks().forEach(t => t.stop());
      state.qrStream = null;
    }
    state.torchActive = false;
    if (el.btnToggleTorch) el.btnToggleTorch.textContent = '💡 Flashlight';
    if (el.qrScannerModal) el.qrScannerModal.classList.remove('show');
  }

  let isScanningBusy = false;

  async function scanQrFrame() {
    if (!el.qrVideo || el.qrVideo.readyState < 2 || isScanningBusy) {
      qrScanAnimationId = requestAnimationFrame(scanQrFrame);
      return;
    }

    // Engine 1: Native Hardware BarcodeDetector (Android Chrome / Modern WebView)
    if (nativeBarcodeDetector) {
      try {
        isScanningBusy = true;
        const barcodes = await nativeBarcodeDetector.detect(el.qrVideo);
        if (barcodes && barcodes.length > 0) {
          const raw = barcodes[0].rawValue;
          if (raw) {
            vibrate(60);
            stopQrScanner();
            parseQrAndConnect(raw);
            isScanningBusy = false;
            return;
          }
        }
      } catch (e) {
        // Fallback to jsQR
      } finally {
        isScanningBusy = false;
      }
    }

    // Engine 2: Ultra-Fast Downscaled jsQR with dual-inversion and center crop
    try {
      const videoW = el.qrVideo.videoWidth;
      const videoH = el.qrVideo.videoHeight;
      if (videoW > 0 && videoH > 0 && window.jsQR) {
        const canvas = el.qrCanvas || document.createElement('canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });

        // Optimal downscale to 480px width for instant ~4ms frame processing
        const targetW = 480;
        const targetH = Math.round((videoH * targetW) / videoW);
        canvas.width = targetW;
        canvas.height = targetH;
        ctx.drawImage(el.qrVideo, 0, 0, targetW, targetH);

        const imgData = ctx.getImageData(0, 0, targetW, targetH);
        let code = window.jsQR(imgData.data, targetW, targetH, {
          inversionAttempts: 'attemptBoth',
        });

        if (!code) {
          // Center 60% Crop Zoom Pass (where the reticle is aiming)
          const cropW = Math.round(videoW * 0.6);
          const cropH = Math.round(videoH * 0.6);
          const cropX = Math.round((videoW - cropW) / 2);
          const cropY = Math.round((videoH - cropH) / 2);
          canvas.width = 360;
          canvas.height = 360;
          ctx.drawImage(el.qrVideo, cropX, cropY, cropW, cropH, 0, 0, 360, 360);
          const cropImgData = ctx.getImageData(0, 0, 360, 360);
          code = window.jsQR(cropImgData.data, 360, 360, {
            inversionAttempts: 'attemptBoth',
          });
        }

        if (code && code.data) {
          vibrate(60);
          stopQrScanner();
          parseQrAndConnect(code.data);
          return;
        }
      }
    } catch (e) {
      console.warn('QR decode error:', e);
    }

    qrScanAnimationId = requestAnimationFrame(scanQrFrame);
  }

  function parseQrAndConnect(data) {
    vibrate(60);
    try {
      const url = new URL(data);
      const ipParam = url.searchParams.get('ip');
      if (ipParam) {
        const clean = ipParam.replace(/^https?:\/\//, '');
        const parts = clean.split(':');
        state.serverHost = parts[0];
        state.serverPort = parts[1] || '8000';
      } else {
        state.serverHost = url.hostname;
        state.serverPort = url.port || '8000';
      }
      if (el.modalIpInput) el.modalIpInput.value = `${state.serverHost}:${state.serverPort}`;
      if (el.settingsIpInput) el.settingsIpInput.value = `${state.serverHost}:${state.serverPort}`;
      showToast(`Connected to ${state.serverHost}:${state.serverPort}`, 'success', '💻');
      saveAllSettings(false);
      connect();
    } catch (e) {
      const clean = data.replace(/^https?:\/\//, '');
      const parts = clean.split(':');
      state.serverHost = parts[0];
      state.serverPort = parts[1] || '8000';
      if (el.modalIpInput) el.modalIpInput.value = `${state.serverHost}:${state.serverPort}`;
      if (el.settingsIpInput) el.settingsIpInput.value = `${state.serverHost}:${state.serverPort}`;
      showToast(`Connected to ${state.serverHost}:${state.serverPort}`, 'success', '💻');
      saveAllSettings(false);
      connect();
    }
  }

  // Export to window for native Android Deep Link triggers
  window.parseQrAndConnect = parseQrAndConnect;

  // --- Main Event Handlers Initialization ---
  function initEventHandlers() {
    if (el.btnToggleTitlebar) el.btnToggleTitlebar.onclick = () => toggleTitleBar(true);
    if (el.btnUnhideTitlebar) el.btnUnhideTitlebar.onclick = () => toggleTitleBar(false);
    if (el.modalBtnScanQr) el.modalBtnScanQr.onclick = startQrScanner;
    if (el.settingsBtnScanQr) el.settingsBtnScanQr.onclick = startQrScanner;
    if (el.btnCloseScanner) el.btnCloseScanner.onclick = stopQrScanner;
    if (el.settingsBtnRotate) el.settingsBtnRotate.onclick = toggleScreenOrientation;

    if (el.btnSwitchCamera) {
      el.btnSwitchCamera.onclick = () => {
        state.currentFacingMode = state.currentFacingMode === 'environment' ? 'user' : 'environment';
        stopQrScanner();
        startQrScanner();
      };
    }

    if (el.btnToggleTorch) {
      el.btnToggleTorch.onclick = async () => {
        if (!state.qrStream) return;
        const track = state.qrStream.getVideoTracks()[0];
        if (track) {
          try {
            state.torchActive = !state.torchActive;
            await track.applyConstraints({ advanced: [{ torch: state.torchActive }] });
            el.btnToggleTorch.textContent = state.torchActive ? '💡 Flash: ON' : '💡 Flashlight';
            vibrate(15);
          } catch (e) {
            showToast('Flashlight not available on this lens', 'warn', '💡');
          }
        }
      };
    }

    if (el.modalBtnConnect) {
      el.modalBtnConnect.onclick = () => {
        const val = el.modalIpInput.value.trim();
        if (val) {
          let host = val;
          let port = '8000';
          if (val.includes(':')) {
            const p = val.split(':');
            host = p[0];
            port = p[1] || '8000';
          }
          state.serverHost = host;
          state.serverPort = port;
          saveAllSettings(false);
          connect();
        }
      };
    }

    const btnCloseConnectModal = document.getElementById('btn-close-connect-modal');
    if (btnCloseConnectModal) {
      btnCloseConnectModal.onclick = () => {
        if (el.connectModal) el.connectModal.classList.remove('show');
      };
    }
    if (el.connectModal) {
      el.connectModal.onclick = (e) => {
        if (e.target === el.connectModal) {
          el.connectModal.classList.remove('show');
        }
      };
    }

    if (el.btnReconnectHeader) {
      el.btnReconnectHeader.onclick = () => {
        if (el.connectModal) el.connectModal.classList.add('show');
      };
    }

    if (el.pillStatus) {
      el.pillStatus.onclick = () => {
        if (el.connectModal) el.connectModal.classList.add('show');
      };
    }

    if (el.btnLeftClick) el.btnLeftClick.onclick = () => { vibrate(20); sendCommand('c,left'); };
    if (el.btnMiddleClick) el.btnMiddleClick.onclick = () => { vibrate(20); sendCommand('c,middle'); };
    if (el.btnRightClick) el.btnRightClick.onclick = () => { vibrate(20); sendCommand('c,right'); };

    if (el.btnDesktopQuick) {
      el.btnDesktopQuick.onclick = () => {
        vibrate(15);
        sendCommand('h,win+d');
        showToast('Desktop Toggled', 'info', '🖥️');
      };
    }

    if (el.btnEscQuick) el.btnEscQuick.onclick = () => { vibrate(15); sendCommand('k,escape'); };

    if (el.btnKbdQuick) {
      el.btnKbdQuick.onclick = (e) => {
        e.preventDefault();
        vibrate(20);
        switchTab('tab-keyboard');
        const liveInput = document.getElementById('live-typing-input');
        if (liveInput) {
          setTimeout(() => liveInput.focus(), 150);
        }
        showToast('Switched to Keyboard', 'success', '⌨️');
      };
    }

    if (el.btnSpeedQuick) {
      el.btnSpeedQuick.onclick = (e) => {
        e.preventDefault();
        vibrate(15);
        const speeds = [1.0, 1.5, 2.0, 2.5];
        let nextIdx = (speeds.findIndex(s => Math.abs(s - state.cursorSpeed) < 0.1) + 1) % speeds.length;
        if (nextIdx < 0) nextIdx = 1;
        state.cursorSpeed = speeds[nextIdx];
        if (el.settingCursorSpeed) el.settingCursorSpeed.value = state.cursorSpeed.toString();
        if (el.valCursorSpeed) el.valCursorSpeed.textContent = `${state.cursorSpeed.toFixed(1)}x`;
        el.btnSpeedQuick.textContent = `${state.cursorSpeed.toFixed(1)}x`;
        saveAllSettings(false);
        showToast(`Cursor Speed: ${state.cursorSpeed.toFixed(1)}x`, 'success', '🖱️');
      };
    }

    if (el.toolDragLock) {
      el.toolDragLock.onclick = () => {
        state.dragLocked = !state.dragLocked;
        el.toolDragLock.classList.toggle('active', state.dragLocked);
        el.toolDragLock.textContent = state.dragLocked ? '🔓 Drag: ON' : '🔒 Drag: Off';
        vibrate(25);
        sendCommand(state.dragLocked ? 'd,left' : 'u,left');
      };
    }

    // Interactive Media & Shortcuts
    document.querySelectorAll('[data-media]').forEach(btn => {
      btn.onclick = () => {
        vibrate(18);
        sendCommand(`media,${btn.dataset.media}`);
      };
    });

    document.querySelectorAll('[data-hotkey]').forEach(tile => {
      tile.onclick = () => {
        vibrate(20);
        sendCommand(`h,${tile.dataset.hotkey}`);
        showToast(`Shortcut: ${tile.dataset.hotkey.toUpperCase()}`, 'success', '⌨️');
      };
    });

    // All Virtual & Physical Matrix Keys (including Numpad, D-Pad, F-Keys, Modifiers)
    document.querySelectorAll('[data-key]').forEach(btn => {
      btn.onclick = (e) => {
        e.preventDefault();
        vibrate(18);
        const key = btn.dataset.key;
        sendCommand(`k,${key}`);
      };
    });

    // Settings Sliders & Checkboxes
    if (el.settingCursorSpeed) {
      el.settingCursorSpeed.oninput = () => {
        state.cursorSpeed = parseFloat(el.settingCursorSpeed.value);
        if (el.valCursorSpeed) el.valCursorSpeed.textContent = state.cursorSpeed.toFixed(1) + 'x';
        if (el.btnSpeedQuick) el.btnSpeedQuick.textContent = `${state.cursorSpeed.toFixed(1)}x`;
        saveAllSettings(false);
      };
    }

    if (el.settingScrollSpeed) {
      el.settingScrollSpeed.oninput = () => {
        state.scrollSpeed = parseFloat(el.settingScrollSpeed.value);
        if (el.valScrollSpeed) el.valScrollSpeed.textContent = state.scrollSpeed + 'x';
        saveAllSettings(false);
      };
    }

    if (el.settingZoomSens) {
      el.settingZoomSens.oninput = () => {
        state.zoomSens = parseFloat(el.settingZoomSens.value);
        if (el.valZoomSens) el.valZoomSens.textContent = state.zoomSens + 'x';
        saveAllSettings(false);
      };
    }

    if (el.settingPinchZoom) {
      el.settingPinchZoom.onchange = () => {
        state.pinchZoomEnabled = el.settingPinchZoom.checked;
        if (!state.pinchZoomEnabled) resetPinchZoom();
        saveAllSettings(false);
      };
    }

    if (el.settingAccel) {
      el.settingAccel.onchange = () => {
        state.smoothAccel = el.settingAccel.checked;
        saveAllSettings(false);
      };
    }

    if (el.settingInvertScroll) {
      el.settingInvertScroll.onchange = () => {
        state.invertScroll = el.settingInvertScroll.checked;
        saveAllSettings(false);
      };
    }

    if (el.settingHaptics) {
      el.settingHaptics.onchange = () => {
        state.hapticsEnabled = el.settingHaptics.checked;
        saveAllSettings(false);
      };
    }

    if (el.settingWakelock) {
      el.settingWakelock.onchange = () => {
        state.wakelockEnabled = el.settingWakelock.checked;
        saveAllSettings(false);
      };
    }

    if (el.settingAutoAudio) {
      el.settingAutoAudio.onchange = () => {
        state.autoAudioStream = el.settingAutoAudio.checked;
        if (state.autoAudioStream && state.connected && !audioStreamActive) {
          startAudioStream();
        } else if (!state.autoAudioStream && audioStreamActive) {
          stopAudioStream();
        }
        saveAllSettings(false);
        showToast(state.autoAudioStream ? 'Auto PC Audio: ON' : 'Auto PC Audio: OFF', 'success', '🔊');
      };
    }

    // Global gesture listener to resume Web Audio API if suspended by browser policy.
    // Only resume while a stream is meant to be running: the tap that presses STOP
    // also bubbles up to window, and resuming here replayed the buffered chunks.
    const unlockAudioOnGesture = () => {
      if (audioCtx && audioCtx.state === 'suspended' && audioStreamActive && !userManuallyStoppedAudio) {
        audioCtx.resume().catch(() => {});
      }
      if (state.autoAudioStream && !audioStreamActive && !userManuallyStoppedAudio && state.connected) {
        startAudioStream();
      }
    };
    window.addEventListener('touchstart', unlockAudioOnGesture, { passive: true });
    window.addEventListener('click', unlockAudioOnGesture, { passive: true });

    if (el.btnSaveIp && el.settingsIpInput) {
      el.btnSaveIp.onclick = () => {
        const val = el.settingsIpInput.value.trim();
        if (val) {
          const parts = val.replace('http://', '').replace('https://', '').split(':');
          state.serverHost = parts[0];
          state.serverPort = parts[1] || '8000';
          saveAllSettings(true);
          connect();
        }
      };
    }

    if (el.btnSaveAllSettings) {
      el.btnSaveAllSettings.onclick = () => saveAllSettings(true);
    }

    if (el.btnResetSettings) {
      el.btnResetSettings.onclick = resetAllSettings;
    }

    // Navigation Dock Tab Switching (6 Tabs)
    if (el.dockTabs) {
      el.dockTabs.forEach((tab) => {
        const onTabClick = (e) => {
          e.preventDefault();
          const targetId = tab.dataset.target;
          switchTab(targetId);
        };
        tab.addEventListener('click', onTabClick);
        tab.addEventListener('pointerdown', onTabClick);
      });
    }
  }

  // --- Real-Time PC Audio Receiver & Low-Latency Player ---
  let audioCtx = null;
  let audioGainNode = null;
  let audioAnalyser = null;
  let audioWs = null;
  let nextAudioPlayTime = 0;
  let audioStreamActive = false;
  let userManuallyStoppedAudio = false;
  let html5AudioFallback = null;
  let audioSampleRate = 48000;
  let audioChannels = 2;
  let audioVisualizerAnimId = null;
  let audioConnecting = false;
  // Bumped on every start/stop so async callbacks (WebSocket handlers, <audio>.play()
  // promises) from a superseded session can detect that they are stale and bail out.
  let audioSessionId = 0;
  // Every chunk is scheduled ahead of time; keep the nodes so stop() can kill them.
  const scheduledAudioSources = new Set();

  function ensureAudioContext() {
    if (!audioCtx || audioCtx.state === 'closed') {
      try {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (AudioContextClass) {
          audioCtx = new AudioContextClass({ latencyHint: 'interactive' });
          audioGainNode = audioCtx.createGain();
          audioGainNode.gain.setValueAtTime(state.audioVolume || 1.0, audioCtx.currentTime);
          audioGainNode.connect(audioCtx.destination);

          audioAnalyser = audioCtx.createAnalyser();
          audioAnalyser.fftSize = 64;
          audioAnalyser.smoothingTimeConstant = 0.75;
          audioAnalyser.connect(audioGainNode);
        }
      } catch (e) {
        console.warn('AudioContext creation error:', e);
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume().catch(() => {});
    }
    return audioCtx;
  }

  function initAudioStreamer() {
    if (el.btnToggleAudioStream) {
      el.btnToggleAudioStream.onclick = (e) => {
        if (e) e.preventDefault();
        vibrate(20);
        toggleAudioStreaming();
      };
    }

    if (el.audioVolumeSlider) {
      el.audioVolumeSlider.oninput = () => {
        const val = parseFloat(el.audioVolumeSlider.value);
        state.audioVolume = val;
        if (el.valAudioVolume) el.valAudioVolume.textContent = `${Math.round(val * 100)}%`;
        if (audioGainNode && audioCtx && audioCtx.state !== 'closed') {
          audioGainNode.gain.setValueAtTime(val, audioCtx.currentTime);
        }
        if (html5AudioFallback) html5AudioFallback.volume = val;
      };
    }
  }

  function updateVisualizerLoop() {
    if (!audioStreamActive || !audioAnalyser) {
      if (el.audioVisualizerBars) {
        const bars = el.audioVisualizerBars.children;
        for (let i = 0; i < bars.length; i++) {
          bars[i].style.height = '4px';
          bars[i].style.background = 'var(--neo-cyan)';
        }
      }
      if (audioVisualizerAnimId) {
        cancelAnimationFrame(audioVisualizerAnimId);
        audioVisualizerAnimId = null;
      }
      return;
    }

    const bufferLength = audioAnalyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    audioAnalyser.getByteFrequencyData(dataArray);

    if (el.audioVisualizerBars) {
      const bars = el.audioVisualizerBars.children;
      const step = Math.max(1, Math.floor(bufferLength / bars.length));
      for (let i = 0; i < bars.length; i++) {
        const val = dataArray[i * step] || 0;
        const heightPx = Math.max(4, Math.min(30, Math.round((val / 255) * 30)));
        bars[i].style.height = `${heightPx}px`;
        if (heightPx > 20) {
          bars[i].style.background = 'var(--neo-yellow)';
        } else if (heightPx > 10) {
          bars[i].style.background = 'var(--neo-lime)';
        } else {
          bars[i].style.background = 'var(--neo-cyan)';
        }
      }
    }

    audioVisualizerAnimId = requestAnimationFrame(updateVisualizerLoop);
  }

  function updateAudioUi(active) {
    audioStreamActive = active;
    if (el.btnToggleAudioStream) {
      if (active) {
        el.btnToggleAudioStream.classList.remove('btn-lime');
        el.btnToggleAudioStream.classList.add('btn-pink');
        if (el.audioBtnIcon) el.audioBtnIcon.textContent = '⏹️';
        if (el.audioBtnLabel) el.audioBtnLabel.textContent = 'STOP HEARING PC AUDIO';
      } else {
        el.btnToggleAudioStream.classList.remove('btn-pink');
        el.btnToggleAudioStream.classList.add('btn-lime');
        if (el.audioBtnIcon) el.audioBtnIcon.textContent = '🔊';
        if (el.audioBtnLabel) el.audioBtnLabel.textContent = 'START HEARING PC AUDIO';
      }
    }

    if (el.audioStatusPill) {
      el.audioStatusPill.textContent = active ? 'STREAMING LIVE' : 'OFFLINE';
      if (active) {
        el.audioStatusPill.classList.add('streaming');
        el.audioStatusPill.style.background = 'var(--neo-lime)';
        el.audioStatusPill.style.color = '#000';
        el.audioStatusPill.style.borderColor = '#000';
      } else {
        el.audioStatusPill.classList.remove('streaming');
        el.audioStatusPill.style.background = 'var(--bg-surface-elevated)';
        el.audioStatusPill.style.color = 'var(--text-muted)';
        el.audioStatusPill.style.borderColor = 'var(--neo-dark)';
      }
    }

    if (el.audioVisualizerBars) {
      if (active) {
        if (!audioVisualizerAnimId) updateVisualizerLoop();
      } else {
        if (audioVisualizerAnimId) {
          cancelAnimationFrame(audioVisualizerAnimId);
          audioVisualizerAnimId = null;
        }
        const bars = el.audioVisualizerBars.children;
        for (let i = 0; i < bars.length; i++) {
          bars[i].style.height = '4px';
          bars[i].style.background = 'var(--neo-cyan)';
        }
      }
    }
  }

  function toggleAudioStreaming(forceState) {
    const isCurrentlyActive = audioStreamActive || audioConnecting;
    const target = forceState !== undefined ? forceState : !isCurrentlyActive;
    if (target) {
      userManuallyStoppedAudio = false;
      startAudioStream();
    } else {
      userManuallyStoppedAudio = true;
      stopAudioStream(true);
      showToast('Stopped PC Audio', 'info', '⏹️');
    }
  }

  function startAudioStream() {
    stopAudioStream(false);
    const session = ++audioSessionId;
    userManuallyStoppedAudio = false;
    audioConnecting = true;
    updateAudioUi(true);

    ensureAudioContext();

    // stopAudioStream() zeroes the gain to silence instantly; restore it for the new session.
    if (audioGainNode && audioCtx && audioCtx.state !== 'closed') {
      try {
        audioGainNode.gain.setValueAtTime(state.audioVolume || 1.0, audioCtx.currentTime);
      } catch (e) {}
    }

    const host = state.serverHost || (window.location.hostname && window.location.hostname !== '' ? window.location.hostname : '127.0.0.1');
    const port = state.serverPort || (window.location.port && window.location.port !== '' ? window.location.port : '8000');
    const audioWsUrl = `ws://${host}:${port}/ws/audio`;

    try {
      const ws = new WebSocket(audioWsUrl);
      audioWs = ws;
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        if (session !== audioSessionId) {
          try { ws.close(); } catch (e) {}
          return;
        }
        audioConnecting = false;
        updateAudioUi(true);
        showToast('Streaming PC Audio to Phone!', 'success', '🔊');
      };

      ws.onmessage = (event) => {
        if (session !== audioSessionId || !audioStreamActive) return;

        if (typeof event.data === 'string') {
          if (event.data.startsWith('cfg,')) {
            const parts = event.data.split(',');
            audioSampleRate = parseInt(parts[1] || '48000', 10);
            audioChannels = parseInt(parts[2] || '2', 10);
          }
          return;
        }

        if (event.data instanceof ArrayBuffer) {
          playPcmChunk(event.data);
        }
      };

      ws.onclose = () => {
        if (session !== audioSessionId) return;
        audioConnecting = false;
        if (audioStreamActive && !userManuallyStoppedAudio) {
          stopAudioStream(true);
        }
      };

      ws.onerror = () => {
        if (session !== audioSessionId) return;
        audioConnecting = false;
        if (!userManuallyStoppedAudio) {
          startHtml5AudioFallback(session);
        }
      };

    } catch (e) {
      audioConnecting = false;
      if (session === audioSessionId && !userManuallyStoppedAudio) {
        startHtml5AudioFallback(session);
      }
    }
  }

  function playPcmChunk(arrayBuffer) {
    if (!audioCtx || !audioStreamActive) return;
    if (audioCtx.state === 'suspended') {
      audioCtx.resume().catch(() => {});
    }

    const int16Array = new Int16Array(arrayBuffer);
    const numFrames = Math.floor(int16Array.length / audioChannels);
    if (numFrames <= 0) return;

    try {
      const audioBuffer = audioCtx.createBuffer(audioChannels, numFrames, audioSampleRate);
      for (let channel = 0; channel < audioChannels; channel++) {
        const channelData = audioBuffer.getChannelData(channel);
        for (let i = 0; i < numFrames; i++) {
          channelData[i] = int16Array[i * audioChannels + channel] / 32768.0;
        }
      }

      const source = audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      if (audioAnalyser) {
        source.connect(audioAnalyser);
      } else if (audioGainNode) {
        source.connect(audioGainNode);
      }

      const now = audioCtx.currentTime;
      if (nextAudioPlayTime < now || (nextAudioPlayTime - now) > 0.20) {
        nextAudioPlayTime = now + 0.035;
      }

      // Track the node until it finishes so stopAudioStream() can cut off
      // everything still queued in the ~200ms scheduling window.
      scheduledAudioSources.add(source);
      source.onended = () => {
        scheduledAudioSources.delete(source);
        try { source.disconnect(); } catch (e) {}
      };

      source.start(nextAudioPlayTime);
      nextAudioPlayTime += audioBuffer.duration;
    } catch (e) {
      console.warn('PCM play error:', e);
    }
  }

  function killScheduledAudioSources() {
    scheduledAudioSources.forEach((source) => {
      try { source.onended = null; } catch (e) {}
      try { source.stop(0); } catch (e) {}
      try { source.disconnect(); } catch (e) {}
    });
    scheduledAudioSources.clear();
  }

  function teardownHtml5Fallback(element) {
    if (!element) return;
    try {
      element.pause();
      // removeAttribute + load() aborts the in-flight stream request. Assigning
      // src = '' instead leaves some WebViews fetching (and playing) forever.
      element.removeAttribute('src');
      element.load();
    } catch (e) {}
  }

  function startHtml5AudioFallback(session) {
    if (session !== undefined && session !== audioSessionId) return;

    teardownHtml5Fallback(html5AudioFallback);
    html5AudioFallback = null;

    const host = state.serverHost || (window.location.hostname && window.location.hostname !== '' ? window.location.hostname : '127.0.0.1');
    const port = state.serverPort || (window.location.port && window.location.port !== '' ? window.location.port : '8000');
    const streamUrl = `http://${host}:${port}/api/audio/stream.wav?t=${Date.now()}`;
    const element = new Audio(streamUrl);
    html5AudioFallback = element;
    element.volume = state.audioVolume || 1.0;
    element.play().then(() => {
      // A stop that lands while play() is pending used to leave this element
      // orphaned and playing with no reference left to pause it.
      if (element !== html5AudioFallback || session !== audioSessionId || userManuallyStoppedAudio) {
        teardownHtml5Fallback(element);
        if (element === html5AudioFallback) html5AudioFallback = null;
        return;
      }
      audioConnecting = false;
      updateAudioUi(true);
      showToast('Streaming PC Audio (HTML5 Fallback)', 'success', '🔊');
    }).catch((e) => {
      console.warn('HTML5 audio play error:', e);
      teardownHtml5Fallback(element);
      if (element === html5AudioFallback) html5AudioFallback = null;
      if (session !== audioSessionId || userManuallyStoppedAudio) return;
      stopAudioStream(true);
      showToast('Could not start audio stream', 'error', '❌');
    });
  }

  function stopAudioStream(notifyUi = true) {
    // Invalidate every in-flight async callback belonging to the session being torn down.
    audioSessionId++;
    audioStreamActive = false;
    audioConnecting = false;
    nextAudioPlayTime = 0;

    if (notifyUi) {
      updateAudioUi(false);
    }

    if (audioVisualizerAnimId) {
      cancelAnimationFrame(audioVisualizerAnimId);
      audioVisualizerAnimId = null;
    }

    // Silence synchronously first - suspend() below is async and resolves too late.
    if (audioGainNode && audioCtx && audioCtx.state !== 'closed') {
      try {
        audioGainNode.gain.cancelScheduledValues(audioCtx.currentTime);
        audioGainNode.gain.setValueAtTime(0, audioCtx.currentTime);
      } catch (e) {}
    }
    killScheduledAudioSources();

    if (audioWs) {
      audioWs.onopen = null;
      audioWs.onmessage = null;
      audioWs.onclose = null;
      audioWs.onerror = null;
      try { audioWs.close(); } catch(e) {}
      audioWs = null;
    }

    if (html5AudioFallback) {
      const element = html5AudioFallback;
      html5AudioFallback = null;
      teardownHtml5Fallback(element);
    }

    if (audioCtx && audioCtx.state === 'running') {
      try {
        audioCtx.suspend().catch(() => {});
      } catch(e) {}
    }
  }

  // --- Bootstrapping ---
  /* ==========================================================================
     PCDeck Pro - Official Lemon Squeezy License API Engine & Chroma Themes
     ========================================================================== */

  window.isProUnlocked = function() {
    return localStorage.getItem('pcdeck_pro_active') === 'true';
  };

  window.openProUpgradeModal = function() {
    const modal = document.getElementById('pro-upgrade-modal');
    if (modal) {
      modal.style.display = 'flex';
      vibrate(20);
    }
  };

  window.closeProUpgradeModal = function() {
    const modal = document.getElementById('pro-upgrade-modal');
    if (modal) modal.style.display = 'none';
  };

  function showCelebrationModal() {
    const modal = document.getElementById('pro-celebration-modal');
    if (modal) {
      modal.style.display = 'flex';
      vibrate([50, 50, 100]);
      setTimeout(() => {
        if (modal.style.display === 'flex') modal.style.display = 'none';
      }, 4500);
    }
  }

  function updateProUI() {
    const isPro = window.isProUnlocked();
    if (window.AndroidApp && typeof window.AndroidApp.setProStatus === 'function') {
      window.AndroidApp.setProStatus(isPro);
    }
    const statusTitle = document.getElementById('settings-pro-status-title');
    const statusDesc = document.getElementById('settings-pro-status-desc');
    const btnUpgrade = document.getElementById('btn-open-pro-upgrade');
    const keyRow = document.getElementById('settings-pro-key-row');
    const headerBadge = document.getElementById('header-pro-badge');

    if (headerBadge) {
      headerBadge.style.display = isPro ? 'inline-block' : 'none';
    }

    if (statusTitle) {
      statusTitle.textContent = isPro ? 'PCDeck Pro (Active)' : 'Free Edition';
      statusTitle.style.color = isPro ? '#ffd700' : '#fff';
    }
    if (statusDesc) {
      statusDesc.textContent = isPro ? '60/120 FPS High-Refresh Streaming, Uncapped Bandwidth & OLED Themes Active' : 'Standard 30 FPS screen streaming & 10 MB/s file sharing';
    }
    if (btnUpgrade) {
      btnUpgrade.style.display = isPro ? 'none' : 'block';
    }
    if (keyRow) {
      keyRow.style.display = isPro ? 'none' : 'flex';
    }
  }

  async function activateKey(keyStr) {
    if (!keyStr || !keyStr.trim()) {
      showToast('Please enter your license key', 'warn');
      return false;
    }
    const cleanKey = keyStr.trim();

    // Developer Test Key (For immediate local verification)
    if (cleanKey.toUpperCase() === 'PCDECK-DEV-TEST-KEY-2026') {
      localStorage.setItem('pcdeck_pro_active', 'true');
      localStorage.setItem('pcdeck_pro_license', 'PCDECK-DEV-TEST-KEY-2026');
      localStorage.setItem('pcdeck_pro_instance_id', 'dev-test-instance-001');
      updateProUI();
      window.closeProUpgradeModal();
      showCelebrationModal();
      showToast('Developer Pro License Activated!', 'success');
      return true;
    }

    showToast('Activating with Lemon Squeezy...', 'info');
    try {
      const instanceName = (navigator.userAgent && navigator.userAgent.includes('Android')) 
        ? 'PCDeck Android Device' 
        : 'PCDeck Windows Client';

      const response = await fetch('https://api.lemonsqueezy.com/v1/licenses/activate', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          license_key: cleanKey,
          instance_name: instanceName
        })
      });

      const data = await response.json().catch(() => null);

      if (data && data.activated) {
        localStorage.setItem('pcdeck_pro_active', 'true');
        localStorage.setItem('pcdeck_pro_license', (data.license_key && data.license_key.key) ? data.license_key.key : cleanKey);
        if (data.instance && data.instance.id) {
          localStorage.setItem('pcdeck_pro_instance_id', data.instance.id);
        }
        if (data.meta) {
          localStorage.setItem('pcdeck_pro_meta', JSON.stringify(data.meta));
        }
        updateProUI();
        window.closeProUpgradeModal();
        showCelebrationModal();
        showToast('PCDeck Pro Activated Successfully!', 'success');
        return true;
      } else if (data && data.error) {
        vibrate([40, 40, 40]);
        showToast(`Activation failed: ${data.error}`, 'error');
        return false;
      } else {
        vibrate([40, 40, 40]);
        showToast('Invalid license key. Please check your purchase email.', 'error');
        return false;
      }
    } catch (netErr) {
      vibrate([40, 40, 40]);
      showToast('Activation error: Internet connection required to verify license.', 'error');
      return false;
    }
  }

  function applyChromaTheme(themeId) {
    document.body.removeAttribute('data-theme');
    if (themeId && themeId !== 'default') {
      document.body.setAttribute('data-theme', themeId);
    }
    localStorage.setItem('pcdeck_chroma_theme', themeId);
  }

  function initProEngine() {
    updateProUI();

    // Restore saved theme
    const savedTheme = localStorage.getItem('pcdeck_chroma_theme') || 'default';
    if (savedTheme !== 'default' && window.isProUnlocked()) {
      applyChromaTheme(savedTheme);
      const sel = document.getElementById('setting-theme-picker');
      if (sel) sel.value = savedTheme;
    }

    // Corner Pro Notification Toast / Card (Bottom-Right)
    let proCornerTimeout = null;
    window.showProCornerCard = function() {
      const card = document.getElementById('pro-corner-card');
      if (card) {
        card.classList.add('show');
        vibrate(25);
        if (proCornerTimeout) clearTimeout(proCornerTimeout);
        proCornerTimeout = setTimeout(() => {
          card.classList.remove('show');
        }, 8000);
      }
    };

    window.hideProCornerCard = function() {
      const card = document.getElementById('pro-corner-card');
      if (card) card.classList.remove('show');
      if (proCornerTimeout) clearTimeout(proCornerTimeout);
    };

    window.openProWebsite = function() {
      const checkoutUrl = 'https://pcdeck.lemonsqueezy.com/checkout/buy/5231b162-7c25-44f2-bcc3-f384839344c3';
      if (window.AndroidApp && typeof window.AndroidApp.openUrl === 'function') {
        window.AndroidApp.openUrl(checkoutUrl);
      } else {
        window.open(checkoutUrl, '_blank');
      }
    };

    // Modal buttons
    const btnOpenPro = document.getElementById('btn-open-pro-upgrade');
    if (btnOpenPro) btnOpenPro.onclick = window.openProUpgradeModal;

    const btnClosePro = document.getElementById('modal-btn-close-pro');
    if (btnClosePro) btnClosePro.onclick = window.closeProUpgradeModal;

    const btnBuyPro = document.getElementById('modal-btn-buy-pro');
    if (btnBuyPro) {
      btnBuyPro.onclick = window.openProWebsite;
    }

    const btnCloseCelebration = document.getElementById('btn-close-celebration');
    if (btnCloseCelebration) {
      btnCloseCelebration.onclick = () => {
        const modal = document.getElementById('pro-celebration-modal');
        if (modal) modal.style.display = 'none';
      };
    }

    // Corner Card Buttons
    const btnCloseCorner = document.getElementById('btn-close-pro-corner');
    if (btnCloseCorner) btnCloseCorner.onclick = window.hideProCornerCard;

    const btnCornerBuy = document.getElementById('btn-corner-buy-pro');
    if (btnCornerBuy) btnCornerBuy.onclick = () => {
      window.hideProCornerCard();
      window.openProWebsite();
    };

    const btnCornerModal = document.getElementById('btn-corner-open-modal');
    if (btnCornerModal) btnCornerModal.onclick = () => {
      window.hideProCornerCard();
      window.openProUpgradeModal();
    };

    // Key activation from modal
    const btnActModal = document.getElementById('modal-btn-activate-key');
    const inputKeyModal = document.getElementById('modal-pro-key-input');
    if (btnActModal && inputKeyModal) {
      btnActModal.onclick = () => activateKey(inputKeyModal.value);
    }

    // Key activation from settings tab
    const btnActSettings = document.getElementById('btn-activate-key-settings');
    const inputKeySettings = document.getElementById('input-license-key-settings');
    if (btnActSettings && inputKeySettings) {
      btnActSettings.onclick = () => activateKey(inputKeySettings.value);
    }

    // Radio Segmented FPS Toggle in Title Bar
    window.setStreamFps = function(fpsVal) {
      const btn30 = document.getElementById('btn-fps-30');
      const btn60 = document.getElementById('btn-fps-60');
      const selFps = document.getElementById('setting-stream-fps');

      if (fpsVal === 60 || fpsVal === '60') {
        if (!window.isProUnlocked()) {
          // Keep at 30 FPS, open Pro upgrade modal and notify user
          if (btn60) btn60.classList.remove('active');
          if (btn30) btn30.classList.add('active');
          if (selFps) selFps.value = '30';
          window.openProUpgradeModal();
          showToast('60 FPS Ultra Streaming requires PCDeck Pro', 'warn', '⭐');
          return;
        }
        if (btn30) btn30.classList.remove('active');
        if (btn60) btn60.classList.add('active');
        if (selFps) selFps.value = '60';
        state.streamFps = 60;
        sendStreamConfig();
        saveAllSettings(false);
        showToast('Screen streaming set to 60 FPS Ultra', 'success', '🖥️');
      } else {
        if (btn60) btn60.classList.remove('active');
        if (btn30) btn30.classList.add('active');
        if (selFps) selFps.value = '30';
        state.streamFps = 30;
        sendStreamConfig();
        saveAllSettings(false);
        showToast('Screen streaming set to 30 FPS Standard', 'success', '🎬');
      }
    };

    const btnFps30 = document.getElementById('btn-fps-30');
    const btnFps60 = document.getElementById('btn-fps-60');
    if (btnFps30) btnFps30.onclick = () => window.setStreamFps(30);
    if (btnFps60) btnFps60.onclick = () => window.setStreamFps(60);

    // FPS Gate in Settings
    const selFps = document.getElementById('setting-stream-fps');
    if (selFps) {
      selFps.onchange = () => {
        if ((selFps.value === '60' || selFps.value === '120') && !window.isProUnlocked()) {
          selFps.value = '30';
          window.openProUpgradeModal();
          showToast('60 FPS High-Refresh Streaming requires PCDeck Pro', 'info', '⭐');
          return;
        }
        window.setStreamFps(selFps.value === '30' ? 30 : 60);
      };
    }

    // Adaptive Stream Quality Selector
    const selClarity = document.getElementById('setting-stream-clarity');
    if (selClarity) {
      selClarity.onchange = () => {
        const val = selClarity.value;
        state.autoQualityMode = val;
        if (val === 'auto') {
          showToast('✨ Auto Dynamic Quality Enabled (2.4G/5G/6G AI-Tuned)', 'success', '✨');
          updateAdaptiveQuality(state.latency || 25);
        } else if (val === 'ultrahd') {
          state.streamQuality = 90;
          state.streamScale = 1.0;
          showToast('Ultra HD Crystal Enabled (100% Native · 90Q · 5GHz/6GHz)', 'success', '✨');
          sendStreamConfig();
        } else if (val === 'sharp') {
          state.streamQuality = 80;
          state.streamScale = 0.90;
          showToast('High Clarity Fixed (90% Scale · 80Q)', 'success', '🔍');
          sendStreamConfig();
        } else if (val === 'speed') {
          state.streamQuality = 55;
          state.streamScale = 0.65;
          showToast('Low Latency Speed (65% Scale · 55Q · 2.4GHz)', 'info', '⚡');
          sendStreamConfig();
        } else {
          state.streamQuality = 70;
          state.streamScale = 0.80;
          showToast('Balanced Fast (80% Scale · 70Q)', 'success', '🔍');
          sendStreamConfig();
        }
        saveAllSettings(false);
      };
    }

    // Reflect the saved FPS choice in the title-bar toggle on startup.
    (function syncFpsButtons() {
      const btn30 = document.getElementById('btn-fps-30');
      const btn60 = document.getElementById('btn-fps-60');
      const use60 = state.streamFps === 60 && window.isProUnlocked();
      if (!use60) state.streamFps = 30;
      if (btn30) btn30.classList.toggle('active', !use60);
      if (btn60) btn60.classList.toggle('active', use60);
      if (selFps) selFps.value = use60 ? '60' : '30';
    })();

    // Turbo Speed Gate
    const selSpeed = document.getElementById('setting-transfer-speed');
    if (selSpeed) {
      selSpeed.onchange = () => {
        if (selSpeed.value === 'turbo' && !window.isProUnlocked()) {
          selSpeed.value = 'standard';
          window.showProCornerCard();
          showToast('Uncapped LAN File Bandwidth requires PCDeck Pro', 'info', '⭐');
        }
      };
    }

    // Theme Picker Gate
    const selTheme = document.getElementById('setting-theme-picker');
    if (selTheme) {
      selTheme.onchange = () => {
        if (selTheme.value !== 'default' && !window.isProUnlocked()) {
          selTheme.value = 'default';
          applyChromaTheme('default');
          window.showProCornerCard();
          showToast('Custom Accent Themes require PCDeck Pro', 'info', '⭐');
        } else {
          applyChromaTheme(selTheme.value);
        }
      };
    }
  }

  // --- Cyber-Neon Onboarding Carousel & Direct-to-QR Flow ---
  function initOnboardingEngine() {
    const modal = document.getElementById('onboarding-modal');
    if (!modal) return;

    let currentSlide = 1;
    const totalSlides = 2;

    function showSlide(index) {
      currentSlide = Math.max(1, Math.min(totalSlides, index));
      const slides = modal.querySelectorAll('.onboarding-slide');
      slides.forEach(s => {
        const slideNum = parseInt(s.getAttribute('data-slide'), 10);
        s.classList.toggle('active', slideNum === currentSlide);
      });

      const dots = modal.querySelectorAll('.dot-indicator');
      dots.forEach(d => {
        const dotNum = parseInt(d.getAttribute('data-dot'), 10);
        d.classList.toggle('active', dotNum === currentSlide);
      });

      const btnPrev = document.getElementById('btn-onboarding-prev');
      const btnNext = document.getElementById('btn-onboarding-next');
      if (btnPrev) btnPrev.style.display = currentSlide > 1 ? 'inline-flex' : 'none';
      if (btnNext) {
        btnNext.textContent = currentSlide === 1 ? 'NEXT: CONNECT ➔' : '📷 SCAN PC QR CODE ➔';
      }
    }

    window.openOnboardingModal = function() {
      showSlide(1);
      modal.classList.add('show');
      vibrate(20);
    };

    window.closeOnboardingModal = function(completed = true) {
      modal.classList.remove('show');
      if (completed) {
        localStorage.setItem('pcdeck_onboarding_completed', 'true');
      }
      const isNativeApp = !!window.AndroidApp || window.location.protocol === 'file:';
      // If not connected and in native app without saved IP, show connect modal
      if (!state.connected && !localStorage.getItem('neontrack_ip') && isNativeApp) {
        if (el.connectModal) el.connectModal.classList.add('show');
      }
    };

    const btnSkip = document.getElementById('btn-skip-onboarding');
    if (btnSkip) btnSkip.onclick = () => window.closeOnboardingModal(true);

    const btnPrev = document.getElementById('btn-onboarding-prev');
    if (btnPrev) btnPrev.onclick = () => showSlide(currentSlide - 1);

    const btnNext = document.getElementById('btn-onboarding-next');
    if (btnNext) {
      btnNext.onclick = () => {
        if (currentSlide < totalSlides) {
          showSlide(currentSlide + 1);
        } else {
          window.closeOnboardingModal(true);
          startQrScanner();
        }
      };
    }

    const dots = modal.querySelectorAll('.dot-indicator');
    dots.forEach(d => {
      d.onclick = () => {
        const dotNum = parseInt(d.getAttribute('data-dot'), 10);
        if (dotNum) showSlide(dotNum);
      };
    });

    const pcWebsiteUrl = 'https://pcdeck-pro.vercel.app';
    const pcTutorialsUrl = 'https://pcdeck-pro.vercel.app/#install-help';

    const btnOpenSite = document.getElementById('btn-onboarding-open-site');
    if (btnOpenSite) {
      btnOpenSite.onclick = () => {
        if (window.AndroidApp && typeof window.AndroidApp.openUrl === 'function') {
          window.AndroidApp.openUrl(pcWebsiteUrl);
        } else {
          window.open(pcWebsiteUrl, '_blank');
        }
        showToast('Opening PCDeck Website...', 'success', '🌐');
      };
    }

    const btnTutorials = document.getElementById('btn-onboarding-tutorials');
    if (btnTutorials) {
      btnTutorials.onclick = () => {
        if (window.AndroidApp && typeof window.AndroidApp.openUrl === 'function') {
          window.AndroidApp.openUrl(pcTutorialsUrl);
        } else {
          window.open(pcTutorialsUrl, '_blank');
        }
        showToast('Opening Setup Guides & Tutorials...', 'success', '📖');
      };
    }

    const btnShareLink = document.getElementById('btn-onboarding-share-link');
    if (btnShareLink) {
      btnShareLink.onclick = () => {
        if (navigator.share) {
          navigator.share({
            title: 'PCDeck for Windows',
            text: 'Download the free PCDeck Windows client to connect your phone:',
            url: pcWebsiteUrl
          }).catch(() => {});
        } else if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(pcWebsiteUrl).then(() => {
            showToast('Copied link: pcdeck-pro.vercel.app', 'success', '📋');
          });
        } else {
          showToast('Visit pcdeck-pro.vercel.app on your PC', 'info', '🌐');
        }
      };
    }

    // Trigger buttons from Connect Modal & Settings
    const btnOpenGuide = document.getElementById('btn-open-setup-guide');
    if (btnOpenGuide) {
      btnOpenGuide.onclick = () => {
        if (el.connectModal) el.connectModal.classList.remove('show');
        window.openOnboardingModal();
      };
    }

    const btnSettingsGuide = document.getElementById('btn-settings-open-guide');
    if (btnSettingsGuide) {
      btnSettingsGuide.onclick = () => {
        window.openOnboardingModal();
      };
    }
  }

  function bootstrap() {
    initDomElements();
    loadSettings();
    initScreenTouchDisplay();
    initPinchZoomGestures();
    initTrackpad();
    initVirtualKeyboard();
    initScreenKeyboard();
    initQuickTools();
    initFileManager();
    initAudioStreamer();
    initEventHandlers();
    initProEngine();
    initOnboardingEngine();

    // Flexible Onboarding & Auto-Connection for Web vs App
    const isHttp = window.location.protocol.startsWith('http') && window.location.hostname;
    const isNativeApp = !!window.AndroidApp || window.location.protocol === 'file:';
    const onboardingDone = localStorage.getItem('pcdeck_onboarding_completed');
    const savedIp = localStorage.getItem('neontrack_ip') || (isHttp ? `${state.serverHost}:${state.serverPort}` : null);

    if (isHttp && !isNativeApp) {
      // In web browser mode: seamlessly auto-connect with ZERO modal popups!
      if (el.connectModal) el.connectModal.classList.remove('show');
      const obModal = document.getElementById('onboarding-modal');
      if (obModal) obModal.classList.remove('show');
      connect();
    } else if (!onboardingDone && isNativeApp) {
      if (typeof window.openOnboardingModal === 'function') {
        window.openOnboardingModal();
      }
    } else if (savedIp) {
      connect();
    } else {
      if (el.connectModal) el.connectModal.classList.add('show');
    }

    document.addEventListener('fullscreenchange', updateQuickToolsUi);
    document.addEventListener('webkitfullscreenchange', updateQuickToolsUi);
    window.addEventListener('resize', updateQuickToolsUi);
    window.addEventListener('orientationchange', updateQuickToolsUi);

    // Initialize In-App OTA Auto-Updater System
    initAppUpdater();
  }

  // ==========================================
  // IN-APP OTA AUTO-UPDATER SYSTEM
  // ==========================================
  const CURRENT_APP_VERSION_CODE = 266;
  const CURRENT_APP_VERSION_NAME = '2.6.6';
  let updateDownloadApkUrl = 'https://pcdeck.vercel.app/PCDeck.apk';

  function initAppUpdater() {
    const btnCheckUpdates = document.getElementById('btn-check-for-updates');
    const updateStatusText = document.getElementById('app-update-status-text');
    const appVersionLabel = document.getElementById('app-current-version-label');
    const updateModal = document.getElementById('update-modal');
    const btnUpdateNow = document.getElementById('btn-update-now');
    const btnUpdateLater = document.getElementById('btn-update-later');
    const progressContainer = document.getElementById('update-progress-container');
    const progressBar = document.getElementById('update-progress-bar');
    const progressPercent = document.getElementById('update-progress-percent');
    const actionsRow = document.getElementById('update-actions-row');

    if (appVersionLabel) {
      if (window.AndroidApp && typeof window.AndroidApp.getAppVersionName === 'function') {
        appVersionLabel.innerText = 'v' + window.AndroidApp.getAppVersionName();
      } else {
        appVersionLabel.innerText = 'v' + CURRENT_APP_VERSION_NAME;
      }
    }

    window.onApkUpdateProgress = function(percent) {
      if (progressContainer) progressContainer.style.display = 'block';
      if (progressBar) progressBar.style.width = percent + '%';
      if (progressPercent) progressPercent.innerText = percent + '%';
      if (percent >= 100) {
        if (updateStatusText) updateStatusText.innerText = 'Installing update...';
      }
    };

    let targetUpdateUrl = 'https://pcdeck.vercel.app';
    let isPlayStoreTarget = false;

    async function checkVersionUpdates(isManual = false) {
      try {
        if (updateStatusText && isManual) updateStatusText.innerText = 'Checking for updates...';
        
        let localCode = CURRENT_APP_VERSION_CODE;
        if (window.AndroidApp && typeof window.AndroidApp.getAppVersionCode === 'function') {
          localCode = window.AndroidApp.getAppVersionCode();
        }

        // Fetch version.json from website with cache-busting
        const res = await fetch('https://pcdeck.vercel.app/version.json?_t=' + Date.now(), { cache: 'no-store' });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();

        if (data && data.versionCode && data.versionCode > localCode) {
          const hasPlayStore = !!(data.playStoreUrl && data.playStoreUrl.trim());
          isPlayStoreTarget = hasPlayStore;
          targetUpdateUrl = hasPlayStore ? data.playStoreUrl.trim() : (data.websiteUrl || 'https://pcdeck.vercel.app');

          if (updateStatusText) updateStatusText.innerText = `New update available (v${data.versionName || data.versionCode})`;
          
          // Populate modal
          const modalTitle = document.getElementById('update-modal-title');
          const modalSubtitle = document.getElementById('update-modal-subtitle');
          const modalNotes = document.getElementById('update-modal-notes');
          const btnNowLabel = document.getElementById('btn-update-now-label');

          if (modalTitle) modalTitle.innerText = `PCDeck v${data.versionName || data.versionCode}`;
          if (modalSubtitle) {
            modalSubtitle.innerText = hasPlayStore ? 'A new update is available on Google Play!' : 'A new version is ready to download from our website!';
          }
          if (modalNotes && data.releaseNotes) modalNotes.innerText = data.releaseNotes;
          if (btnNowLabel) {
            btnNowLabel.innerText = hasPlayStore ? '🛍️ OPEN PLAY STORE ➔' : '🌐 GET UPDATE ON WEBSITE ➔';
          }

          if (updateModal) {
            updateModal.style.display = 'flex';
            updateModal.classList.add('show');
          }
          vibrate(30);
        } else {
          if (updateStatusText) updateStatusText.innerText = 'PCDeck is up to date (v' + (data.versionName || CURRENT_APP_VERSION_NAME) + ')';
          if (isManual) {
            showToast('You are on the latest version of PCDeck!', 'success', '✨');
          }
        }
      } catch (err) {
        if (isManual) {
          showToast('Could not check for updates. Check internet.', 'warn', '⚠️');
        }
        if (updateStatusText) updateStatusText.innerText = 'Latest version verified';
      }
    }

    if (btnCheckUpdates) {
      btnCheckUpdates.onclick = () => {
        vibrate(15);
        checkVersionUpdates(true);
      };
    }

    if (btnUpdateLater && updateModal) {
      btnUpdateLater.onclick = () => {
        vibrate(10);
        updateModal.classList.remove('show');
        updateModal.style.display = 'none';
      };
    }

    if (btnUpdateNow) {
      btnUpdateNow.onclick = () => {
        vibrate(25);
        if (updateModal) {
          updateModal.classList.remove('show');
          updateModal.style.display = 'none';
        }

        showToast(isPlayStoreTarget ? 'Opening Google Play Store...' : 'Opening PCDeck Website...', 'success', '🌐');

        if (window.AndroidApp && typeof window.AndroidApp.openUrl === 'function') {
          window.AndroidApp.openUrl(targetUpdateUrl);
        } else {
          window.open(targetUpdateUrl, '_blank');
        }
      };
    }

    // Auto-check 4 seconds after launch in background
    setTimeout(() => {
      checkVersionUpdates(false);
    }, 4000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }
})();

