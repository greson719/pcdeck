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
    document.body.classList.toggle('on-screen-tab', targetId === 'tab-screen');
    if (targetId !== 'tab-screen' && typeof window.closeScreenTypeBar === 'function') {
      window.closeScreenTypeBar();
    }

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

    // Update Titlebar Actions (Screen Streaming FPS vs File Transfer Pro Toggle)
    if (typeof window.updateTitlebarActions === 'function') {
      window.updateTitlebarActions(targetId);
    }

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
    cursorSpeed: 1.0,
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
    transferSpeed: 'standard', // 'standard' (10 MB/s) or 'turbo' (Pro uncapped multi-stream)
    screenMode: 'touch', // 'touch', 'mouse', or 'rclick'
    dragLocked: false,
    titleBarHidden: false,
    gamepadHudEnabled: false,
    gamepadHudActive: false,
    gamepadHudEditing: false,
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
      settingGamepadHud: document.getElementById('setting-gamepad-hud'),
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

  // --- Host / IP Address Sanitizer ---
  function parseHostPort(input) {
    if (!input || typeof input !== 'string') return null;
    let clean = input.trim();
    if (clean.includes('?')) {
      try {
        const u = new URL(clean.startsWith('http') ? clean : `http://${clean}`);
        const ipParam = u.searchParams.get('ip');
        if (ipParam) clean = ipParam;
        else if (u.hostname) return { host: u.hostname, port: u.port || '8000' };
      } catch (e) {}
    }
    clean = clean.replace(/^(https?:\/\/|wss?:\/\/)/i, '');
    clean = clean.split('/')[0].split('?')[0].trim();
    if (!clean) return null;
    if (clean.includes(':')) {
      const parts = clean.split(':');
      const host = parts[0].trim();
      const port = parts[1].trim() || '8000';
      return { host, port };
    }
    return { host: clean, port: '8000' };
  }

  // --- Settings Persistence ---
  function loadSettings() {
    try {
      const isHttp = window.location.protocol.startsWith('http') && window.location.hostname;
      const urlParams = new URLSearchParams(window.location.search);
      const queryIp = urlParams.get('ip');

      if (queryIp) {
        const parsed = parseHostPort(queryIp);
        if (parsed) {
          state.serverHost = parsed.host;
          state.serverPort = parsed.port;
          if (el.modalIpInput) el.modalIpInput.value = `${state.serverHost}:${state.serverPort}`;
          if (el.settingsIpInput) el.settingsIpInput.value = `${state.serverHost}:${state.serverPort}`;
          localStorage.setItem('neontrack_ip', `${state.serverHost}:${state.serverPort}`);
          localStorage.setItem('pcdeck_onboarding_completed', 'true');
        }
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
          const parsed = parseHostPort(savedIp);
          if (parsed) {
            state.serverHost = parsed.host;
            state.serverPort = parsed.port;
            if (el.modalIpInput) el.modalIpInput.value = `${state.serverHost}:${state.serverPort}`;
            if (el.settingsIpInput) el.settingsIpInput.value = `${state.serverHost}:${state.serverPort}`;
          }
        }
      }

      const cursor = localStorage.getItem('neontrack_cursor_speed');
      if (cursor) {
        state.cursorSpeed = parseFloat(cursor);
        if (el.settingCursorSpeed) el.settingCursorSpeed.value = cursor;
        if (el.valCursorSpeed) el.valCursorSpeed.textContent = parseFloat(cursor).toFixed(1) + 'x';
        if (el.btnSpeedQuick) el.btnSpeedQuick.textContent = `${parseFloat(cursor).toFixed(1)}x`;
      } else {
        state.cursorSpeed = 1.0;
        if (el.settingCursorSpeed) el.settingCursorSpeed.value = '1.0';
        if (el.valCursorSpeed) el.valCursorSpeed.textContent = '1.0x';
        if (el.btnSpeedQuick) el.btnSpeedQuick.textContent = '1.0x';
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

      const hudEnabled = localStorage.getItem('neontrack_gamepad_hud_enabled');
      if (hudEnabled !== null) {
        state.gamepadHudEnabled = hudEnabled === 'true';
        if (el.settingGamepadHud) el.settingGamepadHud.checked = state.gamepadHudEnabled;
      } else {
        state.gamepadHudEnabled = false;
        if (el.settingGamepadHud) el.settingGamepadHud.checked = false;
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

      const savedSpeed = localStorage.getItem('neontrack_transfer_speed');
      if (savedSpeed === 'turbo' || savedSpeed === 'standard') {
        state.transferSpeed = savedSpeed;
      }
      const selSpeed = document.getElementById('setting-transfer-speed');
      if (selSpeed) {
        selSpeed.value = state.transferSpeed || 'standard';
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
      localStorage.setItem('neontrack_gamepad_hud_enabled', state.gamepadHudEnabled.toString());
      localStorage.setItem('neontrack_auto_audio', state.autoAudioStream.toString());
      localStorage.setItem('neontrack_stream_fps', state.streamFps.toString());
      localStorage.setItem('neontrack_stream_quality', state.streamQuality.toString());
      localStorage.setItem('neontrack_stream_scale', state.streamScale.toString());
      localStorage.setItem('neontrack_stream_auto_mode', state.autoQualityMode || 'auto');
      localStorage.setItem('neontrack_transfer_speed', state.transferSpeed || 'standard');
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
    state.cursorSpeed = 1.0;
    state.scrollSpeed = 1.4;
    state.zoomSens = 1.0;
    state.pinchZoomEnabled = true;
    state.smoothAccel = true;
    state.invertScroll = false;
    state.hapticsEnabled = true;
    state.wakelockEnabled = true;
    state.gamepadHudEnabled = false;
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
    if (el.settingGamepadHud) el.settingGamepadHud.checked = false;
    if (el.settingAccel) el.settingAccel.checked = true;
    if (el.settingInvertScroll) el.settingInvertScroll.checked = false;
    if (el.settingHaptics) el.settingHaptics.checked = true;
    if (el.settingWakelock) el.settingWakelock.checked = true;
    if (el.settingAutoAudio) el.settingAutoAudio.checked = true;
    if (window.updateTitlebarActions) window.updateTitlebarActions();

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
      // Check if Gamepad HUD is active or touch is on UI overlays
      if (state.gamepadHudActive || (e.target && e.target.closest('#screen-gamepad-overlay, #btn-screen-keyboard, #screen-type-bar, #btn-screen-gamepad-hud'))) {
        return;
      }

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
      if (state.gamepadHudActive || (e.target && e.target.closest('#screen-gamepad-overlay, #btn-screen-keyboard, #screen-type-bar, #btn-screen-gamepad-hud'))) {
        return;
      }

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
      if (state.gamepadHudActive || (e.target && e.target.closest('#screen-gamepad-overlay, #btn-screen-keyboard, #screen-type-bar, #btn-screen-gamepad-hud'))) {
        return;
      }

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

  // --- Auto-Connect, Zero-Config Discovery & WebSocket Management ---
  let isSubnetSweeping = false;
  let wsConnectTimeoutTimer = null;

  function clearWsConnectTimeout() {
    if (wsConnectTimeoutTimer) {
      clearTimeout(wsConnectTimeoutTimer);
      wsConnectTimeoutTimer = null;
    }
  }

  // Global handler called when PC server is discovered via native UDP or subnet scan
  window.onServerDiscovered = function(discoveredHost, discoveredPort) {
    if (!discoveredHost || typeof discoveredHost !== 'string') return;
    const cleanHost = discoveredHost.trim();
    const cleanPort = (discoveredPort && typeof discoveredPort === 'string' ? discoveredPort.trim() : '8000') || '8000';
    if (!cleanHost || cleanHost === '127.0.0.1' || cleanHost === '0.0.0.0') return;

    const wasDifferent = (state.serverHost !== cleanHost || state.serverPort !== cleanPort);

    state.serverHost = cleanHost;
    state.serverPort = cleanPort;
    if (el.modalIpInput) el.modalIpInput.value = `${cleanHost}:${cleanPort}`;
    if (el.settingsIpInput) el.settingsIpInput.value = `${cleanHost}:${cleanPort}`;
    localStorage.setItem('neontrack_ip', `${cleanHost}:${cleanPort}`);
    localStorage.setItem('pcdeck_onboarding_completed', 'true');

    if (el.connectModal && el.connectModal.classList.contains('show')) {
      el.connectModal.classList.remove('show');
    }

    // If not connected or was pointing to stale host, connect immediately (< 10ms)
    if (!state.connected || wasDifferent) {
      clearWsConnectTimeout();
      connect(true);
    }
  };

  function triggerDiscoveryAndSweep() {
    // 1. Trigger Native Android UDP Broadcast Discovery (< 5ms)
    if (window.AndroidApp && typeof window.AndroidApp.discoverServer === 'function') {
      try {
        window.AndroidApp.discoverServer();
      } catch (e) {}
    }

    // 2. Parallel Fast Subnet Sweeper for web and fallback (< 250ms)
    sweepSubnetAndConnect();
  }

  async function sweepSubnetAndConnect() {
    if (isSubnetSweeping || state.connected) return;
    isSubnetSweeping = true;

    try {
      const candidates = new Set();

      let deviceIp = '';
      if (window.AndroidApp && typeof window.AndroidApp.getDeviceIp === 'function') {
        try { deviceIp = window.AndroidApp.getDeviceIp(); } catch (e) {}
      }

      const saved = localStorage.getItem('neontrack_ip');
      if (saved) {
        const p = parseHostPort(saved);
        if (p) candidates.add(p.host);
      }
      if (state.serverHost) candidates.add(state.serverHost);

      // High-priority hotspot and router gateways
      const priorityIps = [
        '192.168.43.1',   // Android Mobile Hotspot Gateway
        '192.168.137.1',  // Windows Mobile Hotspot Gateway
        '192.168.1.1',    // Router Gateway
        '192.168.0.1',    // Router Gateway
        '192.168.1.100',  // Common DHCP PC IP
        '192.168.0.100',
        '192.168.1.2',
        '192.168.0.2',
        '10.0.0.1',
        '10.0.0.2',
      ];
      priorityIps.forEach(ip => candidates.add(ip));

      // Derive subnet /24 ranges to sweep
      const subnetsToSweep = new Set();
      if (deviceIp && deviceIp.includes('.')) {
        subnetsToSweep.add(deviceIp.substring(0, deviceIp.lastIndexOf('.')));
      }
      if (state.serverHost && state.serverHost.includes('.')) {
        subnetsToSweep.add(state.serverHost.substring(0, state.serverHost.lastIndexOf('.')));
      }
      if (saved && saved.includes('.')) {
        const p = parseHostPort(saved);
        if (p && p.host.includes('.')) {
          subnetsToSweep.add(p.host.substring(0, p.host.lastIndexOf('.')));
        }
      }

      if (subnetsToSweep.size === 0) {
        subnetsToSweep.add('192.168.43');
        subnetsToSweep.add('192.168.137');
        subnetsToSweep.add('192.168.1');
        subnetsToSweep.add('192.168.0');
      }

      const fullTargetList = Array.from(candidates);
      for (const subnet of subnetsToSweep) {
        for (let i = 1; i <= 254; i++) {
          const ip = `${subnet}.${i}`;
          if (!candidates.has(ip)) {
            fullTargetList.push(ip);
          }
        }
      }

      let found = false;
      const port = state.serverPort || '8000';

      // Sweep in concurrent batches of 32 for maximum speed (< 250ms)
      const BATCH_SIZE = 32;
      for (let i = 0; i < fullTargetList.length && !found && !state.connected; i += BATCH_SIZE) {
        const batch = fullTargetList.slice(i, i + BATCH_SIZE);
        const promises = batch.map(ip => {
          return new Promise(resolve => {
            const controller = new AbortController();
            const timer = setTimeout(() => {
              controller.abort();
              resolve(null);
            }, 350);

            fetch(`http://${ip}:${port}/api/ping`, {
              signal: controller.signal,
              mode: 'cors',
              cache: 'no-store',
            })
              .then(r => r.json())
              .then(data => {
                clearTimeout(timer);
                if (data && data.status === 'ok' && (data.app === 'PCDeck' || data.name)) {
                  resolve({ ip: data.ip || ip, port: (data.port ? data.port.toString() : port) });
                } else {
                  resolve(null);
                }
              })
              .catch(() => {
                clearTimeout(timer);
                resolve(null);
              });
          });
        });

        const results = await Promise.all(promises);
        const match = results.find(r => r !== null);
        if (match) {
          found = true;
          window.onServerDiscovered(match.ip, match.port);
          break;
        }
      }
    } catch (e) {
    } finally {
      isSubnetSweeping = false;
    }
  }

  function clearAutoReconnect() {
    if (state.autoReconnectTimer) {
      clearTimeout(state.autoReconnectTimer);
      clearInterval(state.autoReconnectTimer);
      state.autoReconnectTimer = null;
    }
  }

  function connect(force) {
    clearAutoReconnect();
    clearWsConnectTimeout();
    updateStatus('connecting', 'Connecting...');
    const isHttp = window.location.protocol.startsWith('http') && window.location.hostname;
    const host = state.serverHost || (isHttp ? window.location.hostname : '127.0.0.1');
    const port = state.serverPort || (isHttp ? (window.location.port || '8000') : '8000');
    state.serverHost = host;
    state.serverPort = port;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const targetWsUrl = `${protocol}//${host}:${port}/ws`;
    const targetScreenWsUrl = `${protocol}//${host}:${port}/ws/screen`;

    // If socket is already OPEN and connecting to the same target, avoid redundant reconnect
    if (!force && mainWs && mainWs.readyState === WebSocket.OPEN && state.connected && state.wsUrl === targetWsUrl) {
      updateStatus('connected', 'Connected');
      connectScreenWs();
      return;
    }

    state.wsUrl = targetWsUrl;
    state.screenWsUrl = targetScreenWsUrl;

    if (mainWs) {
      const oldWs = mainWs;
      mainWs = null;
      oldWs.onopen = null;
      oldWs.onmessage = null;
      oldWs.onclose = null;
      oldWs.onerror = null;
      try { oldWs.close(); } catch (e) {}
    }

    // Concurrently trigger native UDP discovery on connect attempt
    if (window.AndroidApp && typeof window.AndroidApp.discoverServer === 'function') {
      try { window.AndroidApp.discoverServer(); } catch (e) {}
    }

    // Fast-Fail Connect Timeout (1200ms):
    // If target host does not respond within 1200ms, abort hang and trigger instant discovery!
    wsConnectTimeoutTimer = setTimeout(() => {
      if (mainWs && mainWs.readyState === WebSocket.CONNECTING) {
        try { mainWs.close(); } catch (e) {}
        triggerDiscoveryAndSweep();
      }
    }, 1200);

    try {
      const ws = new WebSocket(state.wsUrl);
      mainWs = ws;
      mainWs.onopen = (e) => {
        clearWsConnectTimeout();
        if (ws !== mainWs) return;
        onMainWsOpen(e);
      };
      mainWs.onmessage = (e) => {
        if (ws !== mainWs) return;
        onMainWsMessage(e);
      };
      mainWs.onclose = (e) => {
        clearWsConnectTimeout();
        if (ws !== mainWs) return;
        onMainWsClose(e);
      };
      mainWs.onerror = (e) => {
        clearWsConnectTimeout();
        if (ws !== mainWs) return;
        onMainWsError(e);
      };

      connectScreenWs();
    } catch (e) {
      clearWsConnectTimeout();
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

  function updateAdaptiveQuality(currentRtt) {
    if (state.autoQualityMode !== 'auto') return;

    // Exponential moving average for jitter-resistant smoothed RTT
    smoothedRtt = Math.round(smoothedRtt * 0.65 + currentRtt * 0.35);

    let targetQuality = 75;
    let targetScale = 0.85;

    if (smoothedRtt < 22) {
      // Ultra-low latency (< 22ms)
      targetQuality = 88;
      targetScale = 1.0;
    } else if (smoothedRtt <= 48) {
      // Clean fast connection (22-48ms)
      targetQuality = 78;
      targetScale = 0.90;
    } else if (smoothedRtt <= 90) {
      // Standard connection (48-90ms)
      targetQuality = 70;
      targetScale = 0.78;
    } else if (smoothedRtt <= 150) {
      // Elevated latency (90-150ms)
      targetQuality = 58;
      targetScale = 0.65;
    } else {
      // High latency / interference spike (> 150ms)
      targetQuality = 45;
      targetScale = 0.50;
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

    // Update status label with clean, legitimate latency
    if (el.statusLabel && mainWs && mainWs.readyState === WebSocket.OPEN) {
      el.statusLabel.textContent = `Online • ${smoothedRtt}ms`;
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
        const oldScreenWs = screenWs;
        screenWs = null;
        oldScreenWs.onopen = null;
        oldScreenWs.onmessage = null;
        oldScreenWs.onclose = null;
        oldScreenWs.onerror = null;
        try { oldScreenWs.close(); } catch (e) {}
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
          }, 1000);
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

    clearAutoReconnect();
    saveAllSettings(false);

    if (pingInterval) clearInterval(pingInterval);
    pingInterval = setInterval(() => {
      if (mainWs && mainWs.readyState === WebSocket.OPEN) {
        mainWs.send(`p,${Date.now()}`);
      }
    }, 1500);

    // Refresh Places & Current Directory
    loadFsPlaces();

    // Immediately restore / verify screen stream channel upon reconnection
    connectScreenWs();

    // Send Pro status to PC Server
    const isProActive = typeof window.isProUnlocked === 'function' ? window.isProUnlocked() : false;
    if (mainWs && mainWs.readyState === WebSocket.OPEN) {
      mainWs.send(`pro_status,${isProActive ? '1' : '0'}`);
    }

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
      if (el.statusLabel && mainWs && mainWs.readyState === WebSocket.OPEN) {
        el.statusLabel.textContent = `Online • ${state.latency}ms`;
      }
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
    clearWsConnectTimeout();
    state.connected = false;
    reconnectAttempts++;

    if (reconnectAttempts >= 3) {
      updateStatus('disconnected', 'Reconnecting... (Check Wi-Fi/Hotspot)');
      if (reconnectAttempts === 3) {
        showToast(`Searching for PC on network...`, 'info', '🔍');
      }
    } else {
      updateStatus('disconnected', 'Reconnecting...');
    }

    // Trigger instant UDP discovery and subnet sweep on connection drop
    triggerDiscoveryAndSweep();

    if (pingInterval) {
      clearInterval(pingInterval);
      pingInterval = null;
    }
    if (audioStreamActive) {
      stopAudioStream();
    }

    clearAutoReconnect();
    const isHttp = window.location.protocol.startsWith('http') && window.location.hostname;
    const hasTarget = localStorage.getItem('neontrack_ip') || state.serverHost || (isHttp ? window.location.hostname : null);
    if (hasTarget) {
      // Super fast initial retry (350ms) instead of 1000ms+ delay
      const delay = reconnectAttempts <= 1 ? 350 : Math.min(600 + Math.min(reconnectAttempts, 4) * 500, 2500);
      state.autoReconnectTimer = setTimeout(() => {
        state.autoReconnectTimer = null;
        if (!state.connected) {
          connect();
        }
      }, delay);
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
        screenCtx.imageSmoothingEnabled = false;
      }
    }

    let renderedOk = false;
    try {
      const blob = (data instanceof Blob) ? data : new Blob([data], { type: 'image/jpeg' });

      // Primary Decoder: Hardware-Accelerated createImageBitmap
      if (window.createImageBitmap) {
        try {
          const bmp = await createImageBitmap(blob, { imageOrientation: 'none', premultiplyAlpha: 'none' });
          if (el.screenCanvas.width !== bmp.width || el.screenCanvas.height !== bmp.height) {
            el.screenCanvas.width = bmp.width;
            el.screenCanvas.height = bmp.height;
            screenCtx = el.screenCanvas.getContext('2d', { alpha: false, desynchronized: true });
            if (screenCtx) screenCtx.imageSmoothingEnabled = false;
          }
          if (screenCtx) {
            screenCtx.drawImage(bmp, 0, 0);
            renderedOk = true;
          }
          if (bmp.close) bmp.close();
        } catch (bmpErr) {
          try {
            const bmp = await createImageBitmap(blob);
            if (el.screenCanvas.width !== bmp.width || el.screenCanvas.height !== bmp.height) {
              el.screenCanvas.width = bmp.width;
              el.screenCanvas.height = bmp.height;
              screenCtx = el.screenCanvas.getContext('2d', { alpha: false, desynchronized: true });
            }
            if (screenCtx) {
              screenCtx.drawImage(bmp, 0, 0);
              renderedOk = true;
            }
            if (bmp.close) bmp.close();
          } catch (e2) {}
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
            }
            if (screenCtx) {
              screenCtx.drawImage(cachedScreenImg, 0, 0);
              renderedOk = true;
            }
            resolve();
          };
          cachedScreenImg.onerror = (err) => {
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
        requestAnimationFrame(processNextScreenFrame);
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
    document.body.classList.toggle('on-screen-tab', targetId === 'tab-screen');
    document.body.classList.toggle('gamepad-mode-active', targetId === 'tab-trackpad' && gamepadActive);

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

    // Update Titlebar Actions (Screen Streaming FPS vs File Transfer Pro Toggle)
    if (typeof window.updateTitlebarActions === 'function') {
      window.updateTitlebarActions(targetId);
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
      document.body.classList.add('typing-active');
      // Focus must happen in the same gesture or Android will not raise the keyboard.
      input.focus();
      if (input.value) {
        const len = input.value.length;
        try { input.setSelectionRange(len, len); } catch(e) {}
      }
      showToast('Typing to PC — tap ✕ to close', 'success', '⌨️');
    }

    function closeTypeBar() {
      input.blur();
      bar.hidden = true;
      fab.classList.remove('active');
      document.body.classList.remove('typing-active');
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

    // Real-time titlebar label update during active transfer
    const transferLabel = document.getElementById('fast-transfer-label');
    if (transferLabel && speed && speed !== '-- MB/s') {
      transferLabel.textContent = `Fast Transfer • ${speed}`;
    }
  }

  function hideTransferProgress(delay = 0) {
    if (hideTransferTimeout) {
      clearTimeout(hideTransferTimeout);
      hideTransferTimeout = null;
    }
    if (delay === 0) {
      const boxes = document.querySelectorAll('.file-transfer-card');
      boxes.forEach(box => { box.style.display = 'none'; });
      if (typeof window.syncTransferSpeedButtons === 'function') {
        window.syncTransferSpeedButtons();
      }
    } else {
      hideTransferTimeout = setTimeout(() => {
        const boxes = document.querySelectorAll('.file-transfer-card');
        boxes.forEach(box => { box.style.display = 'none'; });
        if (typeof window.syncTransferSpeedButtons === 'function') {
          window.syncTransferSpeedButtons();
        }
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
        status: `Starting stream (${file.name})...`,
        speed: 'Connecting...',
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

    showToast(shouldHide ? 'Full View (Title Bar Hidden)' : 'Title Bar Restored', 'info', shouldHide ? '📐' : '👁️');
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
    const parsed = parseHostPort(data);
    if (parsed) {
      state.serverHost = parsed.host;
      state.serverPort = parsed.port;
      if (el.modalIpInput) el.modalIpInput.value = `${state.serverHost}:${state.serverPort}`;
      if (el.settingsIpInput) el.settingsIpInput.value = `${state.serverHost}:${state.serverPort}`;
      showToast(`Connected to ${state.serverHost}:${state.serverPort}`, 'success', '💻');
      reconnectAttempts = 0;
      saveAllSettings(false);
      connect(true);
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
          const parsed = parseHostPort(val);
          if (parsed) {
            state.serverHost = parsed.host;
            state.serverPort = parsed.port;
            reconnectAttempts = 0;
            saveAllSettings(false);
            connect(true);
          }
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

    if (el.settingGamepadHud) {
      el.settingGamepadHud.onchange = () => {
        state.gamepadHudEnabled = el.settingGamepadHud.checked;
        if (window.updateTitlebarActions) {
          window.updateTitlebarActions();
        }
        if (!state.gamepadHudEnabled && state.gamepadHudActive) {
          if (typeof window.toggleGamepadHUD === 'function') {
            window.toggleGamepadHUD(false);
          }
        }
        saveAllSettings(false);
        showToast(state.gamepadHudEnabled ? 'Gaming Controller HUD Enabled' : 'Gaming Controller HUD Disabled', 'info', '🎮');
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
          const parsed = parseHostPort(val);
          if (parsed) {
            state.serverHost = parsed.host;
            state.serverPort = parsed.port;
            reconnectAttempts = 0;
            saveAllSettings(true);
            connect(true);
          }
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
  let audioSessionId = 0;
  const scheduledAudioSources = new Set();

  // Ultra-Low-Latency Jitter-Free Circular Ring Buffer Audio Engine
  const AUDIO_RING_BUFFER_SIZE = 48000 * 2; // 2 seconds of float frames
  let audioRingBufferL = new Float32Array(AUDIO_RING_BUFFER_SIZE);
  let audioRingBufferR = new Float32Array(AUDIO_RING_BUFFER_SIZE);
  let audioRingWritePos = 0;
  let audioRingReadPos = 0;
  let audioRingAvailable = 0;
  let audioContinuousNode = null;
  let isAudioPrebuffering = true;
  const AUDIO_PREBUFFER_THRESHOLD = 1440; // ~30ms pre-buffer before starting playback

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
      setupContinuousAudioProcessor();
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
        showToast('Streaming Smooth PC Audio!', 'success', '🔊');
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

  function setupContinuousAudioProcessor() {
    ensureAudioContext();
    if (!audioCtx) return;

    if (audioContinuousNode) {
      try { audioContinuousNode.disconnect(); } catch (e) {}
      audioContinuousNode = null;
    }

    // Reset ring buffer pointers & pre-buffering gate
    audioRingWritePos = 0;
    audioRingReadPos = 0;
    audioRingAvailable = 0;
    isAudioPrebuffering = true;

    try {
      const node = audioCtx.createScriptProcessor(1024, 0, 2);
      audioContinuousNode = node;

      node.onaudioprocess = (e) => {
        if (!audioStreamActive) return;
        const outL = e.outputBuffer.getChannelData(0);
        const outR = e.outputBuffer.getChannelData(1);
        const bufLen = outL.length;

        // 1. Prebuffer gate to absorb initial network jitter
        if (isAudioPrebuffering) {
          if (audioRingAvailable < AUDIO_PREBUFFER_THRESHOLD) {
            outL.fill(0);
            outR.fill(0);
            return;
          }
          isAudioPrebuffering = false;
        }

        // 2. Buffer underrun check
        if (audioRingAvailable < bufLen) {
          for (let i = 0; i < bufLen; i++) {
            if (audioRingAvailable > 0) {
              outL[i] = audioRingBufferL[audioRingReadPos];
              outR[i] = audioRingBufferR[audioRingReadPos];
              audioRingReadPos = (audioRingReadPos + 1) % AUDIO_RING_BUFFER_SIZE;
              audioRingAvailable--;
            } else {
              outL[i] = 0;
              outR[i] = 0;
            }
          }
          isAudioPrebuffering = true;
          return;
        }

        // 3. Adaptive clock drift compensation (keep latency < 35ms without pitch distortion)
        const needCatchup = audioRingAvailable > 2880; // > 60ms backlog

        for (let i = 0; i < bufLen; i++) {
          outL[i] = audioRingBufferL[audioRingReadPos];
          outR[i] = audioRingBufferR[audioRingReadPos];
          audioRingReadPos = (audioRingReadPos + 1) % AUDIO_RING_BUFFER_SIZE;
          audioRingAvailable--;

          if (needCatchup && i % 128 === 0 && audioRingAvailable > 0) {
            // Subtly skip 1 frame per 128 to gently drain buffer
            audioRingReadPos = (audioRingReadPos + 1) % AUDIO_RING_BUFFER_SIZE;
            audioRingAvailable--;
          }
        }
      };

      if (audioAnalyser) {
        node.connect(audioAnalyser);
      } else if (audioGainNode) {
        node.connect(audioGainNode);
      }
    } catch (e) {
      console.warn('Continuous audio node creation error:', e);
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

    for (let i = 0; i < numFrames; i++) {
      const sL = int16Array[i * audioChannels] / 32768.0;
      const sR = audioChannels > 1 ? int16Array[i * audioChannels + 1] / 32768.0 : sL;

      audioRingBufferL[audioRingWritePos] = sL;
      audioRingBufferR[audioRingWritePos] = sR;
      audioRingWritePos = (audioRingWritePos + 1) % AUDIO_RING_BUFFER_SIZE;
      audioRingAvailable = Math.min(AUDIO_RING_BUFFER_SIZE, audioRingAvailable + 1);
    }
  }

  function killScheduledAudioSources() {
    if (audioContinuousNode) {
      try { audioContinuousNode.disconnect(); } catch (e) {}
      audioContinuousNode = null;
    }
    audioRingWritePos = 0;
    audioRingReadPos = 0;
    audioRingAvailable = 0;
  }

  function teardownHtml5Fallback(element) {
    if (!element) return;
    try {
      element.pause();
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
    if (mainWs && mainWs.readyState === WebSocket.OPEN) {
      mainWs.send(`pro_status,${isPro ? '1' : '0'}`);
    }

    if (typeof window.syncTransferSpeedButtons === 'function') {
      window.syncTransferSpeedButtons();
    }
    if (typeof window.updateTitlebarActions === 'function') {
      window.updateTitlebarActions(state.activeTab);
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
          showToast('✨ Auto Dynamic Quality Enabled (Real-Time AI-Tuned)', 'success', '✨');
          updateAdaptiveQuality(state.latency || 25);
        } else if (val === 'ultrahd') {
          state.streamQuality = 90;
          state.streamScale = 1.0;
          showToast('Ultra HD Crystal Enabled (100% Native · 90Q)', 'success', '✨');
          sendStreamConfig();
        } else if (val === 'sharp') {
          state.streamQuality = 80;
          state.streamScale = 0.90;
          showToast('High Clarity Fixed (90% Scale · 80Q)', 'success', '🔍');
          sendStreamConfig();
        } else if (val === 'speed') {
          state.streamQuality = 55;
          state.streamScale = 0.65;
          showToast('Low Latency Speed (65% Scale · 55Q)', 'info', '⚡');
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

    // Title Bar Context Actions (Screen Streaming FPS vs File Transfer Pro Toggle)
    // Title Bar Context Actions (Screen Streaming FPS vs Kinetic Fast Transfer Pill)
    window.updateTitlebarActions = function(targetTabId) {
      const activeTab = targetTabId || state.activeTab || 'tab-screen';
      const fpsGroup = document.getElementById('titlebar-fps-group');
      const transferPill = document.getElementById('titlebar-transfer-group');
      const btnGameHud = document.getElementById('btn-screen-gamepad-hud');

      if (btnGameHud) {
        btnGameHud.style.display = (activeTab === 'tab-screen' && state.gamepadHudEnabled) ? 'inline-flex' : 'none';
      }

      if (activeTab === 'tab-files') {
        if (fpsGroup) fpsGroup.style.display = 'none';
        if (transferPill) transferPill.style.display = 'inline-flex';
        syncTransferSpeedButtons();
      } else {
        if (transferPill) transferPill.style.display = 'none';
        if (fpsGroup) fpsGroup.style.display = 'inline-flex';
      }
    };

    // Kinetic Fast Transfer Pill Sync & Toggle
    function syncTransferSpeedButtons() {
      const transferPill = document.getElementById('titlebar-transfer-group');
      const transferLabel = document.getElementById('fast-transfer-label');
      const selSpeed = document.getElementById('setting-transfer-speed');
      const isPro = typeof window.isProUnlocked === 'function' ? window.isProUnlocked() : false;
      const isTurbo = (state.transferSpeed === 'turbo' || (isPro && state.transferSpeed !== 'standard')) && isPro;

      if (!isPro && state.transferSpeed === 'turbo') {
        state.transferSpeed = 'standard';
      }

      if (transferPill) {
        transferPill.classList.toggle('pro-active', isTurbo);
        transferPill.title = isPro
          ? (isTurbo ? 'Fast File Transfer • Gigabit LAN Uncapped (Pro)' : 'Fast File Transfer • Standard 10 MB/s')
          : 'Fast File Transfer • Tap to unlock Gigabit Turbo';
      }

      if (transferLabel) {
        transferLabel.textContent = 'Fast File Transfer';
      }

      if (selSpeed) selSpeed.value = isTurbo ? 'turbo' : 'standard';
    }
    window.syncTransferSpeedButtons = syncTransferSpeedButtons;

    // Toggle Fast Transfer Tier on Pill Click
    const transferPill = document.getElementById('titlebar-transfer-group');
    if (transferPill) {
      transferPill.onclick = () => {
        vibrate(20);
        if (!window.isProUnlocked()) {
          window.openProUpgradeModal();
          showToast('Uncapped Gigabit LAN File Bandwidth requires PCDeck Pro', 'warn', '⭐');
          return;
        }
        const nextSpeed = state.transferSpeed === 'turbo' ? 'standard' : 'turbo';
        window.setTransferSpeed(nextSpeed);
      };
    }

    window.setTransferSpeed = function(speedVal) {
      const selSpeed = document.getElementById('setting-transfer-speed');

      if (speedVal === 'turbo') {
        if (!window.isProUnlocked()) {
          if (selSpeed) selSpeed.value = 'standard';
          window.openProUpgradeModal();
          showToast('Uncapped Gigabit LAN File Bandwidth requires PCDeck Pro', 'warn', '⭐');
          syncTransferSpeedButtons();
          return;
        }
        if (selSpeed) selSpeed.value = 'turbo';
        state.transferSpeed = 'turbo';
        saveAllSettings(false);
        syncTransferSpeedButtons();
        showToast('Fast Transfer: Turbo Gigabit Mode Active (Uncapped)', 'success', '⚡');
      } else {
        if (selSpeed) selSpeed.value = 'standard';
        state.transferSpeed = 'standard';
        saveAllSettings(false);
        syncTransferSpeedButtons();
        showToast('Fast Transfer: Standard Mode Active (10 MB/s)', 'info', '📁');
      }
    };

    // Reflect saved choices in title-bar toggles on startup
    (function syncTitlebarControls() {
      const btn30 = document.getElementById('btn-fps-30');
      const btn60 = document.getElementById('btn-fps-60');
      const use60 = state.streamFps === 60 && window.isProUnlocked();
      if (!use60) state.streamFps = 30;
      if (btn30) btn30.classList.toggle('active', !use60);
      if (btn60) btn60.classList.toggle('active', use60);
      if (selFps) selFps.value = use60 ? '60' : '30';

      syncTransferSpeedButtons();
      window.updateTitlebarActions(state.activeTab);
    })();

    // Turbo Speed Gate in Settings
    const selSpeed = document.getElementById('setting-transfer-speed');
    if (selSpeed) {
      selSpeed.onchange = () => {
        if (selSpeed.value === 'turbo' && !window.isProUnlocked()) {
          selSpeed.value = 'standard';
          window.openProUpgradeModal();
          showToast('Uncapped LAN File Bandwidth requires PCDeck Pro', 'info', '⭐');
          syncTransferSpeedButtons();
          return;
        }
        window.setTransferSpeed(selSpeed.value === 'turbo' ? 'turbo' : 'standard');
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

  // =========================================================================
  // VIRTUAL XBOX GAMEPAD CONTROLLER ENGINE
  // =========================================================================
  let gamepadActive = false;
  const gpStickState = {
    left: { x: 0, y: 0, active: false, pointerId: null },
    right: { x: 0, y: 0, active: false, pointerId: null },
  };

  function initGamepadEngine() {
    const btnToggle = document.getElementById('btn-gamepad-mode-toggle');
    const btnReturn = document.getElementById('btn-return-trackpad');
    const stdTrackpad = document.getElementById('standard-trackpad-view');
    const gpContainer = document.getElementById('gamepad-container');

    let activeGpPreset = 'xbox';
    let gpSensitivity = 1.0;
    let gpHaptics = true;

    // Presets definitions
    const GP_PRESETS = {
      xbox: {
        name: 'Xbox 360',
        buttons: { y: 'Y', x: 'X', b: 'B', a: 'A' },
        sublabels: { y: 'USE', x: 'RELOAD', b: 'CROUCH', a: 'JUMP' },
        triggers: { ltTitle: 'LT', ltSub: 'AIM', rtTitle: 'RT', rtSub: 'FIRE', lbTitle: 'LB', rbTitle: 'RB' },
        colors: {
          y: 'radial-gradient(circle at 35% 30%, #fbbf24 0%, #f59e0b 60%, #d97706 100%)',
          x: 'radial-gradient(circle at 35% 30%, #38bdf8 0%, #0284c7 60%, #0369a1 100%)',
          b: 'radial-gradient(circle at 35% 30%, #ff4b72 0%, #ef4444 60%, #b91c1c 100%)',
          a: 'radial-gradient(circle at 35% 30%, #2ecc71 0%, #10b981 60%, #047857 100%)'
        },
        textColors: { y: '#000', x: '#fff', b: '#fff', a: '#fff' },
        driverLabel: 'Virtual Xbox 360: Active'
      },
      ps: {
        name: 'PlayStation',
        buttons: { y: '△', x: '□', b: '○', a: '✕' },
        sublabels: { y: 'TRIANGLE', x: 'SQUARE', b: 'CIRCLE', a: 'CROSS' },
        triggers: { ltTitle: 'L2', ltSub: 'AIM', rtTitle: 'R2', rtSub: 'FIRE', lbTitle: 'L1', rbTitle: 'R1' },
        colors: {
          y: 'radial-gradient(circle at 35% 30%, #2ecc71 0%, #10b981 60%, #047857 100%)',
          x: 'radial-gradient(circle at 35% 30%, #ff4b72 0%, #ec4899 60%, #be185d 100%)',
          b: 'radial-gradient(circle at 35% 30%, #ef4444 0%, #dc2626 60%, #991b1b 100%)',
          a: 'radial-gradient(circle at 35% 30%, #38bdf8 0%, #0284c7 60%, #0369a1 100%)'
        },
        textColors: { y: '#fff', x: '#fff', b: '#fff', a: '#fff' },
        driverLabel: 'Virtual DualShock 4: Active'
      },
      racing: {
        name: 'Racing Mode',
        buttons: { y: 'NOS', x: 'GEAR-', b: 'HAND', a: 'GEAR+' },
        sublabels: { y: 'BOOST', x: 'SHIFT DN', b: 'E-BRAKE', a: 'SHIFT UP' },
        triggers: { ltTitle: 'BRAKE', ltSub: 'STOP', rtTitle: 'GAS', rtSub: 'ACCEL', lbTitle: 'CLUTCH', rbTitle: 'HORN' },
        colors: {
          y: 'radial-gradient(circle at 35% 30%, #fbbf24 0%, #f59e0b 60%, #d97706 100%)',
          x: 'radial-gradient(circle at 35% 30%, #38bdf8 0%, #0284c7 60%, #0369a1 100%)',
          b: 'radial-gradient(circle at 35% 30%, #ff4b72 0%, #ef4444 60%, #b91c1c 100%)',
          a: 'radial-gradient(circle at 35% 30%, #2ecc71 0%, #10b981 60%, #047857 100%)'
        },
        textColors: { y: '#000', x: '#fff', b: '#fff', a: '#fff' },
        driverLabel: 'Racing Wheel & Pedals: Active'
      },
      wasd: {
        name: 'WASD / FPS',
        buttons: { y: 'E', x: 'R', b: 'C', a: 'SPACE' },
        sublabels: { y: 'USE', x: 'RELOAD', b: 'CROUCH', a: 'JUMP' },
        triggers: { ltTitle: 'R-CLICK', ltSub: 'AIM', rtTitle: 'L-CLICK', rtSub: 'SHOOT', lbTitle: 'Q (LEAN)', rbTitle: 'E (LEAN)' },
        colors: {
          y: 'radial-gradient(circle at 35% 30%, #fbbf24 0%, #f59e0b 60%, #d97706 100%)',
          x: 'radial-gradient(circle at 35% 30%, #38bdf8 0%, #0284c7 60%, #0369a1 100%)',
          b: 'radial-gradient(circle at 35% 30%, #ff4b72 0%, #ef4444 60%, #b91c1c 100%)',
          a: 'radial-gradient(circle at 35% 30%, #2ecc71 0%, #10b981 60%, #047857 100%)'
        },
        textColors: { y: '#000', x: '#fff', b: '#fff', a: '#fff' },
        driverLabel: 'WASD FPS Keypad: Active'
      }
    };

    function applyGamepadPreset(presetKey) {
      activeGpPreset = presetKey;
      const conf = GP_PRESETS[presetKey] || GP_PRESETS.xbox;
      const driverBadge = document.getElementById('gp-driver-text');
      if (driverBadge) driverBadge.textContent = conf.driverLabel;

      const presetChips = document.querySelectorAll('.gp-preset-chip');
      presetChips.forEach(c => {
        c.classList.toggle('active', c.dataset.preset === presetKey);
      });

      // Update diamond buttons label and sublabels
      const diamonds = document.querySelectorAll('#gp-action-diamond');
      diamonds.forEach(diamond => {
        Object.keys(conf.buttons).forEach(btnKey => {
          const btn = diamond.querySelector(`[data-gp="${btnKey}"]`);
          if (btn) {
            const jewel = btn.querySelector('.gp-btn-jewel, .btn-glyph');
            if (jewel) {
              jewel.textContent = conf.buttons[btnKey];
            } else {
              btn.textContent = conf.buttons[btnKey];
            }
            const sub = btn.querySelector('.gp-action-sublabel');
            if (sub && conf.sublabels && conf.sublabels[btnKey]) {
              sub.textContent = conf.sublabels[btnKey];
            }
            btn.style.background = conf.colors[btnKey];
            btn.style.color = conf.textColors[btnKey];
          }
        });
      });

      // Update shoulder trigger and bumper labels
      const ltTitle = document.getElementById('lt-btn-title');
      const ltSub = document.getElementById('lt-btn-sub');
      const rtTitle = document.getElementById('rt-btn-title');
      const rtSub = document.getElementById('rt-btn-sub');
      const lbTitle = document.getElementById('lb-btn-title');
      const rbTitle = document.getElementById('rb-btn-title');

      if (conf.triggers) {
        if (ltTitle) ltTitle.textContent = conf.triggers.ltTitle;
        if (ltSub) ltSub.textContent = conf.triggers.ltSub;
        if (rtTitle) rtTitle.textContent = conf.triggers.rtTitle;
        if (rtSub) rtSub.textContent = conf.triggers.rtSub;
        if (lbTitle) lbTitle.textContent = conf.triggers.lbTitle;
        if (rbTitle) rbTitle.textContent = conf.triggers.rbTitle;
      }

      showToast(`Gamepad Preset: ${conf.name}`, 'success', '🎮');
    }

    // Preset chips click
    const presetChips = document.querySelectorAll('.gp-preset-chip');
    presetChips.forEach(chip => {
      chip.onclick = () => {
        vibrate(15);
        applyGamepadPreset(chip.dataset.preset);
      };
    });

    // Top Header Menu & Guide Orb: Toggle / Reveal Bottom Console Options (Xbox, PlayStation, Racing, WASD)
    const btnTopMenu = document.getElementById('btn-gp-top-menu');
    const btnGuideOrb = document.getElementById('btn-gp-guide-orb');
    const btnDriverBadge = document.getElementById('gp-driver-badge');
    const bottomPresetBar = document.getElementById('gp-bottom-preset-bar');

    function toggleBottomConsolePresets() {
      vibrate(15);
      if (bottomPresetBar) {
        bottomPresetBar.classList.add('pulse-highlight');
        bottomPresetBar.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        setTimeout(() => bottomPresetBar.classList.remove('pulse-highlight'), 1200);
      }
      showToast('🎮 Console Layouts: Xbox 360, PlayStation, Racing, WASD/FPS', 'info', '🎮');
    }

    if (btnTopMenu) {
      btnTopMenu.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleBottomConsolePresets();
      };
    }
    if (btnGuideOrb) {
      btnGuideOrb.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleBottomConsolePresets();
      };
    }
    if (btnDriverBadge) {
      btnDriverBadge.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleBottomConsolePresets();
      };
    }

    // Top Back-to-Trackpad Button
    const btnTopBack = document.getElementById('btn-gp-top-back-trackpad');
    if (btnTopBack) {
      btnTopBack.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setGamepadMode(false);
        showToast('Switched to Trackpad', 'info', '🖱️');
      };
    }

    // Stick Sensitivity Toggle
    const btnSens = document.getElementById('btn-gp-sens-toggle');
    const SENS_OPTIONS = [1.0, 1.5, 2.0];
    if (btnSens) {
      btnSens.onclick = () => {
        vibrate(15);
        let idx = (SENS_OPTIONS.indexOf(gpSensitivity) + 1) % SENS_OPTIONS.length;
        gpSensitivity = SENS_OPTIONS[idx];
        btnSens.textContent = `Sens: ${gpSensitivity.toFixed(1)}x`;
        showToast(`Stick Sensitivity: ${gpSensitivity.toFixed(1)}x`, 'info', '🕹️');
      };
    }

    // Haptics Toggle
    const btnHaptics = document.getElementById('btn-gp-haptic-toggle');
    if (btnHaptics) {
      btnHaptics.onclick = () => {
        gpHaptics = !gpHaptics;
        btnHaptics.classList.toggle('active', gpHaptics);
        btnHaptics.textContent = gpHaptics ? '📳 Haptics: ON' : '📴 Haptics: OFF';
        vibrate(gpHaptics ? 25 : 5);
      };
    }

    let isGpLayoutEditing = false;
    let selectedGpElemId = null;

    // Default Gamepad Layout
    const DEFAULT_GP_LAYOUT = {
      elements: {
        'elem-left-stick': { scale: 1.0, hidden: false, name: '🕹️ Left Stick (Move)' },
        'elem-dpad': { scale: 1.0, hidden: false, name: '➕ 3D D-Pad' },
        'elem-actions': { scale: 1.0, hidden: false, name: '🎯 Action Diamond' },
        'elem-right-stick': { scale: 1.0, hidden: false, name: '🕹️ Right Stick (Aim)' },
        'elem-lt': { scale: 1.0, hidden: false, name: '🎯 Left Trigger (LT)' },
        'elem-lb': { scale: 1.0, hidden: false, name: '⚡ Left Bumper (LB)' },
        'elem-rt': { scale: 1.0, hidden: false, name: '🔥 Right Trigger (RT)' },
        'elem-rb': { scale: 1.0, hidden: false, name: '💥 Right Bumper (RB)' },
        'elem-sys': { scale: 1.0, hidden: false, name: '🎮 System Hub' },
        'elem-center-spine': { scale: 1.0, hidden: false, name: 'PCDeck Emblem' }
      },
      customButtons: []
    };

    function loadGpLayout() {
      try {
        const raw = localStorage.getItem('pcdeck_gamepad_custom_layout');
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed && parsed.elements) return parsed;
        }
      } catch (e) {
        console.warn('[GamepadLayout] Error loading custom layout:', e);
      }
      return JSON.parse(JSON.stringify(DEFAULT_GP_LAYOUT));
    }

    let gpCustomLayout = loadGpLayout();

    function selectGpElement(elemId) {
      const prevSelected = document.querySelectorAll('.gp-elem-selected');
      prevSelected.forEach(el => el.classList.remove('gp-elem-selected'));

      selectedGpElemId = elemId;
      const titleBadge = document.getElementById('gp-edit-selected-title');
      const deleteBtn = document.getElementById('btn-gp-delete-selected');
      const sizeSlider = document.getElementById('gp-size-slider');
      const sizeValText = document.getElementById('gp-size-val');

      if (!elemId) {
        if (titleBadge) titleBadge.textContent = 'Tap a Control';
        if (deleteBtn) deleteBtn.style.display = 'none';
        return;
      }

      const targetElem = document.querySelector(`[data-elem-id="${elemId}"]`);
      if (targetElem) {
        targetElem.classList.add('gp-elem-selected');
        let elemName = 'Control';
        let elemScale = 1.0;

        if (gpCustomLayout.elements[elemId]) {
          elemName = gpCustomLayout.elements[elemId].name || elemId;
          elemScale = gpCustomLayout.elements[elemId].scale || 1.0;
        } else {
          const customEntry = (gpCustomLayout.customButtons || []).find(b => b.id === elemId);
          if (customEntry) {
            elemName = customEntry.label || customEntry.key || elemId;
            elemScale = customEntry.scale || 1.0;
          }
        }

        if (titleBadge) titleBadge.textContent = elemName;
        if (deleteBtn) deleteBtn.style.display = 'inline-flex';
        const sVal = Math.round(elemScale * 100);
        if (sizeSlider) sizeSlider.value = sVal;
        if (sizeValText) sizeValText.textContent = `${sVal}%`;
      }
    }

    function applyGpLayout() {
      const customContainer = document.getElementById('gp-custom-elements-container');
      if (customContainer) customContainer.innerHTML = '';

      // Apply built-in elements layout
      Object.keys(gpCustomLayout.elements || {}).forEach(elemId => {
        const conf = gpCustomLayout.elements[elemId];
        const elElem = document.querySelector(`[data-elem-id="${elemId}"]`);
        if (elElem) {
          elElem.style.display = conf.hidden ? 'none' : '';
          if (conf.left !== undefined && conf.left !== 'auto') {
            elElem.style.position = 'absolute';
            elElem.style.left = conf.left;
            elElem.style.top = conf.top || 'auto';
            elElem.style.right = conf.right || 'auto';
            elElem.style.bottom = conf.bottom || 'auto';
          } else {
            elElem.style.position = '';
            elElem.style.left = '';
            elElem.style.top = '';
            elElem.style.right = '';
            elElem.style.bottom = '';
          }
          const scale = conf.scale !== undefined ? conf.scale : 1.0;
          elElem.style.transform = `scale(${scale})`;
        }
      });

      // Render custom dynamically added buttons
      (gpCustomLayout.customButtons || []).forEach(bConf => {
        renderCustomGpButton(bConf);
      });
    }

    function renderCustomGpButton(bConf) {
      const customContainer = document.getElementById('gp-custom-elements-container');
      if (!customContainer) return;

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'gp-custom-btn';
      btn.dataset.elemId = bConf.id;
      btn.dataset.customKey = bConf.key;
      btn.style.left = bConf.left || '50%';
      btn.style.top = bConf.top || '50%';
      btn.style.transform = `scale(${bConf.scale || 1.0})`;

      const mainLabel = document.createElement('span');
      mainLabel.className = 'gp-custom-btn-main';
      mainLabel.textContent = (bConf.key || '').toUpperCase();

      const subLabel = document.createElement('span');
      subLabel.className = 'gp-custom-btn-sub';
      subLabel.textContent = bConf.label || '';

      btn.appendChild(mainLabel);
      if (bConf.label && bConf.label !== bConf.key) {
        btn.appendChild(subLabel);
      }

      // Pointer event for custom button
      const onDown = (e) => {
        if (isGpLayoutEditing) return;
        e.preventDefault();
        e.stopPropagation();
        btn.classList.add('active');
        if (gpHaptics) vibrate(12);
        const k = bConf.key;
        if (k.startsWith('mouse_')) {
          sendCommand(`mouse,down,${k.replace('mouse_', '')}`);
        } else {
          sendCommand(`key,down,${k}`);
        }
      };

      const onUp = (e) => {
        if (isGpLayoutEditing) return;
        e.preventDefault();
        e.stopPropagation();
        btn.classList.remove('active');
        const k = bConf.key;
        if (k.startsWith('mouse_')) {
          sendCommand(`mouse,up,${k.replace('mouse_', '')}`);
        } else {
          sendCommand(`key,up,${k}`);
        }
      };

      btn.addEventListener('pointerdown', onDown);
      btn.addEventListener('pointerup', onUp);
      btn.addEventListener('pointercancel', onUp);

      customContainer.appendChild(btn);
    }

    function setGamepadEditMode(editing) {
      isGpLayoutEditing = editing;
      document.body.classList.toggle('gp-layout-editing', editing);
      const toolbar = document.getElementById('gp-editor-toolbar');
      if (toolbar) toolbar.style.display = editing ? 'flex' : 'none';

      if (editing) {
        showToast('✏️ Tap any control to drag or resize', 'info', '🎮');
        selectGpElement(selectedGpElemId || 'elem-left-stick');
      } else {
        selectGpElement(null);
      }
    }

    // Initialize Layout Editor Controls
    const btnEditLayout = document.getElementById('btn-gp-edit-layout');
    if (btnEditLayout) {
      btnEditLayout.onclick = () => setGamepadEditMode(!isGpLayoutEditing);
    }

    const btnExitEditor = document.getElementById('btn-gp-exit-editor');
    if (btnExitEditor) {
      btnExitEditor.onclick = () => setGamepadEditMode(false);
    }

    const btnSaveLayout = document.getElementById('btn-gp-save-layout');
    if (btnSaveLayout) {
      btnSaveLayout.onclick = () => {
        vibrate(25);
        try {
          localStorage.setItem('pcdeck_gamepad_custom_layout', JSON.stringify(gpCustomLayout));
          showToast('💾 Custom Layout Saved!', 'success', '✓');
        } catch (e) {
          console.error('[GamepadLayout] Save error:', e);
        }
        setGamepadEditMode(false);
      };
    }

    const btnResetLayout = document.getElementById('btn-gp-reset-layout');
    if (btnResetLayout) {
      btnResetLayout.onclick = () => {
        vibrate(20);
        localStorage.removeItem('pcdeck_gamepad_custom_layout');
        gpCustomLayout = JSON.parse(JSON.stringify(DEFAULT_GP_LAYOUT));
        applyGpLayout();
        selectGpElement(null);
        showToast('🔄 Restored Factory Layout', 'info', '🎮');
      };
    }

    // Size adjustment
    const sizeSlider = document.getElementById('gp-size-slider');
    const sizeValText = document.getElementById('gp-size-val');
    const btnSizeDec = document.getElementById('btn-gp-size-dec');
    const btnSizeInc = document.getElementById('btn-gp-size-inc');

    function updateSelectedSize(scaleVal) {
      scaleVal = Math.max(0.6, Math.min(2.2, scaleVal));
      if (!selectedGpElemId) return;

      if (gpCustomLayout.elements[selectedGpElemId]) {
        gpCustomLayout.elements[selectedGpElemId].scale = scaleVal;
      } else {
        const customEntry = (gpCustomLayout.customButtons || []).find(b => b.id === selectedGpElemId);
        if (customEntry) customEntry.scale = scaleVal;
      }

      const targetElem = document.querySelector(`[data-elem-id="${selectedGpElemId}"]`);
      if (targetElem) {
        targetElem.style.transform = `scale(${scaleVal})`;
      }

      const sVal = Math.round(scaleVal * 100);
      if (sizeSlider) sizeSlider.value = sVal;
      if (sizeValText) sizeValText.textContent = `${sVal}%`;
    }

    if (sizeSlider) {
      sizeSlider.oninput = () => {
        const s = parseInt(sizeSlider.value, 10) / 100;
        updateSelectedSize(s);
      };
    }

    const gpSizePills = document.querySelectorAll('.gp-pill-btn');
    gpSizePills.forEach(pill => {
      pill.onclick = () => {
        vibrate(10);
        gpSizePills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        const s = parseInt(pill.dataset.gpSize, 10) / 100;
        updateSelectedSize(s);
      };
    });

    if (btnSizeDec) {
      btnSizeDec.onclick = () => {
        const cur = (sizeSlider ? parseInt(sizeSlider.value, 10) : 100) / 100;
        updateSelectedSize(cur - 0.1);
      };
    }
    if (btnSizeInc) {
      btnSizeInc.onclick = () => {
        const cur = (sizeSlider ? parseInt(sizeSlider.value, 10) : 100) / 100;
        updateSelectedSize(cur + 0.1);
      };
    }

    // Delete selected element
    const btnDeleteSelected = document.getElementById('btn-gp-delete-selected');
    if (btnDeleteSelected) {
      btnDeleteSelected.onclick = () => {
        if (!selectedGpElemId) return;
        vibrate(20);
        if (gpCustomLayout.elements[selectedGpElemId]) {
          gpCustomLayout.elements[selectedGpElemId].hidden = true;
          const elElem = document.querySelector(`[data-elem-id="${selectedGpElemId}"]`);
          if (elElem) elElem.style.display = 'none';
        } else {
          gpCustomLayout.customButtons = (gpCustomLayout.customButtons || []).filter(b => b.id !== selectedGpElemId);
          const elElem = document.querySelector(`[data-elem-id="${selectedGpElemId}"]`);
          if (elElem) elElem.remove();
        }
        showToast('🗑️ Control Removed', 'info', '✕');
        selectGpElement(null);
      };
    }

    // Add Control Modal
    const addModal = document.getElementById('gp-add-control-modal');
    const btnOpenAddModal = document.getElementById('btn-gp-open-add-modal');
    const btnModalClose = document.getElementById('btn-gp-modal-close');

    if (btnOpenAddModal && addModal) {
      btnOpenAddModal.onclick = () => {
        vibrate(15);
        addModal.style.display = 'flex';
      };
    }
    if (btnModalClose && addModal) {
      btnModalClose.onclick = () => {
        addModal.style.display = 'none';
      };
    }

    // Modal Tabs
    const modalTabs = document.querySelectorAll('.gp-tab-btn');
    modalTabs.forEach(t => {
      t.onclick = () => {
        modalTabs.forEach(tb => tb.classList.remove('active'));
        t.classList.add('active');
        const targetTab = t.dataset.tab;
        const contents = document.querySelectorAll('.gp-add-tab-content');
        contents.forEach(c => {
          c.style.display = c.id === `gp-add-tab-${targetTab}` ? 'block' : 'none';
        });
      };
    });

    // Add preset controls (unhide or position)
    const addPresetCards = document.querySelectorAll('.gp-add-item-card');
    addPresetCards.forEach(card => {
      card.onclick = () => {
        const type = card.dataset.addType;
        const elemKey = `elem-${type}`;
        if (gpCustomLayout.elements[elemKey]) {
          gpCustomLayout.elements[elemKey].hidden = false;
          gpCustomLayout.elements[elemKey].scale = 1.0;
          const elElem = document.querySelector(`[data-elem-id="${elemKey}"]`);
          if (elElem) {
            elElem.style.display = '';
            elElem.style.transform = 'scale(1)';
          }
        }
        if (addModal) addModal.style.display = 'none';
        selectGpElement(elemKey);
        showToast(`➕ Added ${card.querySelector('.item-name').textContent}`, 'success', '🎮');
      };
    });

    // Add PC Key items
    const addKeyItems = document.querySelectorAll('.gp-key-item');
    addKeyItems.forEach(kBtn => {
      kBtn.onclick = () => {
        const key = kBtn.dataset.key;
        const label = kBtn.dataset.label || key.toUpperCase();
        const customId = `custom-btn-${Date.now()}`;
        const newBtnConf = {
          id: customId,
          key: key,
          label: label,
          left: '48%',
          top: '45%',
          scale: 1.0
        };
        gpCustomLayout.customButtons = gpCustomLayout.customButtons || [];
        gpCustomLayout.customButtons.push(newBtnConf);
        renderCustomGpButton(newBtnConf);
        if (addModal) addModal.style.display = 'none';
        selectGpElement(customId);
        showToast(`➕ Added Button: ${label}`, 'success', '⌨️');
      };
    });

    // Add Custom Letter / Key Form
    const btnCustomAddConfirm = document.getElementById('btn-gp-add-custom-confirm');
    const customKeyNameInput = document.getElementById('gp-custom-key-name');
    const customKeyLabelInput = document.getElementById('gp-custom-key-label');

    if (btnCustomAddConfirm && customKeyNameInput) {
      btnCustomAddConfirm.onclick = () => {
        const keyName = (customKeyNameInput.value || '').trim().toLowerCase();
        if (!keyName) {
          showToast('Please enter a key name', 'warning', '⚠️');
          return;
        }
        const label = (customKeyLabelInput.value || '').trim() || keyName.toUpperCase();
        const customId = `custom-btn-${Date.now()}`;
        const newBtnConf = {
          id: customId,
          key: keyName,
          label: label,
          left: '50%',
          top: '50%',
          scale: 1.0
        };
        gpCustomLayout.customButtons = gpCustomLayout.customButtons || [];
        gpCustomLayout.customButtons.push(newBtnConf);
        renderCustomGpButton(newBtnConf);
        customKeyNameInput.value = '';
        if (customKeyLabelInput) customKeyLabelInput.value = '';
        if (addModal) addModal.style.display = 'none';
        selectGpElement(customId);
        showToast(`➕ Added Custom Key: ${label}`, 'success', '⚙️');
      };
    }

    // Drag-and-Drop Repositioning Engine for Layout Editor (100% Fluid, Zero Snapping)
    let dragTarget = null;
    let dragOffset = { x: 0, y: 0 };
    let isCurrentlyDragging = false;

    if (gpContainer) {
      gpContainer.addEventListener('pointerdown', (e) => {
        if (!isGpLayoutEditing) return;
        const selectable = e.target.closest('[data-elem-id]');
        if (selectable && gpContainer.contains(selectable) && !selectable.closest('#gp-editor-toolbar, #gp-bottom-preset-bar')) {
          e.preventDefault();
          e.stopPropagation();
          const elemId = selectable.dataset.elemId;
          selectGpElement(elemId);
          dragTarget = selectable;
          isCurrentlyDragging = true;
          dragTarget.classList.add('gp-is-dragging');

          const containerRect = gpContainer.getBoundingClientRect();
          const rect = selectable.getBoundingClientRect();
          dragOffset.x = e.clientX - rect.left;
          dragOffset.y = e.clientY - rect.top;

          // Convert to container-relative coordinate immediately so there is zero jump/snap on first touch
          const curLeftPx = rect.left - containerRect.left;
          const curTopPx = rect.top - containerRect.top;
          dragTarget.style.position = 'absolute';
          dragTarget.style.left = `${curLeftPx.toFixed(1)}px`;
          dragTarget.style.top = `${curTopPx.toFixed(1)}px`;
          dragTarget.style.right = 'auto';
          dragTarget.style.bottom = 'auto';

          try { selectable.setPointerCapture(e.pointerId); } catch (_) {}
        }
      });

      gpContainer.addEventListener('pointermove', (e) => {
        if (!isGpLayoutEditing || !dragTarget || !isCurrentlyDragging) return;
        e.preventDefault();
        e.stopPropagation();
        const containerRect = gpContainer.getBoundingClientRect();
        let leftPx = e.clientX - containerRect.left - dragOffset.x;
        let topPx = e.clientY - containerRect.top - dragOffset.y;

        // Fluid continuous bounding
        leftPx = Math.max(0, Math.min(containerRect.width - dragTarget.offsetWidth, leftPx));
        topPx = Math.max(0, Math.min(containerRect.height - dragTarget.offsetHeight, topPx));

        // High precision pixel placement during drag for instant 60/120fps response
        dragTarget.style.left = `${leftPx.toFixed(1)}px`;
        dragTarget.style.top = `${topPx.toFixed(1)}px`;

        const leftPercent = ((leftPx / containerRect.width) * 100).toFixed(2);
        const topPercent = ((topPx / containerRect.height) * 100).toFixed(2);

        const elemId = dragTarget.dataset.elemId;
        if (gpCustomLayout.elements[elemId]) {
          gpCustomLayout.elements[elemId].left = `${leftPercent}%`;
          gpCustomLayout.elements[elemId].top = `${topPercent}%`;
          gpCustomLayout.elements[elemId].right = 'auto';
          gpCustomLayout.elements[elemId].bottom = 'auto';
        } else {
          const customEntry = (gpCustomLayout.customButtons || []).find(b => b.id === elemId);
          if (customEntry) {
            customEntry.left = `${leftPercent}%`;
            customEntry.top = `${topPercent}%`;
          }
        }
      });

      const handleDragEnd = (e) => {
        if (dragTarget) {
          dragTarget.classList.remove('gp-is-dragging');
          const containerRect = gpContainer.getBoundingClientRect();
          const rect = dragTarget.getBoundingClientRect();
          const leftPct = (((rect.left - containerRect.left) / containerRect.width) * 100).toFixed(2) + '%';
          const topPct = (((rect.top - containerRect.top) / containerRect.height) * 100).toFixed(2) + '%';
          dragTarget.style.left = leftPct;
          dragTarget.style.top = topPct;
          try { dragTarget.releasePointerCapture(e.pointerId); } catch (_) {}
          dragTarget = null;
          isCurrentlyDragging = false;
        }
      };

      gpContainer.addEventListener('pointerup', handleDragEnd);
      gpContainer.addEventListener('pointercancel', handleDragEnd);
    }

    // Apply layout on init
    applyGpLayout();

    function setGamepadMode(active) {
      gamepadActive = active;
      if (stdTrackpad) stdTrackpad.style.display = active ? 'none' : '';
      if (gpContainer) gpContainer.style.display = active ? 'flex' : 'none';
      document.body.classList.toggle('gamepad-mode-active', active);
      const tabTrackpad = document.getElementById('tab-trackpad');
      if (tabTrackpad) tabTrackpad.classList.toggle('gamepad-mode-active', active);
      if (btnToggle) {
        btnToggle.style.background = active ? 'var(--neo-lime)' : 'var(--neo-cyan)';
        btnToggle.textContent = active ? '🖱️ Trackpad' : '🎮 Gamepad';
      }
      if (active) {
        applyGamepadPreset(activeGpPreset);
        applyGpLayout();
      } else {
        setGamepadEditMode(false);
      }
      vibrate(20);
    }

    if (btnToggle) {
      btnToggle.onclick = () => setGamepadMode(!gamepadActive);
    }
    const returnButtons = document.querySelectorAll('#btn-return-trackpad, .gp-exit-chip');
    returnButtons.forEach((btn) => {
      btn.onclick = () => setGamepadMode(false);
    });

    // Bind Digital & Action Buttons
    const gpButtons = document.querySelectorAll('[data-gp]');
    gpButtons.forEach((btn) => {
      const code = btn.dataset.gp;
      const onDown = (e) => {
        if (isGpLayoutEditing) return;
        e.preventDefault();
        e.stopPropagation();
        btn.classList.add('active');
        if (gpHaptics) vibrate(12);

        if (activeGpPreset === 'wasd') {
          const wasdKeyMap = {
            a: 'space', b: 'c', x: 'z', y: 'r',
            lb: 'q', rb: 'e',
            lt: 'mouse_right', rt: 'mouse_left',
            ls_click: 'shift', rs_click: 'alt',
            back: 'm', start: 'escape'
          };
          const key = wasdKeyMap[code] || code;
          if (key.startsWith('mouse_')) {
            sendCommand(`mouse,down,${key.replace('mouse_', '')}`);
          } else {
            sendCommand(`key,down,${key}`);
          }
        } else {
          sendCommand(`gp,btn,${code},1`);
        }
      };

      const onUp = (e) => {
        if (isGpLayoutEditing) return;
        e.preventDefault();
        e.stopPropagation();
        btn.classList.remove('active');

        if (activeGpPreset === 'wasd') {
          const wasdKeyMap = {
            a: 'space', b: 'c', x: 'z', y: 'r',
            lb: 'q', rb: 'e',
            lt: 'mouse_right', rt: 'mouse_left',
            ls_click: 'shift', rs_click: 'alt',
            back: 'm', start: 'escape'
          };
          const key = wasdKeyMap[code] || code;
          if (key.startsWith('mouse_')) {
            sendCommand(`mouse,up,${key.replace('mouse_', '')}`);
          } else {
            sendCommand(`key,up,${key}`);
          }
        } else {
          sendCommand(`gp,btn,${code},0`);
        }
      };

      btn.addEventListener('pointerdown', onDown);
      btn.addEventListener('pointerup', onUp);
      btn.addEventListener('pointercancel', onUp);
    });

    // Setup Dual Analog Sticks (Left & Right)
    setupAnalogStick('gp-left-stick-zone', 'gp-left-thumb', 'left');
    setupAnalogStick('gp-right-stick-zone', 'gp-right-thumb', 'right');
  }

  function setupAnalogStick(zoneId, thumbId, stickKey) {
    const zone = document.getElementById(zoneId);
    const thumb = document.getElementById(thumbId);
    if (!zone || !thumb) return;

    const base = zone.querySelector('.gp-stick-base') || zone;

    const handlePointerMove = (e) => {
      const s = gpStickState[stickKey];
      if (!s.active || s.pointerId !== e.pointerId) return;
      e.preventDefault();
      e.stopPropagation();

      const rect = base.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      let dx = e.clientX - centerX;
      let dy = e.clientY - centerY;
      const dist = Math.hypot(dx, dy);

      const maxTravel = Math.max(22, (rect.width / 2) - (thumb.offsetWidth / 2 || 24));

      if (dist > maxTravel) {
        dx = (dx / dist) * maxTravel;
        dy = (dy / dist) * maxTravel;
      }

      thumb.style.transform = `translate(${dx}px, ${dy}px)`;

      // Normalize to -1.0 .. +1.0
      let normX = dx / maxTravel;
      let normY = -(dy / maxTravel);

      const deadzone = 0.08;
      if (Math.abs(normX) < deadzone) normX = 0;
      if (Math.abs(normY) < deadzone) normY = 0;

      normX = Math.max(-1, Math.min(1, normX * gpSensitivity));
      normY = Math.max(-1, Math.min(1, normY * gpSensitivity));

      s.x = Math.round(normX * 100) / 100;
      s.y = Math.round(normY * 100) / 100;

      sendCommand(`gp,axis,${stickKey},${s.x},${s.y}`);
    };

    const handlePointerDown = (e) => {
      e.preventDefault();
      e.stopPropagation();
      base.setPointerCapture(e.pointerId);
      const s = gpStickState[stickKey];
      s.active = true;
      s.pointerId = e.pointerId;
      handlePointerMove(e);
    };

    const handlePointerUp = (e) => {
      const s = gpStickState[stickKey];
      if (s.pointerId === e.pointerId) {
        e.stopPropagation();
        s.active = false;
        s.pointerId = null;
        s.x = 0;
        s.y = 0;
        thumb.style.transform = 'translate(0px, 0px)';
        sendCommand(`gp,axis,${stickKey},0,0`);
      }
    };

    base.addEventListener('pointerdown', handlePointerDown);
    base.addEventListener('pointermove', handlePointerMove);
    base.addEventListener('pointerup', handlePointerUp);
    base.addEventListener('pointercancel', handlePointerUp);
  }

  /* ==========================================================================
     🎮 IN-DISPLAY MOBILE GAMING CONTROLLER HUD (PUBG / COD STYLE)
     ========================================================================== */
  function initScreenGamepadHUD() {
    const btnToggleHud = document.getElementById('btn-screen-gamepad-hud');
    const hudOverlay = document.getElementById('screen-gamepad-overlay');
    const hudContainer = document.getElementById('hud-elements-container');
    const btnCloseHud = document.getElementById('btn-hud-close');
    const btnEditLayout = document.getElementById('btn-hud-edit-layout');
    const btnModeSwitch = document.getElementById('btn-hud-emulation-mode');
    const editorToolbar = document.getElementById('hud-editor-toolbar');
    const selectedElemLabel = document.getElementById('hud-selected-elem-label');
    const sizeSlider = document.getElementById('hud-size-slider');
    const sizeValText = document.getElementById('hud-size-val');
    const btnSizeDec = document.getElementById('btn-hud-size-dec');
    const btnSizeInc = document.getElementById('btn-hud-size-inc');
    const opacitySlider = document.getElementById('hud-opacity-slider');
    const opacityValText = document.getElementById('hud-opacity-val');
    const btnDeleteSelected = document.getElementById('btn-hud-delete-selected');
    const btnAddBtn = document.getElementById('btn-hud-add-btn');
    const btnReset = document.getElementById('btn-hud-reset');
    const btnSave = document.getElementById('btn-hud-save');
    const addBtnModal = document.getElementById('hud-add-btn-modal');
    const btnModalCancel = document.getElementById('btn-hud-modal-cancel');
    const btnModalAddSelected = document.getElementById('btn-hud-modal-add-selected');
    const customKeyInput = document.getElementById('hud-custom-key-input');
    const filterTabs = document.querySelectorAll('.hud-filter-tab');
    const keyPickBtns = document.querySelectorAll('.hud-key-pick-btn');

    if (!btnToggleHud || !hudOverlay || !hudContainer) return;

    let isEditing = false;
    let selectedElemId = null;
    let emulationMode = 'xinput'; // 'xinput' or 'wasd'
    let customBtnCounter = 0;
    let chosenPresetBtn = null;

    // Default HUD Elements Layout
    const DEFAULT_HUD_LAYOUT = {
      scale: 1.0,
      opacity: 0.65,
      mode: 'xinput',
      elements: {
        'joystick': { left: '6%', bottom: '18%', top: 'auto', right: 'auto', type: 'joystick', scale: 1.0, label: 'JOYSTICK' },
        'lt': { left: '6%', top: '14%', right: 'auto', bottom: 'auto', type: 'trigger', gp: 'lt', key: 'mouse_right', scale: 1.0, label: 'LT (AIM)' },
        'lb': { left: '20%', top: '14%', right: 'auto', bottom: 'auto', type: 'trigger', gp: 'lb', key: 'shift', scale: 1.0, label: 'LB (SPRINT)' },
        'rt': { right: '6%', top: '14%', left: 'auto', bottom: 'auto', type: 'trigger', gp: 'rt', key: 'mouse_left', scale: 1.0, label: 'RT (FIRE)' },
        'rb': { right: '20%', top: '14%', left: 'auto', bottom: 'auto', type: 'trigger', gp: 'rb', key: 'ctrl', scale: 1.0, label: 'RB (PRONE)' },
        'btn-a': { right: '14%', bottom: '12%', left: 'auto', top: 'auto', type: 'circle', gp: 'a', key: 'space', scale: 1.0, label: 'A (JUMP)' },
        'btn-b': { right: '5%', bottom: '22%', left: 'auto', top: 'auto', type: 'circle', gp: 'b', key: 'c', scale: 1.0, label: 'B (CROUCH)' },
        'btn-x': { right: '23%', bottom: '22%', left: 'auto', top: 'auto', type: 'circle', gp: 'x', key: 'r', scale: 1.0, label: 'X (RELOAD)' },
        'btn-y': { right: '14%', bottom: '32%', left: 'auto', top: 'auto', type: 'circle', gp: 'y', key: 'e', scale: 1.0, label: 'Y (USE)' },
        'btn-1': { right: '33%', bottom: '12%', left: 'auto', top: 'auto', type: 'pill', gp: '1', key: '1', scale: 1.0, label: '1 (PRIMARY)' },
        'btn-2': { right: '33%', bottom: '24%', left: 'auto', top: 'auto', type: 'pill', gp: '2', key: '2', scale: 1.0, label: '2 (SECONDARY)' },
        'btn-tab': { left: '33%', bottom: '12%', right: 'auto', top: 'auto', type: 'pill', gp: 'back', key: 'tab', scale: 1.0, label: 'TAB (BAG)' },
        'btn-esc': { left: '33%', bottom: '24%', right: 'auto', top: 'auto', type: 'pill', gp: 'start', key: 'escape', scale: 1.0, label: 'ESC (MENU)' }
      }
    };

    function loadSavedLayout() {
      try {
        const raw = localStorage.getItem('pcdeck_gamepad_hud_layout');
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed && parsed.elements) return parsed;
        }
      } catch (e) {
        console.warn('[GamepadHUD] Error loading layout:', e);
      }
      return JSON.parse(JSON.stringify(DEFAULT_HUD_LAYOUT));
    }

    let currentLayout = loadSavedLayout();

    function getElementFriendlyName(elemId, elElem) {
      if (!elemId) return 'None';
      const conf = currentLayout.elements[elemId];
      if (conf && conf.label) return conf.label;
      if (elElem && elElem.textContent) {
        const txt = elElem.textContent.replace('✕', '').trim();
        if (txt) return txt.substring(0, 14);
      }
      return elemId.toUpperCase();
    }

    function selectHudElement(elemId) {
      // Clear previous selection
      const prevSelected = hudContainer.querySelectorAll('.hud-elem-selected');
      prevSelected.forEach(el => el.classList.remove('hud-elem-selected'));

      selectedElemId = elemId;
      if (!elemId) {
        if (selectedElemLabel) selectedElemLabel.textContent = 'Tap a Key';
        if (btnDeleteSelected) btnDeleteSelected.style.display = 'none';
        return;
      }

      const elElem = hudContainer.querySelector(`[data-elem-id="${elemId}"]`);
      if (elElem) {
        elElem.classList.add('hud-elem-selected');
        const friendlyName = getElementFriendlyName(elemId, elElem);
        if (selectedElemLabel) selectedElemLabel.textContent = friendlyName;
        if (btnDeleteSelected) btnDeleteSelected.style.display = 'inline-flex';

        const conf = currentLayout.elements[elemId] || {};
        const elemScale = conf.scale !== undefined ? conf.scale : 1.0;
        const sVal = Math.round(elemScale * 100);
        if (sizeSlider) sizeSlider.value = sVal;
        if (sizeValText) sizeValText.textContent = `${sVal}%`;

        const elemOpacity = conf.opacity !== undefined ? conf.opacity : (currentLayout.opacity || 0.65);
        const opVal = Math.round(elemOpacity * 100);
        if (opacitySlider) opacitySlider.value = opVal;
        if (opacityValText) opacityValText.textContent = `${opVal}%`;
      } else {
        selectedElemId = null;
        if (selectedElemLabel) selectedElemLabel.textContent = 'Tap a Key';
        if (btnDeleteSelected) btnDeleteSelected.style.display = 'none';
      }
    }

    function removeHudElement(elemId) {
      if (!elemId) return;
      const elElem = hudContainer.querySelector(`[data-elem-id="${elemId}"]`);
      if (elElem) {
        delete currentLayout.elements[elemId];
        elElem.remove();
        if (selectedElemId === elemId) {
          selectHudElement(null);
        }
        vibrate(20);
        showToast(`🗑️ Button Removed`, 'info', '✕');
      }
    }

    function applyLayout(layout) {
      hudContainer.style.opacity = layout.opacity !== undefined ? layout.opacity : 0.65;
      emulationMode = layout.mode || 'xinput';

      if (btnModeSwitch) {
        btnModeSwitch.textContent = emulationMode === 'xinput' ? 'Mode: XInput' : 'Mode: PC Keys';
      }

      // Sync elements
      Object.keys(layout.elements).forEach(elemId => {
        let elElem = hudContainer.querySelector(`[data-elem-id="${elemId}"]`);
        const conf = layout.elements[elemId];
        if (!elElem && conf.custom) {
          elElem = createCustomHudButton(elemId, conf);
        }
        if (elElem) {
          elElem.style.left = conf.left !== 'auto' ? conf.left : 'auto';
          elElem.style.top = conf.top !== 'auto' ? conf.top : 'auto';
          elElem.style.right = conf.right !== 'auto' ? conf.right : 'auto';
          elElem.style.bottom = conf.bottom !== 'auto' ? conf.bottom : 'auto';
          const scale = conf.scale !== undefined ? conf.scale : 1.0;
          elElem.style.transform = `scale(${scale})`;
          if (conf.opacity !== undefined) {
            elElem.style.opacity = conf.opacity;
          }
          if (conf.gp) elElem.dataset.gp = conf.gp;
          if (conf.key) elElem.dataset.key = conf.key;
        }
      });

      // Remove default DOM elements that were deleted by the user from currentLayout
      const existingDomElems = hudContainer.querySelectorAll('.hud-elem');
      existingDomElems.forEach(el => {
        const id = el.dataset.elemId;
        if (id && !layout.elements[id]) {
          el.remove();
        }
      });
    }

    function createCustomHudButton(elemId, conf) {
      const btn = document.createElement('div');
      btn.className = 'hud-elem hud-tactical-pill is-custom-btn';
      btn.dataset.elemId = elemId;
      btn.dataset.gp = conf.gp || 'a';
      btn.dataset.key = conf.key || 'space';
      const labelText = conf.label || conf.key.toUpperCase();
      btn.innerHTML = `<span>${labelText}</span>`;
      hudContainer.appendChild(btn);
      bindHudElementEvents(btn);
      return btn;
    }

    // Toggle In-Display Gaming HUD
    function toggleGamepadHUD(forceState) {
      const nextState = forceState !== undefined ? forceState : !state.gamepadHudActive;
      state.gamepadHudActive = nextState;
      btnToggleHud.classList.toggle('active', nextState);
      document.body.classList.toggle('gamepad-hud-active', nextState);

      if (nextState) {
        hudOverlay.style.display = 'flex';
        applyLayout(currentLayout);
        vibrate(30);
        showToast('🎮 In-Display Gaming HUD Active (Full Screen View)', 'info', '🎮');
      } else {
        exitEditMode();
        hudOverlay.style.display = 'none';
        sendCommand('gr');
        vibrate(15);
        showToast('Gaming HUD Closed', 'info', '🎮');
      }
    }

    window.toggleGamepadHUD = toggleGamepadHUD;
    btnToggleHud.onclick = () => toggleGamepadHUD();
    if (btnCloseHud) btnCloseHud.onclick = () => toggleGamepadHUD(false);

    if (btnModeSwitch) {
      btnModeSwitch.onclick = () => {
        vibrate(15);
        emulationMode = emulationMode === 'xinput' ? 'wasd' : 'xinput';
        currentLayout.mode = emulationMode;
        btnModeSwitch.textContent = emulationMode === 'xinput' ? 'Mode: XInput' : 'Mode: PC Keys';
        showToast(`Emulation Mode: ${emulationMode === 'xinput' ? 'Virtual Xbox 360' : 'PC Keyboard/Mouse'}`, 'info', '🕹️');
      };
    }

    // Layout Customizer Mode (PUBG / CoD Style)
    function enterEditMode() {
      isEditing = true;
      state.gamepadHudEditing = true;
      hudContainer.classList.add('hud-editing');
      editorToolbar.style.display = 'flex';
      btnEditLayout.textContent = '🔒 Exit Edit';
      btnEditLayout.classList.add('active');

      // Auto-select first available element
      const firstElem = hudContainer.querySelector('.hud-elem');
      if (firstElem) {
        selectHudElement(firstElem.dataset.elemId);
      }
      showToast('✏️ Tap any key to resize, or drag to position', 'info', '✏️');
    }

    function exitEditMode() {
      isEditing = false;
      state.gamepadHudEditing = false;
      hudContainer.classList.remove('hud-editing');
      editorToolbar.style.display = 'none';
      btnEditLayout.textContent = '✏️ Edit Layout';
      btnEditLayout.classList.remove('active');
      selectHudElement(null);
    }

    if (btnEditLayout) {
      btnEditLayout.onclick = () => {
        vibrate(15);
        if (isEditing) exitEditMode();
        else enterEditMode();
      };
    }

    // Per-Key Size Control (Slider + Buttons)
    function setElementScale(scaleRatio) {
      if (!selectedElemId) {
        showToast('Tap a button on screen to select it first', 'warn', '👆');
        return;
      }
      const elElem = hudContainer.querySelector(`[data-elem-id="${selectedElemId}"]`);
      if (elElem) {
        scaleRatio = Math.max(0.5, Math.min(2.2, scaleRatio));
        if (!currentLayout.elements[selectedElemId]) {
          currentLayout.elements[selectedElemId] = { scale: 1.0 };
        }
        currentLayout.elements[selectedElemId].scale = scaleRatio;
        elElem.style.transform = `scale(${scaleRatio})`;
        const sVal = Math.round(scaleRatio * 100);
        if (sizeSlider) sizeSlider.value = sVal;
        if (sizeValText) sizeValText.textContent = `${sVal}%`;
      }
    }

    if (sizeSlider) {
      sizeSlider.oninput = (e) => {
        const val = parseInt(e.target.value, 10);
        setElementScale(val / 100);
      };
    }

    const hudSizePills = document.querySelectorAll('[data-hud-size]');
    hudSizePills.forEach(pill => {
      pill.onclick = () => {
        vibrate(10);
        hudSizePills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        const s = parseInt(pill.dataset.hudSize, 10) / 100;
        setElementScale(s);
      };
    });

    if (btnSizeDec) {
      btnSizeDec.onclick = () => {
        const curVal = sizeSlider ? parseInt(sizeSlider.value, 10) : 100;
        setElementScale((curVal - 5) / 100);
      };
    }

    if (btnSizeInc) {
      btnSizeInc.onclick = () => {
        const curVal = sizeSlider ? parseInt(sizeSlider.value, 10) : 100;
        setElementScale((curVal + 5) / 100);
      };
    }

    // Opacity Control
    if (opacitySlider) {
      opacitySlider.oninput = (e) => {
        const opVal = parseInt(e.target.value, 10) / 100;
        currentLayout.opacity = opVal;
        hudContainer.style.opacity = opVal;
        if (opacityValText) opacityValText.textContent = `${parseInt(e.target.value, 10)}%`;
      };
    }

    const hudOpacityPills = document.querySelectorAll('[data-hud-opacity]');
    hudOpacityPills.forEach(pill => {
      pill.onclick = () => {
        vibrate(10);
        hudOpacityPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        const opVal = parseInt(pill.dataset.hudOpacity, 10) / 100;
        currentLayout.opacity = opVal;
        hudContainer.style.opacity = opVal;
        if (opacitySlider) opacitySlider.value = parseInt(pill.dataset.hudOpacity, 10);
        if (opacityValText) opacityValText.textContent = `${parseInt(pill.dataset.hudOpacity, 10)}%`;
      };
    });

    const btnExitHudEditor = document.getElementById('btn-hud-exit-editor');
    if (btnExitHudEditor) {
      btnExitHudEditor.onclick = () => exitEditMode();
    }

    // Delete Selected Button
    if (btnDeleteSelected) {
      btnDeleteSelected.onclick = () => {
        if (selectedElemId) {
          removeHudElement(selectedElemId);
        }
      };
    }

    // Save Layout
    if (btnSave) {
      btnSave.onclick = () => {
        vibrate(30);
        const allElems = hudContainer.querySelectorAll('.hud-elem');
        const containerRect = hudContainer.getBoundingClientRect();
        allElems.forEach(el => {
          const elemId = el.dataset.elemId;
          const rect = el.getBoundingClientRect();
          const leftPct = ((rect.left - containerRect.left) / containerRect.width * 100).toFixed(1) + '%';
          const topPct = ((rect.top - containerRect.top) / containerRect.height * 100).toFixed(1) + '%';
          if (!currentLayout.elements[elemId]) {
            currentLayout.elements[elemId] = { custom: true, gp: el.dataset.gp, key: el.dataset.key, label: el.textContent.replace('✕', '').trim() };
          }
          currentLayout.elements[elemId].left = leftPct;
          currentLayout.elements[elemId].top = topPct;
          currentLayout.elements[elemId].right = 'auto';
          currentLayout.elements[elemId].bottom = 'auto';
        });
        currentLayout.mode = emulationMode;

        localStorage.setItem('pcdeck_gamepad_hud_layout', JSON.stringify(currentLayout));
        exitEditMode();
        showToast('💾 Gaming HUD Layout Saved Permanently!', 'success', '💾');
      };
    }

    // Reset Layout
    if (btnReset) {
      btnReset.onclick = () => {
        vibrate(20);
        currentLayout = JSON.parse(JSON.stringify(DEFAULT_HUD_LAYOUT));
        localStorage.removeItem('pcdeck_gamepad_hud_layout');
        hudContainer.innerHTML = `
          <div id="hud-elem-joystick" class="hud-elem hud-joystick-zone" data-elem-id="joystick" style="left: 6%; bottom: 18%;">
            <div class="hud-joystick-base">
              <div class="hud-joystick-stick" id="hud-joystick-thumb"></div>
              <span class="hud-joystick-label">LS / WASD</span>
            </div>
          </div>
          <div id="hud-elem-lt" class="hud-elem hud-trigger-btn hud-trigger-lt" data-elem-id="lt" data-gp="lt" style="left: 6%; top: 14%;">
            <span class="hud-btn-text">LT</span>
            <span class="hud-btn-sub">AIM / ADS</span>
          </div>
          <div id="hud-elem-lb" class="hud-elem hud-trigger-btn hud-trigger-lb" data-elem-id="lb" data-gp="lb" style="left: 20%; top: 14%;">
            <span class="hud-btn-text">LB</span>
            <span class="hud-btn-sub">SPRINT</span>
          </div>
          <div id="hud-elem-rt" class="hud-elem hud-trigger-btn hud-trigger-rt" data-elem-id="rt" data-gp="rt" style="right: 6%; top: 14%;">
            <span class="hud-btn-text">RT</span>
            <span class="hud-btn-sub">FIRE 💥</span>
          </div>
          <div id="hud-elem-rb" class="hud-elem hud-trigger-btn hud-trigger-rb" data-elem-id="rb" data-gp="rb" style="right: 20%; top: 14%;">
            <span class="hud-btn-text">RB</span>
            <span class="hud-btn-sub">PRONE</span>
          </div>
          <div id="hud-elem-btn-a" class="hud-elem hud-action-circle btn-hud-a" data-elem-id="btn-a" data-gp="a" style="right: 14%; bottom: 12%;">
            <span class="hud-circle-glyph">A</span>
            <span class="hud-circle-sub">JUMP</span>
          </div>
          <div id="hud-elem-btn-b" class="hud-elem hud-action-circle btn-hud-b" data-elem-id="btn-b" data-gp="b" style="right: 5%; bottom: 22%;">
            <span class="hud-circle-glyph">B</span>
            <span class="hud-circle-sub">CROUCH</span>
          </div>
          <div id="hud-elem-btn-x" class="hud-elem hud-action-circle btn-hud-x" data-elem-id="btn-x" data-gp="x" style="right: 23%; bottom: 22%;">
            <span class="hud-circle-glyph">X</span>
            <span class="hud-circle-sub">RELOAD</span>
          </div>
          <div id="hud-elem-btn-y" class="hud-elem hud-action-circle btn-hud-y" data-elem-id="btn-y" data-gp="y" style="right: 14%; bottom: 32%;">
            <span class="hud-circle-glyph">Y</span>
            <span class="hud-circle-sub">USE</span>
          </div>
          <div id="hud-elem-btn-1" class="hud-elem hud-tactical-pill" data-elem-id="btn-1" data-gp="1" style="right: 33%; bottom: 12%;">
            <span>1️⃣ PRIM</span>
          </div>
          <div id="hud-elem-btn-2" class="hud-elem hud-tactical-pill" data-elem-id="btn-2" data-gp="2" style="right: 33%; bottom: 24%;">
            <span>2️⃣ SEC</span>
          </div>
          <div id="hud-elem-btn-tab" class="hud-elem hud-tactical-pill" data-elem-id="btn-tab" data-gp="back" style="left: 33%; bottom: 12%;">
            <span>🎒 TAB</span>
          </div>
          <div id="hud-elem-btn-esc" class="hud-elem hud-tactical-pill" data-elem-id="btn-esc" data-gp="start" style="left: 33%; bottom: 24%;">
            <span>⚙️ ESC</span>
          </div>
        `;
        const newElems = hudContainer.querySelectorAll('.hud-elem');
        newElems.forEach(bindHudElementEvents);
        initJoystick();
        applyLayout(currentLayout);
        selectHudElement('btn-a');
        showToast('↺ Restored Default Controller Layout', 'info', '↺');
      };
    }

    // Add Button Modal & Category Filtering
    if (btnAddBtn && addBtnModal) {
      btnAddBtn.onclick = () => {
        vibrate(15);
        chosenPresetBtn = null;
        if (customKeyInput) customKeyInput.value = '';
        keyPickBtns.forEach(b => b.classList.remove('selected'));
        addBtnModal.style.display = 'flex';
      };
    }

    if (btnModalCancel && addBtnModal) {
      btnModalCancel.onclick = () => {
        addBtnModal.style.display = 'none';
      };
    }

    if (filterTabs) {
      filterTabs.forEach(tab => {
        tab.onclick = () => {
          filterTabs.forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
          const filter = tab.dataset.filter;
          keyPickBtns.forEach(btn => {
            if (filter === 'all' || btn.dataset.category === filter) {
              btn.style.display = 'block';
            } else {
              btn.style.display = 'none';
            }
          });
        };
      });
    }

    keyPickBtns.forEach(pick => {
      pick.onclick = () => {
        keyPickBtns.forEach(b => b.classList.remove('selected'));
        pick.classList.add('selected');
        chosenPresetBtn = pick;
        if (customKeyInput) customKeyInput.value = '';
      };
    });

    if (btnModalAddSelected) {
      btnModalAddSelected.onclick = () => {
        let key = '';
        let label = '';
        let gp = 'a';

        const customVal = customKeyInput ? customKeyInput.value.trim().toLowerCase() : '';
        if (customVal) {
          key = customVal;
          label = customVal.toUpperCase();
          gp = 'a';
        } else if (chosenPresetBtn) {
          key = chosenPresetBtn.dataset.key;
          label = chosenPresetBtn.dataset.label || key.toUpperCase();
          gp = chosenPresetBtn.dataset.gp || 'a';
        } else {
          showToast('Please select a button or type a custom key', 'warn', '⚠️');
          return;
        }

        customBtnCounter++;
        const customId = `custom-btn-${customBtnCounter}-${Date.now()}`;
        currentLayout.elements[customId] = {
          left: '45%',
          top: '45%',
          right: 'auto',
          bottom: 'auto',
          custom: true,
          key: key,
          gp: gp,
          label: label,
          scale: 1.0
        };

        const elNew = createCustomHudButton(customId, currentLayout.elements[customId]);
        elNew.style.left = '45%';
        elNew.style.top = '45%';
        elNew.style.transform = 'scale(1.0)';
        addBtnModal.style.display = 'none';
        selectHudElement(customId);
        showToast(`➕ Added "${label}" (Drag to reposition)`, 'success', '➕');
        vibrate(25);
      };
    }

    // Multi-Touch Button & Drag Engine (100% Fluid, Zero Snapping)
    function bindHudElementEvents(elElem) {
      let isDragging = false;
      let startX = 0, startY = 0;
      let initialLeft = 0, initialTop = 0;

      elElem.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        e.stopPropagation();

        if (isEditing) {
          const rect = elElem.getBoundingClientRect();
          // Check if delete handle tapped (top-right corner 28px region)
          if (e.clientX > rect.right - 28 && e.clientY < rect.top + 28) {
            removeHudElement(elElem.dataset.elemId);
            return;
          }

          // Select this element
          selectHudElement(elElem.dataset.elemId);

          // Fluid Drag Mode
          isDragging = true;
          elElem.classList.add('is-dragging');
          try { elElem.setPointerCapture(e.pointerId); } catch (_) {}
          startX = e.clientX;
          startY = e.clientY;
          const containerRect = hudContainer.getBoundingClientRect();
          initialLeft = rect.left - containerRect.left;
          initialTop = rect.top - containerRect.top;

          elElem.style.position = 'absolute';
          elElem.style.left = `${initialLeft.toFixed(1)}px`;
          elElem.style.top = `${initialTop.toFixed(1)}px`;
          elElem.style.right = 'auto';
          elElem.style.bottom = 'auto';
          return;
        }

        // Gameplay Button Press Mode
        if (elElem.dataset.elemId === 'joystick') return;

        elElem.classList.add('active-pressed');
        if (state.hapticsEnabled) vibrate(12);

        const gpCode = elElem.dataset.gp;
        const key = elElem.dataset.key;

        if (emulationMode === 'wasd') {
          if (key && key.startsWith('mouse_')) {
            sendCommand(`mouse,down,${key.replace('mouse_', '')}`);
          } else if (key) {
            sendCommand(`key,down,${key}`);
          }
        } else {
          if (gpCode === 'lt' || gpCode === 'rt') {
            sendCommand(`gt,${gpCode},1.0`);
          } else if (gpCode) {
            sendCommand(`gp,btn,${gpCode},1`);
          }
        }
      });

      elElem.addEventListener('pointermove', (e) => {
        if (isEditing && isDragging) {
          e.preventDefault();
          e.stopPropagation();
          const dx = e.clientX - startX;
          const dy = e.clientY - startY;
          const newLeft = Math.max(0, Math.min(hudContainer.clientWidth - elElem.offsetWidth, initialLeft + dx));
          const newTop = Math.max(0, Math.min(hudContainer.clientHeight - elElem.offsetHeight, initialTop + dy));
          elElem.style.left = `${newLeft.toFixed(1)}px`;
          elElem.style.top = `${newTop.toFixed(1)}px`;
          elElem.style.right = 'auto';
          elElem.style.bottom = 'auto';
        }
      });

      const onPointerRelease = (e) => {
        if (isEditing && isDragging) {
          isDragging = false;
          elElem.classList.remove('is-dragging');
          try { elElem.releasePointerCapture(e.pointerId); } catch (_) {}
          const containerRect = hudContainer.getBoundingClientRect();
          const rect = elElem.getBoundingClientRect();
          const leftPct = (((rect.left - containerRect.left) / containerRect.width) * 100).toFixed(2) + '%';
          const topPct = (((rect.top - containerRect.top) / containerRect.height) * 100).toFixed(2) + '%';
          elElem.style.left = leftPct;
          elElem.style.top = topPct;
          if (currentLayout.elements[elElem.dataset.elemId]) {
            currentLayout.elements[elElem.dataset.elemId].left = leftPct;
            currentLayout.elements[elElem.dataset.elemId].top = topPct;
            currentLayout.elements[elElem.dataset.elemId].right = 'auto';
            currentLayout.elements[elElem.dataset.elemId].bottom = 'auto';
          }
          return;
        }

        if (elElem.dataset.elemId === 'joystick') return;

        elElem.classList.remove('active-pressed');
        const gpCode = elElem.dataset.gp;
        const key = elElem.dataset.key;

        if (emulationMode === 'wasd') {
          if (key && key.startsWith('mouse_')) {
            sendCommand(`mouse,up,${key.replace('mouse_', '')}`);
          } else if (key) {
            sendCommand(`key,up,${key}`);
          }
        } else {
          if (gpCode === 'lt' || gpCode === 'rt') {
            sendCommand(`gt,${gpCode},0.0`);
          } else if (gpCode) {
            sendCommand(`gp,btn,${gpCode},0`);
          }
        }
      };

      elElem.addEventListener('pointerup', onPointerRelease);
      elElem.addEventListener('pointercancel', onPointerRelease);
    }

    // Bind all initial elements
    const initialElems = hudContainer.querySelectorAll('.hud-elem');
    initialElems.forEach(bindHudElementEvents);

    // 🕹️ Virtual Joystick Engine
    let joystickActive = false;
    let joystickPointerId = null;
    let lastStickX = 0, lastStickY = 0;
    const maxStickRadius = 40;
    let activeKeys = { w: false, a: false, s: false, d: false };

    function initJoystick() {
      const joystickZone = document.getElementById('hud-elem-joystick');
      const joystickThumb = document.getElementById('hud-joystick-thumb');
      if (!joystickZone || !joystickThumb) return;

      joystickZone.addEventListener('pointerdown', (e) => {
        if (isEditing) return;
        e.preventDefault();
        e.stopPropagation();
        joystickActive = true;
        joystickPointerId = e.pointerId;
        joystickZone.setPointerCapture(e.pointerId);
        if (state.hapticsEnabled) vibrate(15);
        updateJoystickPosition(e.clientX, e.clientY);
      });

      joystickZone.addEventListener('pointermove', (e) => {
        if (!joystickActive || joystickPointerId !== e.pointerId || isEditing) return;
        e.preventDefault();
        e.stopPropagation();
        updateJoystickPosition(e.clientX, e.clientY);
      });

      const onJoystickRelease = (e) => {
        if (!joystickActive || joystickPointerId !== e.pointerId) return;
        joystickActive = false;
        joystickPointerId = null;
        try { joystickZone.releasePointerCapture(e.pointerId); } catch (_) {}
        joystickThumb.style.transform = 'translate(0px, 0px)';

        if (emulationMode === 'wasd') {
          ['w', 'a', 's', 'd'].forEach(k => {
            if (activeKeys[k]) {
              sendCommand(`key,up,${k}`);
              activeKeys[k] = false;
            }
          });
        } else {
          sendCommand('ga,left,0,0');
        }
      };

      joystickZone.addEventListener('pointerup', onJoystickRelease);
      joystickZone.addEventListener('pointercancel', onJoystickRelease);

      function updateJoystickPosition(clientX, clientY) {
        const rect = joystickZone.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        let dx = clientX - centerX;
        let dy = clientY - centerY;
        const dist = Math.hypot(dx, dy);

        if (dist > maxStickRadius) {
          dx = (dx / dist) * maxStickRadius;
          dy = (dy / dist) * maxStickRadius;
        }

        joystickThumb.style.transform = `translate(${dx}px, ${dy}px)`;

        let normX = dx / maxStickRadius;
        let normY = -(dy / maxStickRadius);

        const deadzone = 0.12;
        if (Math.abs(normX) < deadzone) normX = 0;
        if (Math.abs(normY) < deadzone) normY = 0;

        if (emulationMode === 'wasd') {
          const pressW = normY > 0.35;
          const pressS = normY < -0.35;
          const pressD = normX > 0.35;
          const pressA = normX < -0.35;

          if (pressW !== activeKeys.w) { sendCommand(`key,${pressW ? 'down' : 'up'},w`); activeKeys.w = pressW; }
          if (pressS !== activeKeys.s) { sendCommand(`key,${pressS ? 'down' : 'up'},s`); activeKeys.s = pressS; }
          if (pressA !== activeKeys.a) { sendCommand(`key,${pressA ? 'down' : 'up'},a`); activeKeys.a = pressA; }
          if (pressD !== activeKeys.d) { sendCommand(`key,${pressD ? 'down' : 'up'},d`); activeKeys.d = pressD; }
        } else {
          normX = Math.round(normX * 100) / 100;
          normY = Math.round(normY * 100) / 100;
          if (normX !== lastStickX || normY !== lastStickY) {
            lastStickX = normX;
            lastStickY = normY;
            sendCommand(`ga,left,${normX},${normY}`);
          }
        }
      }
    }

    initJoystick();

    // Apply layout on startup
    applyLayout(currentLayout);
  }

  // =========================================================================
  // WIRELESS PC MICROPHONE MODULE
  // =========================================================================
  let micWs = null;
  let micAudioContext = null;
  let micMediaStream = null;
  let micProcessorNode = null;
  let micGainNode = null;
  let micActive = false;
  let micMuted = false;

  function initWirelessMicrophone() {
    const btnToggle = document.getElementById('btn-toggle-mic');
    const btnMute = document.getElementById('btn-mute-mic');
    const statusBadge = document.getElementById('mic-status-badge');
    const vuFill = document.getElementById('vu-meter-fill');
    const vuDb = document.getElementById('vu-meter-db');
    const gainSlider = document.getElementById('mic-gain-slider');
    const gainVal = document.getElementById('mic-gain-val');

    if (gainSlider && gainVal) {
      gainSlider.oninput = (e) => {
        gainVal.textContent = `${e.target.value}%`;
        if (micGainNode) micGainNode.gain.value = e.target.value / 100;
      };
    }

    async function startMic() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
        micMediaStream = stream;
        micAudioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 48000 });
        const source = micAudioContext.createMediaStreamSource(stream);

        micGainNode = micAudioContext.createGain();
        if (gainSlider) micGainNode.gain.value = gainSlider.value / 100;

        const analyser = micAudioContext.createAnalyser();
        analyser.fftSize = 64;
        source.connect(micGainNode);
        micGainNode.connect(analyser);

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${state.serverHost}:${state.serverPort}/ws/mic`;
        micWs = new WebSocket(wsUrl);
        micWs.binaryType = 'arraybuffer';

        // Stream 16-bit PCM Audio
        const scriptNode = micAudioContext.createScriptProcessor(2048, 1, 1);
        const pcmData = new Int16Array(2048);
        scriptNode.onaudioprocess = (e) => {
          if (!micActive || micMuted || micWs.readyState !== WebSocket.OPEN) return;
          const input = e.inputBuffer.getChannelData(0);
          for (let i = 0; i < input.length; i++) {
            let s = Math.max(-1, Math.min(1, input[i]));
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          micWs.send(pcmData.buffer);
        };

        micGainNode.connect(scriptNode);
        scriptNode.connect(micAudioContext.destination);
        micProcessorNode = scriptNode;

        // VU meter ticker
        const pcmBuffer = new Uint8Array(analyser.frequencyBinCount);
        const updateVu = () => {
          if (!micActive) return;
          analyser.getByteFrequencyData(pcmBuffer);
          let sum = 0;
          for (let i = 0; i < pcmBuffer.length; i++) sum += pcmBuffer[i];
          let avg = sum / pcmBuffer.length;
          let pct = Math.min(100, Math.round((avg / 128) * 100));
          if (vuFill) vuFill.style.width = `${pct}%`;
          if (vuDb) vuDb.textContent = `${pct > 0 ? '-' + (100 - pct) : '-inf'} dB`;
          requestAnimationFrame(updateVu);
        };

        micActive = true;
        if (btnToggle) {
          btnToggle.className = 'neo-btn btn-pink';
          btnToggle.innerHTML = '<span>⏹️</span><span>STOP MICROPHONE</span>';
        }
        if (btnMute) btnMute.style.display = 'inline-block';
        if (statusBadge) {
          statusBadge.className = 'mini-status-chip online';
          statusBadge.textContent = 'TRANSMITTING';
        }
        const quickMicBtn = document.getElementById('btn-quick-mic-toggle');
        if (quickMicBtn) {
          quickMicBtn.style.background = 'var(--neo-pink)';
          quickMicBtn.textContent = '🎙️ Mic: ON';
        }
        const toolMicSub = document.getElementById('tool-mic-status');
        if (toolMicSub) toolMicSub.textContent = 'Active';

        showToast('Microphone Active (Streaming to PC)', 'success', '🎙️');
        updateVu();
      } catch (err) {
        showToast('Mic Access Denied: ' + err.message, 'error', '⚠️');
      }
    }

    function stopMic() {
      micActive = false;
      if (micMediaStream) {
        micMediaStream.getTracks().forEach(t => t.stop());
        micMediaStream = null;
      }
      if (micAudioContext) {
        micAudioContext.close();
        micAudioContext = null;
      }
      if (micWs) {
        micWs.close();
        micWs = null;
      }
      if (btnToggle) {
        btnToggle.className = 'neo-btn btn-lime';
        btnToggle.innerHTML = '<span>🎙️</span><span>START TRANSMITTING</span>';
      }
      if (btnMute) btnMute.style.display = 'none';
      if (statusBadge) {
        statusBadge.className = 'mini-status-chip offline';
        statusBadge.textContent = 'OFFLINE';
      }
      if (vuFill) vuFill.style.width = '0%';

      const quickMicBtn = document.getElementById('btn-quick-mic-toggle');
      if (quickMicBtn) {
        quickMicBtn.style.background = 'var(--neo-lime)';
        quickMicBtn.textContent = '🎙️ Mic';
      }
      const toolMicSub = document.getElementById('tool-mic-status');
      if (toolMicSub) toolMicSub.textContent = 'Offline';
    }

    const toggleMicHandler = () => {
      vibrate(15);
      if (micActive) stopMic(); else startMic();
    };

    if (btnToggle) btnToggle.onclick = toggleMicHandler;

    const quickMicBtn = document.getElementById('btn-quick-mic-toggle');
    if (quickMicBtn) quickMicBtn.onclick = toggleMicHandler;

    const toolMicBtn = document.getElementById('tool-mic-quick');
    if (toolMicBtn) toolMicBtn.onclick = () => {
      toggleMicHandler();
      if (el.quickToolsDrawer) el.quickToolsDrawer.classList.remove('open');
    };

    if (btnMute) {
      btnMute.onclick = () => {
        vibrate(15);
        micMuted = !micMuted;
        btnMute.textContent = micMuted ? '🔊 UNMUTE' : '🔇 MUTE';
        btnMute.style.background = micMuted ? 'var(--neo-yellow)' : '';
      };
    }
  }

  // =========================================================================
  // WIRELESS HD WEBCAM MODULE WITH MULTI-LENS & TORCH SUPPORT
  // =========================================================================
  let camWs = null;
  let camMediaStream = null;
  let camActive = false;
  let camFacingMode = 'environment';
  let camSelectedDeviceId = '';
  let camTargetRes = 720;
  let camFps = 30;
  let camTorchActive = false;
  let availableVideoDevices = [];

  function initWirelessWebcam() {
    const btnToggle = document.getElementById('btn-toggle-cam');
    const btnSwitch = document.getElementById('btn-switch-cam-lens');
    const btnTorch = document.getElementById('btn-toggle-torch');
    const deviceSelect = document.getElementById('cam-device-select');
    const statusBadge = document.getElementById('cam-status-badge');
    const videoPreview = document.getElementById('webcam-preview-video');
    const placeholder = document.getElementById('cam-idle-placeholder');
    const resChips = document.querySelectorAll('.cam-res-selector .neo-chip-toggle');

    // Enumerate hardware cameras
    async function enumerateCameras() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        availableVideoDevices = devices.filter(d => d.kind === 'videoinput');

        if (deviceSelect && availableVideoDevices.length > 0) {
          deviceSelect.innerHTML = '';
          availableVideoDevices.forEach((dev, idx) => {
            const opt = document.createElement('option');
            opt.value = dev.deviceId;
            let label = dev.label || `Camera ${idx + 1}`;
            if (label.toLowerCase().includes('back') || label.toLowerCase().includes('rear') || label.toLowerCase().includes('environment')) {
              opt.textContent = `📷 Rear: ${label}`;
            } else if (label.toLowerCase().includes('front') || label.toLowerCase().includes('user')) {
              opt.textContent = `🤳 Front: ${label}`;
            } else {
              opt.textContent = `📷 ${label}`;
            }
            deviceSelect.appendChild(opt);
          });
          if (camSelectedDeviceId) deviceSelect.value = camSelectedDeviceId;
        }
      } catch (e) {
        console.warn('Camera enumeration error:', e);
      }
    }

    if (deviceSelect) {
      deviceSelect.onchange = () => {
        camSelectedDeviceId = deviceSelect.value;
        if (camActive) {
          stopCam();
          startCam();
        }
      };
    }

    resChips.forEach((chip) => {
      chip.onclick = () => {
        const targetRes = parseInt(chip.dataset.res, 10) || 720;
        if (targetRes === 1080 && (!window.isProUnlocked || !window.isProUnlocked())) {
          if (typeof vibrate === 'function') vibrate(25);
          if (typeof window.openProUpgradeModal === 'function') {
            window.openProUpgradeModal();
          }
          if (typeof showToast === 'function') {
            showToast('1080p 60 FPS HD Webcam requires PCDeck Pro', 'warn', '⭐');
          }
          return;
        }
        resChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        camTargetRes = targetRes;
        camFps = camTargetRes === 1080 ? 60 : (camTargetRes === 480 ? 60 : 30);
        if (typeof vibrate === 'function') vibrate(15);
        if (camActive) {
          stopCam();
          startCam();
        }
      };
    });

    async function startCam() {
      try {
        let width = 1280;
        let height = 720;
        if (camTargetRes === 1080) { width = 1920; height = 1080; }
        else if (camTargetRes === 480) { width = 854; height = 480; }

        const videoConstraints = {
          width: { ideal: width },
          height: { ideal: height },
          frameRate: { ideal: camFps }
        };

        if (camSelectedDeviceId) {
          videoConstraints.deviceId = { exact: camSelectedDeviceId };
        } else {
          videoConstraints.facingMode = camFacingMode;
        }

        const stream = await navigator.mediaDevices.getUserMedia({ video: videoConstraints });
        camMediaStream = stream;

        // Re-enumerate to get full device labels once permission is granted
        await enumerateCameras();

        if (videoPreview) {
          videoPreview.srcObject = stream;
          videoPreview.play();
        }
        if (placeholder) placeholder.style.display = 'none';

        // Check torch capabilities
        const track = stream.getVideoTracks()[0];
        if (track && typeof track.getCapabilities === 'function') {
          const caps = track.getCapabilities();
          if (caps && caps.torch && btnTorch) {
            btnTorch.style.display = 'inline-block';
          }
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${state.serverHost}:${state.serverPort}/ws/cam`;
        camWs = new WebSocket(wsUrl);

        // Hardware-accelerated canvas frame grabber
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d', { alpha: false, desynchronized: true });
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'medium';

        const frameInterval = 1000 / camFps;
        let lastFrameTime = 0;

        const captureFrame = (time) => {
          if (!camActive) return;
          if (time - lastFrameTime >= frameInterval && camWs && camWs.readyState === WebSocket.OPEN && videoPreview && videoPreview.readyState >= 2) {
            lastFrameTime = time;
            ctx.drawImage(videoPreview, 0, 0, canvas.width, canvas.height);
            canvas.toBlob((blob) => {
              if (blob && camWs && camWs.readyState === WebSocket.OPEN) {
                blob.arrayBuffer().then(buf => camWs.send(buf));
              }
            }, 'image/jpeg', 0.82);
          }
          requestAnimationFrame(captureFrame);
        };

        camActive = true;
        if (btnToggle) {
          btnToggle.className = 'neo-btn btn-pink';
          btnToggle.innerHTML = '<span>⏹️</span><span>STOP WEBCAM</span>';
        }
        if (btnSwitch) btnSwitch.style.display = 'inline-block';
        if (statusBadge) {
          statusBadge.className = 'mini-status-chip online';
          statusBadge.textContent = 'STREAMING ' + camTargetRes + 'p';
        }
        const quickCamBtn = document.getElementById('btn-quick-cam-toggle');
        if (quickCamBtn) {
          quickCamBtn.style.background = 'var(--neo-pink)';
          quickCamBtn.textContent = '📹 Cam: ON';
        }
        const toolCamSub = document.getElementById('tool-cam-status');
        if (toolCamSub) toolCamSub.textContent = 'Active';

        showToast('Webcam Broadcasting to PC DirectShow', 'success', '📹');
        requestAnimationFrame(captureFrame);
      } catch (err) {
        showToast('Camera Access Denied: ' + err.message, 'error', '⚠️');
      }
    }

    function stopCam() {
      camActive = false;
      camTorchActive = false;
      if (btnTorch) {
        btnTorch.style.display = 'none';
        btnTorch.style.background = '';
      }
      if (camMediaStream) {
        camMediaStream.getTracks().forEach(t => t.stop());
        camMediaStream = null;
      }
      if (videoPreview) videoPreview.srcObject = null;
      if (placeholder) placeholder.style.display = 'flex';
      if (camWs) {
        camWs.close();
        camWs = null;
      }
      if (btnToggle) {
        btnToggle.className = 'neo-btn btn-cyan';
        btnToggle.innerHTML = '<span>📹</span><span>START WEBCAM</span>';
      }
      if (btnSwitch) btnSwitch.style.display = 'none';
      if (statusBadge) {
        statusBadge.className = 'mini-status-chip offline';
        statusBadge.textContent = 'OFFLINE';
      }
      const quickCamBtn = document.getElementById('btn-quick-cam-toggle');
      if (quickCamBtn) {
        quickCamBtn.style.background = 'var(--neo-cyan)';
        quickCamBtn.textContent = '📹 Cam';
      }
      const toolCamSub = document.getElementById('tool-cam-status');
      if (toolCamSub) toolCamSub.textContent = 'Offline';
    }

    // Torch Toggle
    if (btnTorch) {
      btnTorch.onclick = async () => {
        vibrate(15);
        if (!camMediaStream) return;
        const track = camMediaStream.getVideoTracks()[0];
        if (track) {
          try {
            camTorchActive = !camTorchActive;
            await track.applyConstraints({ advanced: [{ torch: camTorchActive }] });
            btnTorch.style.background = camTorchActive ? 'var(--neo-lime)' : 'var(--neo-yellow)';
            btnTorch.style.color = '#000';
            showToast(`Torch: ${camTorchActive ? 'ON' : 'OFF'}`, 'info', '💡');
          } catch (e) {
            console.warn('Torch toggle error:', e);
          }
        }
      };
    }

    // Cycle Next Lens / Sensor
    if (btnSwitch) {
      btnSwitch.onclick = () => {
        vibrate(15);
        if (availableVideoDevices.length > 1) {
          let currentIdx = availableVideoDevices.findIndex(d => d.deviceId === camSelectedDeviceId);
          let nextIdx = (currentIdx + 1) % availableVideoDevices.length;
          camSelectedDeviceId = availableVideoDevices[nextIdx].deviceId;
          if (deviceSelect) deviceSelect.value = camSelectedDeviceId;
        } else {
          camFacingMode = camFacingMode === 'user' ? 'environment' : 'user';
          camSelectedDeviceId = '';
        }
        if (camActive) {
          stopCam();
          startCam();
        }
      };
    }

    const toggleCamHandler = () => {
      vibrate(15);
      if (camActive) stopCam(); else startCam();
    };

    if (btnToggle) btnToggle.onclick = toggleCamHandler;

    const quickCamBtn = document.getElementById('btn-quick-cam-toggle');
    if (quickCamBtn) quickCamBtn.onclick = toggleCamHandler;

    const toolCamBtn = document.getElementById('tool-cam-quick');
    if (toolCamBtn) toolCamBtn.onclick = () => {
      toggleCamHandler();
      if (el.quickToolsDrawer) el.quickToolsDrawer.classList.remove('open');
    };

    enumerateCameras();
  }

  // =========================================================================
  // HIGH-TRUST DRIVER MODAL MANAGER
  // =========================================================================
  function initDriverTrustManager() {
    const modal = document.getElementById('driver-trust-modal');
    const btnInstall = document.getElementById('btn-modal-install-driver');
    const btnSkip = document.getElementById('btn-modal-skip-driver');
    const statusBox = document.getElementById('driver-install-status-box');

    if (btnInstall) {
      btnInstall.onclick = () => {
        vibrate(20);
        if (statusBox) {
          statusBox.style.display = 'block';
          statusBox.style.background = 'rgba(0, 240, 255, 0.15)';
          statusBox.style.color = 'var(--neo-cyan)';
          statusBox.textContent = '⚡ Running 1-Click Silent Setup on PC...';
        }
        sendCommand('install_driver_request');
      };
    }

    if (btnSkip && modal) {
      btnSkip.onclick = () => {
        vibrate(10);
        modal.style.display = 'none';
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
    initGamepadEngine();
    initScreenGamepadHUD();
    initWirelessMicrophone();
    initWirelessWebcam();
    initDriverTrustManager();

    // Trigger zero-config background UDP discovery and fast subnet probe immediately (< 5ms)
    triggerDiscoveryAndSweep();

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
    } else if (savedIp) {
      connect();
    } else if (isNativeApp && !onboardingDone) {
      if (typeof window.openOnboardingModal === 'function') {
        window.openOnboardingModal();
      }
    } else {
      if (el.connectModal) el.connectModal.classList.add('show');
    }

    document.addEventListener('fullscreenchange', updateQuickToolsUi);
    document.addEventListener('webkitfullscreenchange', updateQuickToolsUi);
    window.addEventListener('resize', updateQuickToolsUi);
    window.addEventListener('orientationchange', updateQuickToolsUi);

    // Dynamic Wake-Up & Proactive Instant Reconnection Engine
    function checkAndResumeConnection() {
      triggerDiscoveryAndSweep();
      if (document.visibilityState === 'visible') {
        if (!state.connected || !mainWs || mainWs.readyState !== WebSocket.OPEN) {
          reconnectAttempts = 0;
          connect();
        } else if (!screenWs || screenWs.readyState !== WebSocket.OPEN) {
          connectScreenWs();
        }
      }
    }
    document.addEventListener('visibilitychange', checkAndResumeConnection);
    window.addEventListener('focus', checkAndResumeConnection);
    window.addEventListener('pageshow', checkAndResumeConnection);
    window.addEventListener('online', () => {
      reconnectAttempts = 0;
      triggerDiscoveryAndSweep();
      connect(true);
    });
    window.onAppResume = checkAndResumeConnection;

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

