(() => {
  // src/core/state.js
  var state = {
    isRecording: false,
    recordMode: "errors",
    // 'errors' | 'all'
    startTime: null,
    consoleLogs: [],
    networkErrors: [],
    jsExceptions: [],
    recordedRequests: [],
    screenshot: null
  };
  window.__errorLensState = window.__errorLensState || state;
  function getState() {
    return window.__errorLensState || state;
  }
  function resetState() {
    const s = getState();
    s.isRecording = false;
    s.startTime = null;
    s.consoleLogs = [];
    s.networkErrors = [];
    s.jsExceptions = [];
    s.recordedRequests = [];
    s.screenshot = null;
  }
  function getSessionData() {
    const s = getState();
    return {
      console_logs: s.consoleLogs.slice(0, 1e3),
      network_errors: s.networkErrors.slice(0, 100),
      js_exceptions: s.jsExceptions.slice(0, 100),
      recorded_requests: s.recordedRequests.slice(0, 500),
      screenshot: s.screenshot,
      recording_duration_ms: s.startTime ? Date.now() - s.startTime : 0,
      record_mode: s.recordMode,
      url: window.location.href,
      user_agent: navigator.userAgent
    };
  }
  function getEventCounts() {
    const s = getState();
    return {
      logs: s.consoleLogs.length,
      errors: s.networkErrors.length + s.jsExceptions.length,
      requests: s.recordedRequests.length,
      total: s.consoleLogs.length + s.networkErrors.length + s.jsExceptions.length + s.recordedRequests.length
    };
  }

  // src/core/config.js
  var CONFIG = {
    VERSION: "2.0.0",
    API_TIMEOUT: 3e4,
    MAX_LOGS: 1e3,
    MAX_REQUESTS: 500,
    JUNK_URL_PATTERNS: [
      /google-analytics\.com/,
      /googletagmanager\.com/,
      /facebook\.com\/tr/,
      /doubleclick\.net/,
      /hotjar\.com/,
      /clarity\.ms/,
      /mc\.yandex\.ru/,
      /\.png(\?|$)/,
      /\.jpg(\?|$)/,
      /\.gif(\?|$)/,
      /\.svg(\?|$)/,
      /\.css(\?|$)/,
      /\.woff/,
      /favicon\.ico/
    ],
    COLORS: {
      IDLE: "#6366f1",
      RECORDING: "#ef4444",
      DONE: "#22c55e",
      GRADIENT: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    }
  };
  var PROD_URL = "http://localhost:3000/api";
  var LOCAL_URL = "http://localhost:8000";
  function detectApiBaseUrl() {
    const userConfig = window.__ERRORLENS_CONFIG__ || {};
    if (userConfig.apiUrl)
      return userConfig.apiUrl;
    const saved = localStorage.getItem("errorlens_api_url");
    if (saved)
      return saved;
    const currentScript = document.currentScript || document.querySelector('script[src*="recorder.js"]');
    const scriptSrc = currentScript ? currentScript.src : "";
    const isScriptFromLocalhost = scriptSrc.includes("localhost") || scriptSrc.includes("127.0.0.1");
    const isPageOnLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    return isScriptFromLocalhost || isPageOnLocalhost ? LOCAL_URL : PROD_URL;
  }
  function isJunkUrl(url) {
    if (!url)
      return true;
    return CONFIG.JUNK_URL_PATTERNS.some((pattern) => pattern.test(url));
  }

  // src/core/api.js
  async function sendSession() {
    const apiUrl = detectApiBaseUrl();
    const sessionData = getSessionData();
    const response = await fetch(`${apiUrl}/sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(sessionData)
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error ${response.status}: ${errorText}`);
    }
    return response.json();
  }
  function loadHtml2Canvas() {
    return new Promise((resolve, reject) => {
      if (window.html2canvas) {
        resolve(window.html2canvas);
        return;
      }
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js";
      script.onload = () => resolve(window.html2canvas);
      script.onerror = () => reject(new Error("Failed to load html2canvas"));
      document.head.appendChild(script);
    });
  }
  async function captureScreenshot() {
    try {
      const html2canvas = await loadHtml2Canvas();
      const canvas = await html2canvas(document.body, {
        logging: false,
        useCORS: true,
        scale: 0.5,
        windowWidth: document.documentElement.scrollWidth,
        windowHeight: document.documentElement.scrollHeight
      });
      return canvas.toDataURL("image/jpeg", 0.5);
    } catch (e) {
      console.warn("[ErrorLens] Screenshot failed:", e);
      return null;
    }
  }
  function getDashboardUrl() {
    return detectApiBaseUrl();
  }

  // src/ui/styles.js
  var STYLES_ID = "errorlens-styles";
  function getStyles() {
    return `
    #errorlens-widget {
      position: fixed;
      top: 10px;
      right: 10px;
      z-index: 2147483647;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      user-select: none;
    }

    .el-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 16px;
      background: ${CONFIG.COLORS.GRADIENT};
      border-radius: 24px;
      color: white;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
      transition: background 0.3s ease, box-shadow 0.3s ease;
    }

    .el-pill:hover {
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
    }

    .el-pill.recording {
      background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
      box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
      animation: el-pulse 1.5s infinite;
    }

    .el-pill.done {
      background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
      box-shadow: 0 4px 15px rgba(34, 197, 94, 0.4);
    }

    .el-pill.sending {
      background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
      box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
    }

    @keyframes el-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.8; }
    }

    .el-logo {
      font-size: 16px;
    }

    .el-label {
      font-weight: 600;
      font-size: 13px;
    }

    .el-btn {
      background: rgba(255, 255, 255, 0.2);
      border: none;
      border-radius: 50%;
      width: 28px;
      height: 28px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 14px;
      transition: background 0.2s;
    }

    .el-btn:hover {
      background: rgba(255, 255, 255, 0.3);
    }

    .el-counter {
      background: rgba(255, 255, 255, 0.25);
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      min-width: 20px;
      text-align: center;
    }

    /* Modal */
    .el-modal {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2147483647;
      animation: el-fade-in 0.2s ease;
    }

    @keyframes el-fade-in {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .el-modal-content {
      background: linear-gradient(145deg, #1a1a2e 0%, #16213e 100%);
      border-radius: 16px;
      padding: 28px;
      max-width: 420px;
      width: 90%;
      color: white;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    }

    .el-modal h2 {
      margin: 0 0 16px;
      font-size: 20px;
      background: ${CONFIG.COLORS.GRADIENT};
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .el-modal p {
      margin: 8px 0;
      color: #a0a0b0;
      font-size: 14px;
    }

    .el-modal-actions {
      display: flex;
      gap: 10px;
      margin-top: 20px;
      flex-wrap: wrap;
    }

    .el-modal-btn {
      background: ${CONFIG.COLORS.GRADIENT};
      border: none;
      padding: 12px 20px;
      border-radius: 10px;
      color: white;
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      transition: transform 0.2s, opacity 0.2s;
    }

    .el-modal-btn:hover {
      transform: translateY(-1px);
      opacity: 0.95;
    }

    .el-modal-btn.secondary {
      background: rgba(255, 255, 255, 0.1);
    }

    /* Mode Menu */
    .el-mode-menu {
      position: fixed;
      top: 60px;
      right: 16px;
      background: ${CONFIG.COLORS.GRADIENT};
      border-radius: 16px;
      padding: 20px;
      box-shadow: 0 10px 40px rgba(102, 126, 234, 0.5);
      z-index: 2147483647;
      animation: el-slide-down 0.2s ease;
      min-width: 280px;
    }

    @keyframes el-slide-down {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .el-mode-menu h3 {
      color: white;
      margin: 0 0 16px;
      font-size: 16px;
      font-weight: 600;
    }

    .el-mode-option {
      background: rgba(255, 255, 255, 0.15);
      border: none;
      border-radius: 12px;
      padding: 14px 16px;
      margin-bottom: 10px;
      width: 100%;
      text-align: left;
      cursor: pointer;
      transition: background 0.2s;
      color: white;
    }

    .el-mode-option:hover {
      background: rgba(255, 255, 255, 0.25);
    }

    .el-mode-option:last-child {
      margin-bottom: 0;
    }

    .el-mode-option strong {
      display: block;
      font-size: 14px;
      margin-bottom: 4px;
    }

    .el-mode-option span {
      font-size: 12px;
      opacity: 0.8;
    }

    /* Spinner */
    .el-spinner {
      width: 20px;
      height: 20px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: el-spin 0.8s linear infinite;
    }

    @keyframes el-spin {
      to { transform: rotate(360deg); }
    }
  `;
  }
  function injectStyles() {
    if (document.getElementById(STYLES_ID))
      return;
    const style = document.createElement("style");
    style.id = STYLES_ID;
    style.textContent = getStyles();
    document.head.appendChild(style);
  }
  function removeStyles() {
    const style = document.getElementById(STYLES_ID);
    if (style)
      style.remove();
  }

  // src/utils/helpers.js
  function getTimestamp() {
    return (/* @__PURE__ */ new Date()).toISOString();
  }
  function isErrorStatus(status) {
    return status >= 400;
  }
  function headersToObject(headers) {
    const obj = {};
    if (headers instanceof Headers) {
      headers.forEach((value, key) => {
        obj[key] = value;
      });
    } else if (headers && typeof headers === "object") {
      Object.assign(obj, headers);
    }
    return obj;
  }
  function truncate(str, maxLength = 1e4) {
    if (!str)
      return str;
    if (typeof str !== "string")
      return str;
    if (str.length <= maxLength)
      return str;
    return str.substring(0, maxLength) + "... [truncated]";
  }
  function safeStringify(obj, maxLength = 5e4) {
    if (obj === void 0 || obj === null)
      return null;
    try {
      const str = JSON.stringify(obj);
      return truncate(str, maxLength);
    } catch (e) {
      return "[Unable to stringify]";
    }
  }
  function getStackTrace() {
    try {
      throw new Error();
    } catch (e) {
      return e.stack?.split("\n").slice(2).join("\n") || "";
    }
  }

  // src/interceptors/console.js
  var originalConsole = {
    log: console.log,
    warn: console.warn,
    error: console.error,
    info: console.info,
    debug: console.debug
  };
  function interceptConsole() {
    ["log", "warn", "error", "info", "debug"].forEach((method) => {
      console[method] = function(...args) {
        const state2 = getState();
        if (state2.isRecording) {
          try {
            const message = args.map((arg) => {
              try {
                if (arg instanceof Error) {
                  return `${arg.name}: ${arg.message}`;
                }
                return typeof arg === "object" ? JSON.stringify(arg) : String(arg);
              } catch {
                return String(arg);
              }
            }).join(" ");
            state2.consoleLogs.push({
              type: method,
              message: message.substring(0, 5e3),
              // Limit message size
              timestamp: getTimestamp(),
              stack: method === "error" ? getStackTrace() : void 0
            });
          } catch (e) {
          }
        }
        originalConsole[method].apply(console, args);
      };
    });
  }
  function restoreConsole() {
    Object.keys(originalConsole).forEach((method) => {
      console[method] = originalConsole[method];
    });
  }

  // src/interceptors/errors.js
  var originalOnError = null;
  var originalOnRejection = null;
  function setupErrorHandler() {
    originalOnError = window.onerror;
    window.onerror = function(message, source, lineno, colno, error) {
      const state2 = getState();
      if (state2.isRecording) {
        state2.jsExceptions.push({
          type: "error",
          message: String(message),
          source,
          lineno,
          colno,
          stack: error?.stack || "",
          timestamp: getTimestamp()
        });
      }
      if (originalOnError) {
        return originalOnError.apply(this, arguments);
      }
      return false;
    };
  }
  function restoreErrorHandler() {
    if (originalOnError !== null) {
      window.onerror = originalOnError;
      originalOnError = null;
    }
  }
  function setupRejectionHandler() {
    originalOnRejection = window.onunhandledrejection;
    window.onunhandledrejection = function(event) {
      const state2 = getState();
      if (state2.isRecording) {
        const reason = event.reason;
        state2.jsExceptions.push({
          type: "unhandledrejection",
          message: "Unhandled Promise Rejection: " + (reason?.message || String(reason)),
          stack: reason?.stack || "",
          timestamp: getTimestamp()
        });
      }
      if (originalOnRejection) {
        return originalOnRejection.apply(this, arguments);
      }
    };
  }
  function restoreRejectionHandler() {
    if (originalOnRejection !== null) {
      window.onunhandledrejection = originalOnRejection;
      originalOnRejection = null;
    }
  }

  // src/interceptors/fetch.js
  var originalFetch = window.fetch;
  function interceptFetch() {
    window.fetch = async function(input, init2 = {}) {
      const url = typeof input === "string" ? input : input.url || String(input);
      const method = (init2.method || "GET").toUpperCase();
      const startTime = Date.now();
      if (isJunkUrl(url)) {
        return originalFetch.apply(this, arguments);
      }
      const state2 = getState();
      try {
        const response = await originalFetch.apply(this, arguments);
        const duration = Date.now() - startTime;
        if (state2.isRecording) {
          const shouldRecord = state2.recordMode === "all" || isErrorStatus(response.status);
          if (shouldRecord) {
            const clone = response.clone();
            let responseBody = null;
            try {
              const contentType = response.headers.get("content-type") || "";
              if (contentType.includes("application/json")) {
                responseBody = await clone.json();
              } else if (contentType.includes("text/")) {
                responseBody = await clone.text();
              }
            } catch (e) {
              responseBody = "[Unable to parse body]";
            }
            const record = {
              type: "fetch",
              method,
              url,
              status: response.status,
              statusText: response.statusText,
              requestHeaders: headersToObject(init2.headers),
              requestBody: safeStringify(init2.body),
              responseHeaders: headersToObject(response.headers),
              responseBody: safeStringify(responseBody, 2e4),
              duration,
              timestamp: getTimestamp()
            };
            if (isErrorStatus(response.status)) {
              state2.networkErrors.push(record);
            }
            state2.recordedRequests.push(record);
          }
        }
        return response;
      } catch (error) {
        if (state2.isRecording) {
          state2.networkErrors.push({
            type: "fetch",
            method,
            url,
            error: error.message || "Network Error",
            duration: Date.now() - startTime,
            timestamp: getTimestamp()
          });
        }
        throw error;
      }
    };
  }
  function restoreFetch() {
    window.fetch = originalFetch;
  }

  // src/interceptors/xhr.js
  var XHRProto = XMLHttpRequest.prototype;
  var originalOpen = XHRProto.open;
  var originalSend = XHRProto.send;
  var originalSetHeader = XHRProto.setRequestHeader;
  function interceptXHR() {
    XHRProto.open = function(method, url) {
      this._errorlens = {
        method,
        url,
        requestHeaders: {},
        startTime: null
      };
      return originalOpen.apply(this, arguments);
    };
    XHRProto.setRequestHeader = function(name, value) {
      if (this._errorlens) {
        this._errorlens.requestHeaders[name] = value;
      }
      return originalSetHeader.apply(this, arguments);
    };
    XHRProto.send = function(body) {
      const state2 = getState();
      if (this._errorlens && !isJunkUrl(this._errorlens.url)) {
        this._errorlens.requestBody = body;
        this._errorlens.startTime = Date.now();
        const xhr = this;
        this.addEventListener("load", function() {
          if (state2.isRecording) {
            const duration = Date.now() - xhr._errorlens.startTime;
            const shouldRecord = state2.recordMode === "all" || isErrorStatus(xhr.status);
            if (shouldRecord) {
              const record = {
                type: "xhr",
                method: xhr._errorlens.method.toUpperCase(),
                url: xhr._errorlens.url,
                status: xhr.status,
                statusText: xhr.statusText,
                requestHeaders: xhr._errorlens.requestHeaders,
                requestBody: safeStringify(xhr._errorlens.requestBody),
                responseBody: safeStringify(xhr.responseText, 2e4),
                duration,
                timestamp: getTimestamp()
              };
              if (isErrorStatus(xhr.status)) {
                state2.networkErrors.push(record);
              }
              state2.recordedRequests.push(record);
            }
          }
        });
        this.addEventListener("error", function() {
          if (state2.isRecording) {
            state2.networkErrors.push({
              type: "xhr",
              method: xhr._errorlens.method.toUpperCase(),
              url: xhr._errorlens.url,
              error: "Network Error",
              duration: Date.now() - xhr._errorlens.startTime,
              timestamp: getTimestamp()
            });
          }
        });
        this.addEventListener("timeout", function() {
          if (state2.isRecording) {
            state2.networkErrors.push({
              type: "xhr",
              method: xhr._errorlens.method.toUpperCase(),
              url: xhr._errorlens.url,
              error: "Request Timeout",
              duration: Date.now() - xhr._errorlens.startTime,
              timestamp: getTimestamp()
            });
          }
        });
      }
      return originalSend.apply(this, arguments);
    };
  }
  function restoreXHR() {
    XHRProto.open = originalOpen;
    XHRProto.send = originalSend;
    XHRProto.setRequestHeader = originalSetHeader;
  }

  // src/interceptors/index.js
  function startInterceptors() {
    interceptConsole();
    setupErrorHandler();
    setupRejectionHandler();
    interceptFetch();
    interceptXHR();
    console.log("[ErrorLens] Interceptors started");
  }
  function stopInterceptors() {
    restoreConsole();
    restoreErrorHandler();
    restoreRejectionHandler();
    restoreFetch();
    restoreXHR();
    console.log("[ErrorLens] Interceptors stopped");
  }

  // src/ui/widget.js
  var widgetElement = null;
  var counterInterval = null;
  var currentModeMenu = null;
  function createWidget() {
    injectStyles();
    if (widgetElement) {
      widgetElement.remove();
    }
    widgetElement = document.createElement("div");
    widgetElement.id = "errorlens-widget";
    widgetElement.innerHTML = `
    <div class="el-pill" id="el-pill">
      <span class="el-logo">\u{1F50D}</span>
      <span class="el-label">ErrorLens</span>
      <button class="el-btn" id="el-record-btn" title="Start Recording">\u26AB</button>
      <span class="el-counter" id="el-counter" style="display:none">0</span>
      <button class="el-btn" id="el-dashboard-btn" title="Open Dashboard">\u{1F4CA}</button>
      <button class="el-btn" id="el-close-btn" title="Close">\u2715</button>
    </div>
  `;
    document.body.appendChild(widgetElement);
    makeWidgetDraggable(widgetElement);
    restoreWidgetPosition();
    document.getElementById("el-record-btn").addEventListener("click", handleRecordClick);
    document.getElementById("el-dashboard-btn").addEventListener("click", () => window.open(getDashboardUrl(), "_blank"));
    document.getElementById("el-close-btn").addEventListener("click", removeWidget);
    return widgetElement;
  }
  function makeWidgetDraggable(widget) {
    let isDragging = false;
    let hasMoved = false;
    let startX, startY, startLeft, startTop;
    function startDrag(e) {
      if (e.target.tagName === "BUTTON" || e.target.closest("button"))
        return;
      isDragging = true;
      hasMoved = false;
      const touch = e.touches ? e.touches[0] : e;
      startX = touch.clientX;
      startY = touch.clientY;
      const rect = widget.getBoundingClientRect();
      startLeft = rect.left;
      startTop = rect.top;
      e.preventDefault();
    }
    function drag(e) {
      if (!isDragging)
        return;
      const touch = e.touches ? e.touches[0] : e;
      const dx = touch.clientX - startX;
      const dy = touch.clientY - startY;
      if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
        hasMoved = true;
      }
      widget.style.left = startLeft + dx + "px";
      widget.style.top = startTop + dy + "px";
      widget.style.right = "auto";
    }
    function stopDrag() {
      if (isDragging && hasMoved) {
        localStorage.setItem("errorlens_widget_pos", JSON.stringify({
          left: widget.style.left,
          top: widget.style.top
        }));
      }
      isDragging = false;
    }
    widget.addEventListener("mousedown", startDrag);
    widget.addEventListener("touchstart", startDrag, { passive: false });
    document.addEventListener("mousemove", drag);
    document.addEventListener("touchmove", drag, { passive: false });
    document.addEventListener("mouseup", stopDrag);
    document.addEventListener("touchend", stopDrag);
  }
  function restoreWidgetPosition() {
    const saved = localStorage.getItem("errorlens_widget_pos");
    if (saved && widgetElement) {
      try {
        const pos = JSON.parse(saved);
        widgetElement.style.left = pos.left;
        widgetElement.style.top = pos.top;
        widgetElement.style.right = "auto";
      } catch (e) {
      }
    }
  }
  async function handleRecordClick(event) {
    event.stopPropagation();
    const state2 = getState();
    if (!state2.isRecording) {
      showModeMenu();
    } else {
      await stopRecording();
    }
  }
  function showModeMenu() {
    if (currentModeMenu) {
      currentModeMenu.remove();
      currentModeMenu = null;
      return;
    }
    const menu = document.createElement("div");
    menu.className = "el-mode-menu";
    menu.innerHTML = `
    <h3>\u{1F3AF} \u0412\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u0440\u0435\u0436\u0438\u043C \u0437\u0430\u043F\u0438\u0441\u0438</h3>
    <button class="el-mode-option" data-mode="errors">
      <strong>\u{1F41B} \u0422\u043E\u043B\u044C\u043A\u043E \u043E\u0448\u0438\u0431\u043A\u0438</strong>
      <span>Console.error, \u0441\u0435\u0442\u0435\u0432\u044B\u0435 \u043E\u0448\u0438\u0431\u043A\u0438 (4xx/5xx), JS exceptions</span>
    </button>
    <button class="el-mode-option" data-mode="all">
      <strong>\u{1F4E1} \u0412\u0441\u0435 \u0437\u0430\u043F\u0440\u043E\u0441\u044B</strong>
      <span>\u0412\u0441\u0435 HTTP \u0437\u0430\u043F\u0440\u043E\u0441\u044B + \u0432\u0441\u0435 console \u043B\u043E\u0433\u0438 + \u043E\u0448\u0438\u0431\u043A\u0438</span>
    </button>
  `;
    document.body.appendChild(menu);
    currentModeMenu = menu;
    menu.querySelectorAll(".el-mode-option").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const mode = e.currentTarget.dataset.mode;
        startRecording(mode);
        menu.remove();
        currentModeMenu = null;
      });
    });
    setTimeout(() => {
      document.addEventListener("click", function closeMenu(e) {
        if (!menu.contains(e.target) && !e.target.closest("#el-record-btn")) {
          menu.remove();
          currentModeMenu = null;
          document.removeEventListener("click", closeMenu);
        }
      });
    }, 100);
  }
  function startRecording(mode) {
    const state2 = getState();
    state2.isRecording = true;
    state2.recordMode = mode;
    state2.startTime = Date.now();
    startInterceptors();
    updateWidgetState("recording");
    startCounterUpdate();
    console.log(`[ErrorLens] Recording started (mode: ${mode})`);
  }
  async function stopRecording() {
    const state2 = getState();
    state2.isRecording = false;
    stopInterceptors();
    stopCounterUpdate();
    updateWidgetState("sending");
    try {
      state2.screenshot = await captureScreenshot();
    } catch (e) {
      console.warn("[ErrorLens] Screenshot failed:", e);
    }
    try {
      const result = await sendSession();
      updateWidgetState("done");
      showResultModal(result);
      console.log("[ErrorLens] Session saved:", result.id);
    } catch (error) {
      updateWidgetState("idle");
      showErrorModal(error);
      console.error("[ErrorLens] Failed to save session:", error);
    }
  }
  function updateWidgetState(newState) {
    const pill = document.getElementById("el-pill");
    const btn = document.getElementById("el-record-btn");
    const counter = document.getElementById("el-counter");
    const label = widgetElement.querySelector(".el-label");
    if (!pill)
      return;
    pill.classList.remove("recording", "done", "sending");
    switch (newState) {
      case "recording":
        pill.classList.add("recording");
        btn.textContent = "\u23F9";
        btn.title = "Stop Recording";
        counter.style.display = "inline";
        label.textContent = "Recording...";
        break;
      case "sending":
        pill.classList.add("sending");
        label.textContent = "Sending...";
        btn.innerHTML = '<span class="el-spinner"></span>';
        break;
      case "done":
        pill.classList.add("done");
        btn.textContent = "\u2713";
        label.textContent = "Done!";
        counter.style.display = "none";
        break;
      default:
        btn.textContent = "\u26AB";
        btn.title = "Start Recording";
        label.textContent = "ErrorLens";
        counter.style.display = "none";
    }
  }
  function startCounterUpdate() {
    stopCounterUpdate();
    counterInterval = setInterval(() => {
      const counter = document.getElementById("el-counter");
      const state2 = getState();
      if (counter && state2.isRecording) {
        const counts = getEventCounts();
        counter.textContent = counts.total;
      }
    }, 500);
  }
  function stopCounterUpdate() {
    if (counterInterval) {
      clearInterval(counterInterval);
      counterInterval = null;
    }
  }
  function showResultModal(result) {
    const counts = getEventCounts();
    const modal = document.createElement("div");
    modal.className = "el-modal";
    modal.innerHTML = `
    <div class="el-modal-content">
      <h2>\u2705 \u0421\u0435\u0441\u0441\u0438\u044F \u0437\u0430\u043F\u0438\u0441\u0430\u043D\u0430!</h2>
      <p><strong>ID:</strong> ${result.id?.substring(0, 8) || "N/A"}...</p>
      <p><strong>\u0421\u043E\u0431\u044B\u0442\u0438\u044F:</strong> ${counts.total} (\u043E\u0448\u0438\u0431\u043E\u043A: ${counts.errors}, \u0437\u0430\u043F\u0440\u043E\u0441\u043E\u0432: ${counts.requests})</p>
      <div class="el-modal-actions">
        <button class="el-modal-btn" onclick="window.open('${getDashboardUrl()}', '_blank'); this.closest('.el-modal').remove();">
          \u{1F4CA} \u041E\u0442\u043A\u0440\u044B\u0442\u044C Dashboard
        </button>
        <button class="el-modal-btn secondary" onclick="this.closest('.el-modal').remove();">
          \u0417\u0430\u043A\u0440\u044B\u0442\u044C
        </button>
      </div>
    </div>
  `;
    document.body.appendChild(modal);
    modal.addEventListener("click", (e) => {
      if (e.target === modal)
        modal.remove();
    });
    resetState();
  }
  function showErrorModal(error) {
    const modal = document.createElement("div");
    modal.className = "el-modal";
    modal.innerHTML = `
    <div class="el-modal-content">
      <h2>\u274C \u041E\u0448\u0438\u0431\u043A\u0430</h2>
      <p>${error.message || "\u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u0441\u043E\u0445\u0440\u0430\u043D\u0438\u0442\u044C \u0441\u0435\u0441\u0441\u0438\u044E"}</p>
      <div class="el-modal-actions">
        <button class="el-modal-btn" onclick="this.closest('.el-modal').remove();">
          \u0417\u0430\u043A\u0440\u044B\u0442\u044C
        </button>
      </div>
    </div>
  `;
    document.body.appendChild(modal);
  }
  function removeWidget() {
    stopCounterUpdate();
    stopInterceptors();
    if (currentModeMenu) {
      currentModeMenu.remove();
      currentModeMenu = null;
    }
    if (widgetElement) {
      widgetElement.remove();
      widgetElement = null;
    }
    removeStyles();
    resetState();
    window.__ERRORLENS_LOADED__ = false;
    console.log("[ErrorLens] Widget removed");
  }

  // src/index.js
  (function init() {
    if (window.__ERRORLENS_LOADED__) {
      const state2 = getState();
      if (state2.isRecording) {
        if (!confirm("ErrorLens \u0437\u0430\u043F\u0438\u0441\u044B\u0432\u0430\u0435\u0442 \u0441\u0435\u0441\u0441\u0438\u044E. \u041E\u0441\u0442\u0430\u043D\u043E\u0432\u0438\u0442\u044C \u0438 \u0437\u0430\u043A\u0440\u044B\u0442\u044C?")) {
          return;
        }
      }
      if (window.__errorLensResults) {
        const choice = confirm("\u0415\u0441\u0442\u044C \u0440\u0435\u0437\u0443\u043B\u044C\u0442\u0430\u0442\u044B \u043F\u0440\u043E\u0448\u043B\u043E\u0439 \u0437\u0430\u043F\u0438\u0441\u0438.\n\n\u041E\u041A = \u041F\u043E\u043A\u0430\u0437\u0430\u0442\u044C \u0440\u0435\u0437\u0443\u043B\u044C\u0442\u0430\u0442\u044B\n\u041E\u0442\u043C\u0435\u043D\u0430 = \u041D\u043E\u0432\u0430\u044F \u0437\u0430\u043F\u0438\u0441\u044C");
        if (choice) {
          console.log("[ErrorLens] Showing existing results");
        }
      }
      console.log("[ErrorLens] Removing existing instance...");
      removeWidget();
      window.__ERRORLENS_LOADED__ = false;
      return;
    }
    console.log(`[ErrorLens] v${CONFIG.VERSION} initializing...`);
    createWidget();
    window.__ERRORLENS_LOADED__ = true;
  })();
})();
