/**
 * ErrorLens Bookmarklet Recorder
 *
 * Stories 2.1 + 2.4 + 7.1:
 * - Intercepts console.log/warn/error
 * - Captures window.onerror and unhandledrejection
 * - Records timestamps for each event
 * - Floating UI widget (red dot = recording)
 * - Click to start/stop and send to backend
 * - Shows result in modal
 * - Record All mode for test generation (Epic 7)
 */
(function() {
    'use strict';

    // Handle re-launch: check if already loaded
    if (window.__errorLensLoaded) {
        const bar = document.getElementById('errorlens-bar');
        const widget = document.getElementById('errorlens-widget');
        const existingWidget = bar || widget;

        if (existingWidget) {
            const isRecording = window.__errorLensState && window.__errorLensState.isRecording;
            const hasResults = window.__errorLensResults;

            if (isRecording) {
                if (confirm('ErrorLens уже записывает.\n\nОстановить и начать заново?')) {
                    window.__errorLensReset();
                }
            } else if (hasResults) {
                const choice = confirm('Есть результаты прошлой записи.\n\nОК = Показать результаты\nОтмена = Новая запись');
                if (choice) {
                    window.__errorLensShowResults();
                } else {
                    window.__errorLensReset();
                }
            } else {
                // Idle state - widget exists, ready to use
                console.log('[ErrorLens] Already loaded, widget ready');
            }
            return;
        } else {
            // Flag is set but widget is gone - reset and continue
            console.log('[ErrorLens] Reinitializing (widget was removed)');
            window.__errorLensLoaded = false;
            window.__errorLensState = null;
            window.__errorLensResults = null;
        }
    }

    // Mark as loaded
    window.__errorLensLoaded = true;

    // Configuration - auto-detect production or use overrides
    const PROD_URL = 'https://errorlens-production.up.railway.app';
    const LOCAL_URL = 'http://localhost:8000';

    // Allow runtime override via window.__ERRORLENS_CONFIG__
    const userConfig = window.__ERRORLENS_CONFIG__ || {};

    // Auto-detect environment:
    // 1. Check if the SCRIPT was loaded from localhost (dev mode)
    // 2. Check if the PAGE is on localhost
    const currentScript = document.currentScript || document.querySelector('script[src*="recorder.js"]');
    const scriptSrc = currentScript ? currentScript.src : '';
    const isScriptFromLocalhost = scriptSrc.includes('localhost') || scriptSrc.includes('127.0.0.1');
    const isPageOnLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    // Use local backend if either script or page is on localhost
    const isLocalDev = isScriptFromLocalhost || isPageOnLocalhost;
    const autoBackendUrl = isLocalDev ? LOCAL_URL : PROD_URL;

    const CONFIG = {
        BACKEND_URL: userConfig.BACKEND_URL || autoBackendUrl,
        WIDGET_STYLE: userConfig.WIDGET_STYLE || 'new', // 'new' (pill) or 'classic' (floating button)
        WIDGET_SIZE: userConfig.WIDGET_SIZE || 60,     // For classic mode only
        USE_SESSIONS_API: userConfig.USE_SESSIONS_API !== false, // Use new /sessions endpoint (saves to DB)
        DASHBOARD_URL: userConfig.DASHBOARD_URL || (userConfig.BACKEND_URL || autoBackendUrl) + '/#/' // Dashboard at root with hash router
    };

    console.log('[ErrorLens] Config:', { backend: CONFIG.BACKEND_URL, dashboard: CONFIG.DASHBOARD_URL });

    // URL patterns to filter out (analytics, ads, static assets)
    const JUNK_URL_PATTERNS = [
        /google-analytics\.com/i,
        /googletagmanager\.com/i,
        /facebook\.com\/tr/i,
        /doubleclick\.net/i,
        /hotjar\.com/i,
        /segment\.io/i,
        /mixpanel\.com/i,
        /amplitude\.com/i,
        /sentry\.io/i,
        /newrelic\.com/i,
        /\.(png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot|css)(\?|$)/i,
        /\/_next\/static\//i,
        /\/static\/js\//i,
        /\/static\/css\//i,
        /\/favicon/i,
    ];

    // Check if URL is junk (analytics, static assets)
    function isJunkUrl(url) {
        return JUNK_URL_PATTERNS.some(pattern => pattern.test(url));
    }

    // Smart API URL detection
    // Many SPAs store API URL in global variables or meta tags
    function detectApiBaseUrl() {
        // Common global variable names for API URL
        const apiVarNames = [
            '__API_URL__',
            'API_URL',
            'API_BASE_URL',
            'apiUrl',
            'apiBaseUrl',
            'REACT_APP_API_URL',
            'VUE_APP_API_URL',
            'NEXT_PUBLIC_API_URL',
            '__NUXT__'
        ];

        // Check window variables
        for (const varName of apiVarNames) {
            if (window[varName] && typeof window[varName] === 'string') {
                console.log(`[ErrorLens] Detected API URL from window.${varName}: ${window[varName]}`);
                return window[varName];
            }
        }

        // Check for Nuxt.js config
        if (window.__NUXT__ && window.__NUXT__.config && window.__NUXT__.config.public) {
            const nuxtApi = window.__NUXT__.config.public.apiBase || window.__NUXT__.config.public.apiUrl;
            if (nuxtApi) {
                console.log(`[ErrorLens] Detected API URL from Nuxt config: ${nuxtApi}`);
                return nuxtApi;
            }
        }

        // Check meta tags
        const metaNames = ['api-url', 'api-base-url', 'apiUrl'];
        for (const name of metaNames) {
            const meta = document.querySelector(`meta[name="${name}"]`);
            if (meta && meta.content) {
                console.log(`[ErrorLens] Detected API URL from meta tag: ${meta.content}`);
                return meta.content;
            }
        }

        // Check for common API patterns in existing requests
        // Will be populated during recording
        return null;
    }

    // Normalize URL to use detected API base if applicable
    function normalizeApiUrl(url, detectedApiBase) {
        if (!detectedApiBase) return url;

        try {
            const urlObj = new URL(url);
            const apiObj = new URL(detectedApiBase);

            // If request goes to same origin but API is on different host
            // Check if this looks like an API request (has /api/ or common API patterns)
            const isApiRequest = /\/(api|auth|v\d+|graphql)\//i.test(urlObj.pathname);

            if (isApiRequest && urlObj.origin === window.location.origin && apiObj.origin !== window.location.origin) {
                // Rewrite URL to use actual API host
                const newUrl = apiObj.origin + urlObj.pathname + urlObj.search;
                console.log(`[ErrorLens] Normalized API URL: ${url} -> ${newUrl}`);
                return newUrl;
            }
        } catch (e) {
            // URL parsing failed, return original
        }

        return url;
    }

    // Detect API base URL on load
    const detectedApiBase = detectApiBaseUrl();

    // State
    const state = {
        isRecording: false,
        recordMode: 'errors', // 'errors' or 'all' (for test generation)
        startTime: null,
        consoleLogs: [],
        jsExceptions: [],
        networkErrors: [],
        recordedRequests: [], // Story 7.1: All HTTP exchanges for test generation
        requestIdCounter: 0,
        screenshot: null,
        detectedApiBase: detectedApiBase, // Smart API URL detection
        originalConsole: {
            log: console.log,
            warn: console.warn,
            error: console.error,
            info: console.info,
            debug: console.debug
        },
        originalOnError: window.onerror,
        originalOnUnhandledRejection: window.onunhandledrejection,
        originalFetch: window.fetch,
        originalXHROpen: XMLHttpRequest.prototype.open,
        originalXHRSend: XMLHttpRequest.prototype.send,
        lastResults: null  // Store last analysis results
    };

    // Expose state globally for re-launch handling
    window.__errorLensState = state;
    window.__errorLensResults = null;

    // Utility: Get ISO timestamp
    function getTimestamp() {
        return new Date().toISOString();
    }

    // Utility: Extract stack trace from Error object
    function getStackTrace(error) {
        if (!error) return null;
        if (error.stack) return error.stack;
        return null;
    }

    // Console interception
    function interceptConsole() {
        ['log', 'warn', 'error', 'info', 'debug'].forEach(level => {
            console[level] = function(...args) {
                // Call original console method
                state.originalConsole[level].apply(console, args);

                // Record if we're recording
                if (state.isRecording) {
                    const message = args.map(arg => {
                        if (typeof arg === 'object') {
                            try {
                                return JSON.stringify(arg, null, 2);
                            } catch (e) {
                                return String(arg);
                            }
                        }
                        return String(arg);
                    }).join(' ');

                    // Extract stack trace for errors
                    let stack = null;
                    if (level === 'error') {
                        const errorArg = args.find(arg => arg instanceof Error);
                        if (errorArg) {
                            stack = getStackTrace(errorArg);
                        } else {
                            // Try to get current stack trace
                            try {
                                throw new Error();
                            } catch (e) {
                                stack = getStackTrace(e);
                            }
                        }
                    }

                    state.consoleLogs.push({
                        timestamp: getTimestamp(),
                        level: level,
                        message: message,
                        stack: stack
                    });

                    updateEventCounter();
                }
            };
        });
    }

    // Restore original console
    function restoreConsole() {
        ['log', 'warn', 'error', 'info', 'debug'].forEach(level => {
            console[level] = state.originalConsole[level];
        });
    }

    // window.onerror handler
    function setupErrorHandler() {
        window.onerror = function(message, source, lineno, colno, error) {
            // Call original handler if exists
            if (state.originalOnError) {
                state.originalOnError.apply(window, arguments);
            }

            // Record if we're recording
            if (state.isRecording) {
                state.jsExceptions.push({
                    timestamp: getTimestamp(),
                    message: String(message),
                    source: source || null,
                    lineno: lineno || null,
                    colno: colno || null,
                    stack: getStackTrace(error)
                });

                updateEventCounter();
            }

            // Don't suppress default error handling
            return false;
        };
    }

    // Restore original error handler
    function restoreErrorHandler() {
        window.onerror = state.originalOnError;
    }

    // unhandledrejection handler
    function setupRejectionHandler() {
        window.onunhandledrejection = function(event) {
            // Call original handler if exists
            if (state.originalOnUnhandledRejection) {
                state.originalOnUnhandledRejection.apply(window, arguments);
            }

            // Record if we're recording
            if (state.isRecording) {
                const reason = event.reason;
                const message = reason instanceof Error ? reason.message : String(reason);
                const stack = reason instanceof Error ? getStackTrace(reason) : null;

                state.jsExceptions.push({
                    timestamp: getTimestamp(),
                    message: 'Unhandled Promise Rejection: ' + message,
                    source: null,
                    lineno: null,
                    colno: null,
                    stack: stack
                });

                updateEventCounter();
            }
        };
    }

    // Restore original rejection handler
    function restoreRejectionHandler() {
        window.onunhandledrejection = state.originalOnUnhandledRejection;
    }

    // Utility: Check if status code is an error (4xx or 5xx)
    function isErrorStatus(status) {
        return status >= 400;
    }

    // Utility: Extract headers as object
    function headersToObject(headers) {
        const obj = {};
        if (headers instanceof Headers) {
            headers.forEach((value, key) => {
                obj[key] = value;
            });
        } else if (headers && typeof headers === 'object') {
            Object.keys(headers).forEach(key => {
                obj[key] = headers[key];
            });
        }
        return obj;
    }

    // Utility: Safely read response body (clone to avoid consuming)
    async function safeReadBody(response) {
        try {
            const clone = response.clone();
            const text = await clone.text();
            // Limit body size to 10KB
            return text.length > 10240 ? text.substring(0, 10240) + '...[truncated]' : text;
        } catch (e) {
            return null;
        }
    }

    // Fetch interception
    function interceptFetch() {
        window.fetch = async function(input, init) {
            const startTime = Date.now();
            const method = (init && init.method) || 'GET';
            const originalUrl = typeof input === 'string' ? input : input.url;
            // Normalize URL to use real API host if detected
            const url = normalizeApiUrl(originalUrl, state.detectedApiBase);

            // Skip junk URLs in record-all mode
            if (state.recordMode === 'all' && isJunkUrl(originalUrl)) {
                return state.originalFetch.apply(window, arguments);
            }

            // Extract request headers and body
            const requestHeaders = init && init.headers ? headersToObject(init.headers) : {};
            const requestBody = init && init.body ? String(init.body).substring(0, 10240) : null;
            const contentType = requestHeaders['content-type'] || requestHeaders['Content-Type'] || null;

            try {
                const response = await state.originalFetch.apply(window, arguments);
                const duration = Date.now() - startTime;

                if (state.isRecording) {
                    const responseBody = await safeReadBody(response);
                    const responseHeaders = headersToObject(response.headers);
                    const timestamp = getTimestamp();

                    // Record error responses (4xx, 5xx) - original behavior
                    if (isErrorStatus(response.status)) {
                        state.networkErrors.push({
                            timestamp: timestamp,
                            type: 'fetch',
                            method: method,
                            url: url,
                            status: response.status,
                            status_text: response.statusText,
                            duration_ms: duration,
                            request_headers: requestHeaders,
                            request_body: requestBody,
                            response_headers: responseHeaders,
                            response_body: responseBody
                        });
                    }

                    // Story 7.1: Record ALL requests in 'all' mode for test generation
                    if (state.recordMode === 'all') {
                        state.recordedRequests.push({
                            id: ++state.requestIdCounter,
                            timestamp: timestamp,
                            request: {
                                timestamp: timestamp,
                                method: method,
                                url: url,
                                headers: requestHeaders,
                                body: requestBody,
                                content_type: contentType
                            },
                            response: {
                                status: response.status,
                                status_text: response.statusText,
                                headers: responseHeaders,
                                body: responseBody,
                                duration_ms: duration
                            }
                        });
                    }

                    updateEventCounter();
                }

                return response;
            } catch (error) {
                // Network error (no response at all)
                if (state.isRecording) {
                    const timestamp = getTimestamp();
                    const duration = Date.now() - startTime;

                    state.networkErrors.push({
                        timestamp: timestamp,
                        type: 'fetch',
                        method: method,
                        url: url,
                        status: 0,
                        status_text: 'Network Error',
                        duration_ms: duration,
                        request_headers: requestHeaders,
                        request_body: requestBody,
                        response_headers: null,
                        response_body: error.message
                    });

                    // Record failed request in 'all' mode too
                    if (state.recordMode === 'all') {
                        state.recordedRequests.push({
                            id: ++state.requestIdCounter,
                            timestamp: timestamp,
                            request: {
                                timestamp: timestamp,
                                method: method,
                                url: url,
                                headers: requestHeaders,
                                body: requestBody,
                                content_type: contentType
                            },
                            response: {
                                status: 0,
                                status_text: 'Network Error',
                                headers: {},
                                body: error.message,
                                duration_ms: duration
                            }
                        });
                    }

                    updateEventCounter();
                }
                throw error;
            }
        };
    }

    // Restore original fetch
    function restoreFetch() {
        window.fetch = state.originalFetch;
    }

    // XMLHttpRequest interception
    function interceptXHR() {
        XMLHttpRequest.prototype.open = function(method, url) {
            // Normalize URL to use real API host if detected
            const normalizedUrl = normalizeApiUrl(url, state.detectedApiBase);
            this._errorlens = {
                method: method,
                url: normalizedUrl,
                originalUrl: url,
                startTime: null,
                requestHeaders: {}
            };
            return state.originalXHROpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function(body) {
            const xhr = this;

            if (xhr._errorlens) {
                xhr._errorlens.startTime = Date.now();
                xhr._errorlens.requestBody = body ? String(body).substring(0, 10240) : null;
            }

            // Override setRequestHeader to capture headers
            const originalSetRequestHeader = xhr.setRequestHeader;
            xhr.setRequestHeader = function(name, value) {
                if (xhr._errorlens) {
                    xhr._errorlens.requestHeaders[name] = value;
                }
                return originalSetRequestHeader.apply(this, arguments);
            };

            // Listen for load event
            xhr.addEventListener('load', function() {
                if (!state.isRecording || !xhr._errorlens) return;

                // Skip junk URLs in record-all mode (use original URL for filtering)
                if (state.recordMode === 'all' && isJunkUrl(xhr._errorlens.originalUrl || xhr._errorlens.url)) return;

                const timestamp = getTimestamp();
                const duration = Date.now() - xhr._errorlens.startTime;

                // Extract response headers
                const responseHeaders = {};
                const headerString = xhr.getAllResponseHeaders();
                if (headerString) {
                    headerString.split('\r\n').forEach(line => {
                        const parts = line.split(': ');
                        if (parts.length === 2) {
                            responseHeaders[parts[0]] = parts[1];
                        }
                    });
                }

                const responseBody = xhr.responseText ? xhr.responseText.substring(0, 10240) : null;
                const contentType = xhr._errorlens.requestHeaders['content-type'] || xhr._errorlens.requestHeaders['Content-Type'] || null;

                // Record error responses (4xx, 5xx) - original behavior
                if (isErrorStatus(xhr.status)) {
                    state.networkErrors.push({
                        timestamp: timestamp,
                        type: 'xhr',
                        method: xhr._errorlens.method,
                        url: xhr._errorlens.url,
                        status: xhr.status,
                        status_text: xhr.statusText,
                        duration_ms: duration,
                        request_headers: xhr._errorlens.requestHeaders,
                        request_body: xhr._errorlens.requestBody,
                        response_headers: responseHeaders,
                        response_body: responseBody
                    });
                }

                // Story 7.1: Record ALL requests in 'all' mode for test generation
                if (state.recordMode === 'all') {
                    state.recordedRequests.push({
                        id: ++state.requestIdCounter,
                        timestamp: timestamp,
                        request: {
                            timestamp: timestamp,
                            method: xhr._errorlens.method,
                            url: xhr._errorlens.url,
                            headers: xhr._errorlens.requestHeaders,
                            body: xhr._errorlens.requestBody,
                            content_type: contentType
                        },
                        response: {
                            status: xhr.status,
                            status_text: xhr.statusText,
                            headers: responseHeaders,
                            body: responseBody,
                            duration_ms: duration
                        }
                    });
                }

                updateEventCounter();
            });

            // Listen for error event (network error)
            xhr.addEventListener('error', function() {
                if (!state.isRecording || !xhr._errorlens) return;

                const timestamp = getTimestamp();
                const duration = Date.now() - xhr._errorlens.startTime;
                const contentType = xhr._errorlens.requestHeaders['content-type'] || xhr._errorlens.requestHeaders['Content-Type'] || null;

                state.networkErrors.push({
                    timestamp: timestamp,
                    type: 'xhr',
                    method: xhr._errorlens.method,
                    url: xhr._errorlens.url,
                    status: 0,
                    status_text: 'Network Error',
                    duration_ms: duration,
                    request_headers: xhr._errorlens.requestHeaders,
                    request_body: xhr._errorlens.requestBody,
                    response_headers: null,
                    response_body: null
                });

                // Record failed request in 'all' mode too
                if (state.recordMode === 'all') {
                    state.recordedRequests.push({
                        id: ++state.requestIdCounter,
                        timestamp: timestamp,
                        request: {
                            timestamp: timestamp,
                            method: xhr._errorlens.method,
                            url: xhr._errorlens.url,
                            headers: xhr._errorlens.requestHeaders,
                            body: xhr._errorlens.requestBody,
                            content_type: contentType
                        },
                        response: {
                            status: 0,
                            status_text: 'Network Error',
                            headers: {},
                            body: null,
                            duration_ms: duration
                        }
                    });
                }

                updateEventCounter();
            });

            return state.originalXHRSend.apply(this, arguments);
        };
    }

    // Restore original XHR
    function restoreXHR() {
        XMLHttpRequest.prototype.open = state.originalXHROpen;
        XMLHttpRequest.prototype.send = state.originalXHRSend;
    }

    // html2canvas CDN URL
    const HTML2CANVAS_CDN = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';

    // Load html2canvas dynamically
    function loadHtml2Canvas() {
        return new Promise((resolve, reject) => {
            // Check if already loaded
            if (window.html2canvas) {
                resolve(window.html2canvas);
                return;
            }

            // Check if script is already loading
            if (document.querySelector(`script[src="${HTML2CANVAS_CDN}"]`)) {
                // Wait for it to load
                const checkInterval = setInterval(() => {
                    if (window.html2canvas) {
                        clearInterval(checkInterval);
                        resolve(window.html2canvas);
                    }
                }, 100);
                return;
            }

            // Load script
            const script = document.createElement('script');
            script.src = HTML2CANVAS_CDN;
            script.onload = () => {
                console.log('[ErrorLens] html2canvas loaded');
                resolve(window.html2canvas);
            };
            script.onerror = () => {
                console.warn('[ErrorLens] Failed to load html2canvas, skipping screenshot');
                resolve(null);
            };
            document.head.appendChild(script);
        });
    }

    // Capture screenshot using html2canvas
    async function captureScreenshot() {
        try {
            const html2canvas = await loadHtml2Canvas();
            if (!html2canvas) {
                return null;
            }

            // Hide our widget temporarily
            const widget = document.getElementById('errorlens-widget');
            const modal = document.getElementById('errorlens-modal');
            if (widget) widget.style.display = 'none';
            if (modal) modal.style.display = 'none';

            // Capture
            const canvas = await html2canvas(document.body, {
                logging: false,
                useCORS: true,
                allowTaint: true,
                scale: 0.5, // Reduce size for faster upload
                windowWidth: document.documentElement.scrollWidth,
                windowHeight: document.documentElement.scrollHeight
            });

            // Restore widget
            if (widget) widget.style.display = 'flex';
            if (modal) modal.style.display = 'flex';

            // Convert to base64 with reduced quality
            const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
            console.log('[ErrorLens] Screenshot captured, size:', Math.round(dataUrl.length / 1024), 'KB');

            return dataUrl;
        } catch (error) {
            console.warn('[ErrorLens] Screenshot failed:', error.message);
            return null;
        }
    }

    // UI Widget - creates either new top bar or classic floating button
    function createWidget() {
        // Check if widget already exists
        if (document.getElementById('errorlens-widget') || document.getElementById('errorlens-bar')) {
            console.log('[ErrorLens] Widget already exists');
            return;
        }

        // Add common styles
        if (!document.getElementById('errorlens-style')) {
            const style = document.createElement('style');
            style.id = 'errorlens-style';
            style.textContent = `
                @keyframes errorlens-pulse {
                    0%, 100% { box-shadow: 0 4px 20px rgba(244, 67, 54, 0.4); }
                    50% { box-shadow: 0 4px 30px rgba(244, 67, 54, 0.7); }
                }
                @keyframes errorlens-fade-in {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes errorlens-bounce {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-5px); }
                }
                @keyframes errorlens-point {
                    0%, 100% { transform: translateX(0); }
                    50% { transform: translateX(5px); }
                }
                .errorlens-widget {
                    position: fixed;
                    top: 16px;
                    right: 16px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 8px 12px 8px 8px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 50px;
                    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
                    z-index: 2147483647;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    animation: errorlens-fade-in 0.3s ease;
                    transition: background 0.3s ease, box-shadow 0.3s ease;
                    user-select: none;
                }
                .errorlens-widget.recording {
                    background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                    animation: errorlens-pulse 1.5s infinite;
                }
                .errorlens-widget.done {
                    background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%);
                    box-shadow: 0 4px 20px rgba(76, 175, 80, 0.4);
                }
                .errorlens-record-btn {
                    width: 36px;
                    height: 36px;
                    border: none;
                    border-radius: 50%;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: white;
                    color: #667eea;
                    transition: all 0.2s ease;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                }
                .errorlens-record-btn:hover {
                    transform: scale(1.1);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                }
                .errorlens-record-btn svg {
                    width: 18px;
                    height: 18px;
                }
                .errorlens-widget.recording .errorlens-record-btn {
                    color: #f44336;
                }
                .errorlens-label {
                    color: white;
                    font-size: 13px;
                    font-weight: 600;
                    letter-spacing: 0.3px;
                    white-space: nowrap;
                }
                .errorlens-counter {
                    background: rgba(255,255,255,0.25);
                    color: white;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 4px 10px;
                    border-radius: 12px;
                    min-width: 20px;
                    text-align: center;
                    white-space: nowrap;
                }
                .errorlens-close {
                    width: 24px;
                    height: 24px;
                    border: none;
                    border-radius: 50%;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    font-size: 14px;
                    transition: all 0.2s ease;
                    margin-left: 4px;
                }
                .errorlens-close:hover {
                    background: rgba(255,255,255,0.35);
                }
                .errorlens-results-btn {
                    background: rgba(255,255,255,0.9);
                    color: #388E3C;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 15px;
                    font-size: 12px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                .errorlens-results-btn:hover {
                    background: white;
                    transform: scale(1.05);
                }
                /* Onboarding tooltip - gradient style */
                .errorlens-tooltip {
                    position: fixed;
                    top: 70px;
                    right: 16px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 16px;
                    padding: 20px 24px;
                    box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4);
                    z-index: 2147483646;
                    max-width: 300px;
                    animation: errorlens-fade-in 0.4s ease;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                .errorlens-tooltip::before {
                    content: '';
                    position: absolute;
                    top: -10px;
                    right: 24px;
                    width: 20px;
                    height: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    transform: rotate(45deg);
                }
                .errorlens-tooltip-icon {
                    width: 48px;
                    height: 48px;
                    background: rgba(255,255,255,0.2);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-bottom: 12px;
                    font-size: 24px;
                    animation: errorlens-bounce 2s infinite;
                }
                .errorlens-tooltip-title {
                    font-size: 16px;
                    font-weight: 700;
                    color: white;
                    margin-bottom: 8px;
                }
                .errorlens-tooltip-text {
                    font-size: 13px;
                    color: rgba(255,255,255,0.9);
                    line-height: 1.6;
                    margin-bottom: 16px;
                }
                .errorlens-tooltip-steps {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    margin-bottom: 16px;
                }
                .errorlens-tooltip-step {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-size: 12px;
                    color: rgba(255,255,255,0.9);
                }
                .errorlens-tooltip-step-num {
                    width: 22px;
                    height: 22px;
                    background: rgba(255,255,255,0.25);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 700;
                    font-size: 11px;
                    color: white;
                }
                .errorlens-tooltip-buttons {
                    display: flex;
                    gap: 10px;
                    align-items: center;
                }
                .errorlens-tooltip-dismiss {
                    background: white;
                    color: #667eea;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 25px;
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }
                .errorlens-tooltip-dismiss:hover {
                    transform: scale(1.05);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.15);
                }
                .errorlens-tooltip-skip {
                    background: none;
                    border: none;
                    color: rgba(255,255,255,0.7);
                    font-size: 12px;
                    cursor: pointer;
                }
                .errorlens-tooltip-skip:hover {
                    color: white;
                }
                /* Dashboard button */
                .errorlens-dashboard-btn {
                    width: 28px;
                    height: 28px;
                    border: none;
                    border-radius: 50%;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    transition: all 0.2s ease;
                }
                .errorlens-dashboard-btn:hover {
                    background: rgba(255,255,255,0.35);
                    transform: scale(1.1);
                }
                .errorlens-dashboard-btn svg {
                    width: 14px;
                    height: 14px;
                }
            `;
            document.head.appendChild(style);
        }

        if (CONFIG.WIDGET_STYLE === 'new') {
            createTopBarWidget();
        } else {
            createClassicWidget();
        }

        console.log('[ErrorLens] Widget created');
    }

    // New beautiful widget with gradient design
    function createTopBarWidget() {
        const widget = document.createElement('div');
        widget.id = 'errorlens-bar';
        widget.className = 'errorlens-widget';

        // Record/Stop button with SVG icons
        const recordBtn = document.createElement('button');
        recordBtn.id = 'errorlens-record-btn';
        recordBtn.className = 'errorlens-record-btn';
        recordBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>`;
        recordBtn.title = 'Начать запись';
        recordBtn.addEventListener('click', handleRecordClick);
        widget.appendChild(recordBtn);

        // Label
        const label = document.createElement('span');
        label.id = 'errorlens-label';
        label.className = 'errorlens-label';
        label.textContent = 'ErrorLens';
        widget.appendChild(label);

        // Event counter (hidden until recording)
        const counter = document.createElement('div');
        counter.id = 'errorlens-counter';
        counter.className = 'errorlens-counter';
        counter.style.display = 'none';
        counter.textContent = '0';
        widget.appendChild(counter);

        // Result button (hidden until done)
        const resultBtn = document.createElement('button');
        resultBtn.id = 'errorlens-result-link';
        resultBtn.className = 'errorlens-results-btn';
        resultBtn.style.display = 'none';
        resultBtn.textContent = 'Результаты';
        widget.appendChild(resultBtn);

        // Dashboard button (sessions)
        const dashboardBtn = document.createElement('button');
        dashboardBtn.className = 'errorlens-dashboard-btn';
        dashboardBtn.title = 'Открыть сессии';
        dashboardBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>`;
        dashboardBtn.addEventListener('click', () => {
            window.open(CONFIG.DASHBOARD_URL, '_blank');
        });
        widget.appendChild(dashboardBtn);

        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'errorlens-close';
        closeBtn.innerHTML = '×';
        closeBtn.title = 'Закрыть';
        closeBtn.addEventListener('click', removeWidget);
        widget.appendChild(closeBtn);

        document.body.appendChild(widget);

        // Enable drag-and-drop
        makeWidgetDraggable(widget);

        // Show onboarding if first time
        showOnboarding();
    }

    // Make widget draggable
    function makeWidgetDraggable(widget) {
        let isDragging = false;
        let hasMoved = false;
        let startX, startY;
        let initialRight, initialTop;

        widget.addEventListener('mousedown', startDrag);
        widget.addEventListener('touchstart', startDrag, { passive: false });

        function startDrag(e) {
            // Don't drag if clicking on a button
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
                return;
            }

            // Prevent text selection
            e.preventDefault();

            isDragging = true;
            hasMoved = false;
            widget.style.cursor = 'grabbing';

            // Get initial position
            const rect = widget.getBoundingClientRect();
            initialRight = window.innerWidth - rect.right;
            initialTop = rect.top;

            // Get start coordinates
            if (e.type === 'touchstart') {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
            } else {
                startX = e.clientX;
                startY = e.clientY;
            }

            // Add move and end listeners
            document.addEventListener('mousemove', drag);
            document.addEventListener('mouseup', stopDrag);
            document.addEventListener('touchmove', drag, { passive: false });
            document.addEventListener('touchend', stopDrag);
        }

        function drag(e) {
            if (!isDragging) return;
            e.preventDefault();

            let currentX, currentY;
            if (e.type === 'touchmove') {
                currentX = e.touches[0].clientX;
                currentY = e.touches[0].clientY;
            } else {
                currentX = e.clientX;
                currentY = e.clientY;
            }

            // Calculate new position
            const deltaX = currentX - startX;
            const deltaY = currentY - startY;

            // Check if actually moved (threshold of 3px)
            if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) {
                hasMoved = true;
            }

            let newRight = initialRight - deltaX;
            let newTop = initialTop + deltaY;

            // Constrain to viewport
            const rect = widget.getBoundingClientRect();
            const maxRight = window.innerWidth - rect.width - 10;
            const maxTop = window.innerHeight - rect.height - 10;

            newRight = Math.max(10, Math.min(newRight, maxRight));
            newTop = Math.max(10, Math.min(newTop, maxTop));

            // Apply position
            widget.style.right = newRight + 'px';
            widget.style.top = newTop + 'px';
        }

        function stopDrag() {
            isDragging = false;
            widget.style.cursor = 'grab';

            // Save position to localStorage only if moved
            if (hasMoved) {
                const rect = widget.getBoundingClientRect();
                localStorage.setItem('errorlens_widget_pos', JSON.stringify({
                    right: window.innerWidth - rect.right,
                    top: rect.top
                }));
            }

            // Remove listeners
            document.removeEventListener('mousemove', drag);
            document.removeEventListener('mouseup', stopDrag);
            document.removeEventListener('touchmove', drag);
            document.removeEventListener('touchend', stopDrag);
        }

        // Restore saved position
        const savedPos = localStorage.getItem('errorlens_widget_pos');
        if (savedPos) {
            try {
                const pos = JSON.parse(savedPos);
                widget.style.right = pos.right + 'px';
                widget.style.top = pos.top + 'px';
            } catch (e) {
                // Ignore invalid saved position
            }
        }

        // Set initial cursor
        widget.style.cursor = 'grab';
    }

    // Show onboarding tooltip for first-time users
    function showOnboarding() {
        // Check if user has seen onboarding
        const hasSeenOnboarding = localStorage.getItem('errorlens_onboarding_seen');
        if (hasSeenOnboarding) return;

        const tooltip = document.createElement('div');
        tooltip.id = 'errorlens-tooltip';
        tooltip.className = 'errorlens-tooltip';
        tooltip.innerHTML = `
            <div class="errorlens-tooltip-icon">🔍</div>
            <div class="errorlens-tooltip-title">Добро пожаловать в ErrorLens!</div>
            <div class="errorlens-tooltip-text">
                Инструмент для записи и анализа ошибок на веб-страницах
            </div>
            <div class="errorlens-tooltip-steps">
                <div class="errorlens-tooltip-step">
                    <span class="errorlens-tooltip-step-num">1</span>
                    <span>Нажмите ● для начала записи</span>
                </div>
                <div class="errorlens-tooltip-step">
                    <span class="errorlens-tooltip-step-num">2</span>
                    <span>Выполните действия на странице</span>
                </div>
                <div class="errorlens-tooltip-step">
                    <span class="errorlens-tooltip-step-num">3</span>
                    <span>Нажмите ■ для анализа ошибок</span>
                </div>
            </div>
            <div class="errorlens-tooltip-buttons">
                <button class="errorlens-tooltip-dismiss" id="errorlens-start-tour">Начать!</button>
                <button class="errorlens-tooltip-skip" id="errorlens-skip-tour">Не показывать</button>
            </div>
        `;

        document.body.appendChild(tooltip);

        document.getElementById('errorlens-start-tour').addEventListener('click', () => {
            tooltip.remove();
        });

        document.getElementById('errorlens-skip-tour').addEventListener('click', () => {
            localStorage.setItem('errorlens_onboarding_seen', 'true');
            tooltip.remove();
        });

        // Auto-hide after 15 seconds
        setTimeout(() => {
            if (document.getElementById('errorlens-tooltip')) {
                tooltip.remove();
            }
        }, 15000);
    }

    // Handle record button click in new UI
    function handleRecordClick(event) {
        if (!state.isRecording) {
            // Show mode selection menu
            showModeMenuForPill(event);
        } else {
            stopRecordingAndSend();
        }
    }

    // Show mode selection menu for pill widget
    function showModeMenuForPill(event) {
        // Remove existing menu if any
        const existingMenu = document.getElementById('errorlens-mode-menu');
        if (existingMenu) existingMenu.remove();

        const menu = document.createElement('div');
        menu.id = 'errorlens-mode-menu';
        menu.style.cssText = `
            position: fixed;
            top: 70px;
            right: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.5);
            z-index: 2147483647;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            overflow: hidden;
            min-width: 280px;
            padding: 16px;
            animation: errorlens-fade-in 0.2s ease;
        `;

        // Menu title
        const title = document.createElement('div');
        title.style.cssText = `
            color: white;
            font-size: 15px;
            font-weight: 700;
            padding: 0 4px 12px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.2);
            margin-bottom: 12px;
        `;
        title.textContent = 'Выберите режим записи';
        menu.appendChild(title);

        // Option 1: Record errors only
        const errorsOption = document.createElement('div');
        errorsOption.style.cssText = `
            padding: 14px 16px;
            cursor: pointer;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            margin-bottom: 8px;
            transition: all 0.2s;
        `;
        errorsOption.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <span style="font-size: 20px;">⚠️</span>
                <span style="font-weight: 600; color: white; font-size: 14px;">Только ошибки</span>
            </div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.85); margin-left: 30px; line-height: 1.4;">
                Записывает ошибки консоли и сети (4xx/5xx).<br>
                <span style="opacity: 0.7;">Подходит для отладки багов</span>
            </div>
        `;
        errorsOption.addEventListener('mouseenter', () => {
            errorsOption.style.background = 'rgba(255, 255, 255, 0.25)';
            errorsOption.style.transform = 'scale(1.02)';
        });
        errorsOption.addEventListener('mouseleave', () => {
            errorsOption.style.background = 'rgba(255, 255, 255, 0.15)';
            errorsOption.style.transform = 'scale(1)';
        });
        errorsOption.addEventListener('click', () => {
            menu.remove();
            startRecording('errors');
            updateBarToRecording();
        });

        // Option 2: Record all requests
        const allOption = document.createElement('div');
        allOption.style.cssText = `
            padding: 14px 16px;
            cursor: pointer;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            transition: all 0.2s;
        `;
        allOption.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <span style="font-size: 20px;">📡</span>
                <span style="font-weight: 600; color: white; font-size: 14px;">Все запросы</span>
            </div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.85); margin-left: 30px; line-height: 1.4;">
                Записывает все HTTP запросы целиком.<br>
                <span style="opacity: 0.7;">Для генерации Postman/pytest тестов</span>
            </div>
        `;
        allOption.addEventListener('mouseenter', () => {
            allOption.style.background = 'rgba(255, 255, 255, 0.25)';
            allOption.style.transform = 'scale(1.02)';
        });
        allOption.addEventListener('mouseleave', () => {
            allOption.style.background = 'rgba(255, 255, 255, 0.15)';
            allOption.style.transform = 'scale(1)';
        });
        allOption.addEventListener('click', () => {
            menu.remove();
            startRecording('all');
            updateBarToRecording();
        });

        menu.appendChild(errorsOption);
        menu.appendChild(allOption);
        document.body.appendChild(menu);

        // Close menu on outside click
        const closeMenu = (e) => {
            if (!menu.contains(e.target) && e.target.id !== 'errorlens-record-btn') {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        };
        setTimeout(() => document.addEventListener('click', closeMenu), 100);
    }

    // Update widget to recording state
    function updateBarToRecording() {
        const widget = document.getElementById('errorlens-bar');
        const recordBtn = document.getElementById('errorlens-record-btn');
        const label = document.getElementById('errorlens-label');
        const counter = document.getElementById('errorlens-counter');
        const tooltip = document.getElementById('errorlens-tooltip');

        // Hide onboarding tooltip if visible
        if (tooltip) tooltip.remove();

        if (widget) {
            widget.className = 'errorlens-widget recording';
        }
        if (recordBtn) {
            recordBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>`;
            recordBtn.title = 'Остановить запись';
        }
        if (label) {
            label.textContent = 'Запись...';
        }
        if (counter) {
            counter.style.display = 'block';
        }
    }

    // Update widget to done state
    function updateBarToDone(result) {
        const widget = document.getElementById('errorlens-bar');
        const recordBtn = document.getElementById('errorlens-record-btn');
        const label = document.getElementById('errorlens-label');
        const counter = document.getElementById('errorlens-counter');
        const resultLink = document.getElementById('errorlens-result-link');

        if (widget) {
            widget.className = 'errorlens-widget done';
        }
        if (recordBtn) {
            recordBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>`;
            recordBtn.title = 'Новая запись';
        }
        if (label) {
            label.textContent = 'Готово!';
        }
        if (counter) {
            counter.style.display = 'none';
        }
        if (resultLink) {
            resultLink.style.display = 'block';
            resultLink.onclick = () => showResult(result);
        }
    }

    // Update widget to idle state
    function updateBarToIdle() {
        const widget = document.getElementById('errorlens-bar');
        const recordBtn = document.getElementById('errorlens-record-btn');
        const label = document.getElementById('errorlens-label');
        const counter = document.getElementById('errorlens-counter');
        const resultLink = document.getElementById('errorlens-result-link');

        if (widget) {
            widget.className = 'errorlens-widget';
        }
        if (recordBtn) {
            recordBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>`;
            recordBtn.title = 'Начать запись';
        }
        if (label) {
            label.textContent = 'ErrorLens';
        }
        if (counter) {
            counter.style.display = 'none';
            counter.textContent = '0';
        }
        if (resultLink) {
            resultLink.style.display = 'none';
        }
    }

    // Remove widget and cleanup
    function removeWidget() {
        const bar = document.getElementById('errorlens-bar');
        const widget = document.getElementById('errorlens-widget');
        const modal = document.getElementById('errorlens-modal');
        const menu = document.getElementById('errorlens-mode-menu');
        const tooltip = document.getElementById('errorlens-tooltip');

        if (bar) bar.remove();
        if (widget) widget.remove();
        if (modal) modal.remove();
        if (menu) menu.remove();
        if (tooltip) tooltip.remove();

        // Restore handlers if recording
        if (state.isRecording) {
            state.isRecording = false;
            restoreConsole();
            restoreErrorHandler();
            restoreRejectionHandler();
            restoreFetch();
            restoreXHR();
        }

        console.log('[ErrorLens] Widget removed');
    }

    // Classic floating button widget (original design)
    function createClassicWidget() {
        const widget = document.createElement('div');
        widget.id = 'errorlens-widget';
        widget.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: ${CONFIG.WIDGET_SIZE}px;
            height: ${CONFIG.WIDGET_SIZE}px;
            border-radius: 50%;
            background: #ff4444;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            cursor: pointer;
            z-index: 999999;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            user-select: none;
        `;

        // Event counter
        const counter = document.createElement('div');
        counter.id = 'errorlens-counter';
        counter.style.cssText = `
            color: white;
            font-size: 14px;
            font-weight: bold;
            font-family: Arial, sans-serif;
        `;
        counter.textContent = '0';
        widget.appendChild(counter);

        // Click handler
        widget.addEventListener('click', handleWidgetClick);

        document.body.appendChild(widget);
    }

    // Update event counter in widget
    function updateEventCounter() {
        const counter = document.getElementById('errorlens-counter');
        if (counter) {
            const errors = state.consoleLogs.length + state.jsExceptions.length + state.networkErrors.length;
            const requests = state.recordedRequests ? state.recordedRequests.length : 0;
            // Show format: errors / requests (if recording all)
            if (state.recordMode === 'all' && requests > 0) {
                counter.textContent = `${errors} / ${requests}`;
                counter.title = `${errors} ошибок, ${requests} запросов`;
            } else {
                counter.textContent = errors.toString();
                counter.title = `${errors} ошибок`;
            }
        }
    }

    // Handle widget click
    function handleWidgetClick(event) {
        if (!state.isRecording) {
            // Show mode selection menu
            showModeMenu(event);
        } else {
            stopRecordingAndSend();
        }
    }

    // Show recording mode selection menu
    function showModeMenu(event) {
        // Remove existing menu if any
        const existingMenu = document.getElementById('errorlens-mode-menu');
        if (existingMenu) existingMenu.remove();

        const menu = document.createElement('div');
        menu.id = 'errorlens-mode-menu';
        menu.style.cssText = `
            position: fixed;
            bottom: 90px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.5);
            z-index: 1000000;
            font-family: Arial, sans-serif;
            overflow: hidden;
            padding: 8px;
            animation: fadeInUp 0.2s ease;
        `;

        // Add animation
        const styleEl = document.createElement('style');
        styleEl.textContent = `
            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        `;
        menu.appendChild(styleEl);

        // Menu title
        const title = document.createElement('div');
        title.style.cssText = `
            color: white;
            font-size: 13px;
            font-weight: 600;
            padding: 8px 12px 12px;
            text-align: center;
            opacity: 0.9;
        `;
        title.textContent = 'Выберите режим записи';
        menu.appendChild(title);

        // Option 1: Record errors only
        const errorsOption = document.createElement('div');
        errorsOption.style.cssText = `
            padding: 14px 18px;
            cursor: pointer;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            margin-bottom: 8px;
            transition: all 0.2s;
        `;
        errorsOption.innerHTML = `
            <div style="font-weight: 600; color: white; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 18px;">⚠️</span> Только ошибки
            </div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 4px; margin-left: 26px;">Записывать 4xx/5xx ошибки</div>
        `;
        errorsOption.addEventListener('mouseenter', () => {
            errorsOption.style.background = 'rgba(255, 255, 255, 0.25)';
            errorsOption.style.transform = 'scale(1.02)';
        });
        errorsOption.addEventListener('mouseleave', () => {
            errorsOption.style.background = 'rgba(255, 255, 255, 0.15)';
            errorsOption.style.transform = 'scale(1)';
        });
        errorsOption.addEventListener('click', () => {
            menu.remove();
            startRecording('errors');
        });

        // Option 2: Record all requests
        const allOption = document.createElement('div');
        allOption.style.cssText = `
            padding: 14px 18px;
            cursor: pointer;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            transition: all 0.2s;
        `;
        allOption.innerHTML = `
            <div style="font-weight: 600; color: white; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 18px;">📡</span> Все запросы
            </div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 4px; margin-left: 26px;">Для генерации тестов</div>
        `;
        allOption.addEventListener('mouseenter', () => {
            allOption.style.background = 'rgba(255, 255, 255, 0.25)';
            allOption.style.transform = 'scale(1.02)';
        });
        allOption.addEventListener('mouseleave', () => {
            allOption.style.background = 'rgba(255, 255, 255, 0.15)';
            allOption.style.transform = 'scale(1)';
        });
        allOption.addEventListener('click', () => {
            menu.remove();
            startRecording('all');
        });

        menu.appendChild(errorsOption);
        menu.appendChild(allOption);
        document.body.appendChild(menu);

        // Close menu on outside click
        const closeMenu = (e) => {
            if (!menu.contains(e.target) && e.target !== document.getElementById('errorlens-widget')) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        };
        setTimeout(() => document.addEventListener('click', closeMenu), 100);
    }

    // Start recording
    function startRecording(mode = 'errors') {
        state.isRecording = true;
        state.recordMode = mode; // 'errors' or 'all'
        state.startTime = Date.now();
        state.consoleLogs = [];
        state.jsExceptions = [];
        state.networkErrors = [];
        state.recordedRequests = [];
        state.requestIdCounter = 0;
        state.screenshot = null;

        // Setup interceptors
        interceptConsole();
        setupErrorHandler();
        setupRejectionHandler();
        interceptFetch();
        interceptXHR();

        // Update widget UI based on style
        if (CONFIG.WIDGET_STYLE === 'classic') {
            const widget = document.getElementById('errorlens-widget');
            if (widget) {
                widget.style.background = mode === 'all' ? '#2196F3' : '#ff0000';
                widget.style.animation = 'pulse-scale 1.5s infinite';
            }
        }

        updateEventCounter();
        console.log('[ErrorLens] Recording started');
    }

    // Stop recording and send to backend
    async function stopRecordingAndSend() {
        state.isRecording = false;
        const duration = Date.now() - state.startTime;

        // Restore original handlers
        restoreConsole();
        restoreErrorHandler();
        restoreRejectionHandler();
        restoreFetch();
        restoreXHR();

        // Update widget UI - show "capturing" state
        const widget = document.getElementById('errorlens-widget');
        if (widget) {
            widget.style.background = '#ffaa00';
            widget.style.animation = 'none';
        }

        console.log('[ErrorLens] Recording stopped. Duration:', duration, 'ms');
        console.log('[ErrorLens] Events captured:', {
            consoleLogs: state.consoleLogs.length,
            jsExceptions: state.jsExceptions.length,
            networkErrors: state.networkErrors.length,
            recordedRequests: state.recordedRequests.length
        });

        // Capture screenshot before sending
        console.log('[ErrorLens] Capturing screenshot...');
        state.screenshot = await captureScreenshot();

        // Send to backend
        sendToBackend(duration);
    }

    // Send collected data to backend with retry
    async function sendToBackend(duration, retryCount = 0) {
        const MAX_RETRIES = 3;
        const RETRY_DELAY = 1000;

        const payload = {
            url: window.location.href,
            user_agent: navigator.userAgent,
            console_logs: state.consoleLogs,
            network_errors: state.networkErrors,
            js_exceptions: state.jsExceptions,
            screenshot: state.screenshot,
            recording_duration_ms: duration,
            // Story 7.1: Extended recording data
            recorded_requests: state.recordedRequests,
            record_mode: state.recordMode,
            // Smart API detection
            detected_api_base: state.detectedApiBase
        };

        console.log('[ErrorLens] Sending to backend:', payload);

        // Show loading state
        const retryText = retryCount > 0 ? ` (попытка ${retryCount + 1}/${MAX_RETRIES})` : '';
        showModal('Анализирую...' + retryText, 'Подождите, ErrorLens анализирует ваши ошибки.', true);

        try {
            // Choose API endpoint based on config
            const endpoint = CONFIG.USE_SESSIONS_API
                ? `${CONFIG.BACKEND_URL}/sessions`
                : `${CONFIG.BACKEND_URL}/analyze`;

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            const responseData = await response.json();
            console.log('[ErrorLens] Response:', responseData);

            // Handle different response formats
            let result;
            if (CONFIG.USE_SESSIONS_API) {
                // Sessions API returns {session_id, analysis}
                result = responseData.analysis || {
                    summary: 'Сессия сохранена',
                    probable_cause: 'Нет данных об ошибках для анализа',
                    suggested_fix: 'Попробуйте записать сессию с ошибками',
                    severity: 'low',
                    raw_events_count: 0
                };
                result.session_id = responseData.session_id;
            } else {
                result = responseData;
            }

            // Store results globally for re-launch handling
            state.lastResults = result;
            window.__errorLensResults = result;

            // Show result in modal and update bar
            if (CONFIG.WIDGET_STYLE === 'new') {
                updateBarToDone(result);
            }
            showResult(result);

        } catch (error) {
            console.error('[ErrorLens] Failed to send data:', error);

            // Retry logic
            if (retryCount < MAX_RETRIES - 1) {
                console.log(`[ErrorLens] Retrying in ${RETRY_DELAY}ms... (attempt ${retryCount + 2}/${MAX_RETRIES})`);
                showModal('Повторная попытка...', `Ошибка: ${error.message}. Повторяем запрос...`, true);
                await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
                return sendToBackend(duration, retryCount + 1);
            }

            // All retries failed - show error with retry button
            showErrorWithRetry(error.message, duration);
        } finally {
            // Reset classic widget UI (new bar is handled separately)
            if (CONFIG.WIDGET_STYLE === 'classic') {
                const widget = document.getElementById('errorlens-widget');
                if (widget) {
                    widget.style.background = '#ff4444';
                }
            }
            updateEventCounter();
        }
    }

    // Show error modal with retry button
    function showErrorWithRetry(errorMessage, duration) {
        const existingModal = document.getElementById('errorlens-modal');
        if (existingModal) existingModal.remove();

        const overlay = document.createElement('div');
        overlay.id = 'errorlens-modal';
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.7); display: flex; align-items: center;
            justify-content: center; z-index: 1000000; font-family: Arial, sans-serif;
        `;

        const modal = document.createElement('div');
        modal.style.cssText = `
            background: white; padding: 30px; border-radius: 10px;
            max-width: 500px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        `;

        modal.innerHTML = `
            <h2 style="margin-top: 0; color: #D32F2F;">Ошибка</h2>
            <p style="color: #666; line-height: 1.5;">Не удалось проанализировать после 3 попыток:<br><strong>${errorMessage}</strong></p>
        `;

        const btnContainer = document.createElement('div');
        btnContainer.style.cssText = 'display: flex; gap: 10px; margin-top: 20px;';

        const retryBtn = document.createElement('button');
        retryBtn.textContent = 'Попробовать снова';
        retryBtn.style.cssText = `
            background: #ff4444; color: white; border: none; padding: 10px 20px;
            border-radius: 5px; cursor: pointer; font-size: 14px;
        `;
        retryBtn.addEventListener('click', () => {
            overlay.remove();
            sendToBackend(duration, 0);
        });

        const closeBtn = document.createElement('button');
        closeBtn.textContent = 'Закрыть';
        closeBtn.style.cssText = `
            background: #999; color: white; border: none; padding: 10px 20px;
            border-radius: 5px; cursor: pointer; font-size: 14px;
        `;
        closeBtn.addEventListener('click', () => overlay.remove());

        btnContainer.appendChild(retryBtn);
        btnContainer.appendChild(closeBtn);
        modal.appendChild(btnContainer);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });
    }

    // Show modal with message - gradient style
    function showModal(title, message, isLoading) {
        // Remove existing modal if any
        const existingModal = document.getElementById('errorlens-modal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = 'errorlens-modal';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(4px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2147483647;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            animation: errorlens-fade-in 0.2s ease;
        `;

        // Create modal content
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 32px;
            border-radius: 20px;
            max-width: 400px;
            box-shadow: 0 20px 60px rgba(102, 126, 234, 0.4);
            text-align: center;
        `;

        // Icon
        const icon = document.createElement('div');
        icon.style.cssText = `
            width: 60px;
            height: 60px;
            background: rgba(255,255,255,0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 28px;
        `;
        icon.textContent = isLoading ? '⏳' : '✓';
        if (isLoading) icon.style.animation = 'errorlens-bounce 1s infinite';
        modal.appendChild(icon);

        const titleEl = document.createElement('h2');
        titleEl.textContent = title;
        titleEl.style.cssText = `
            margin: 0 0 12px 0;
            color: white;
            font-size: 20px;
            font-weight: 700;
        `;
        modal.appendChild(titleEl);

        const messageEl = document.createElement('div');
        messageEl.textContent = message;
        messageEl.style.cssText = `
            color: rgba(255,255,255,0.9);
            margin-bottom: 24px;
            line-height: 1.6;
            font-size: 14px;
        `;
        modal.appendChild(messageEl);

        if (!isLoading) {
            const closeBtn = document.createElement('button');
            closeBtn.textContent = 'Закрыть';
            closeBtn.style.cssText = `
                background: white;
                color: #667eea;
                border: none;
                padding: 12px 32px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                transition: all 0.2s ease;
            `;
            closeBtn.addEventListener('mouseenter', () => closeBtn.style.transform = 'scale(1.05)');
            closeBtn.addEventListener('mouseleave', () => closeBtn.style.transform = 'scale(1)');
            closeBtn.addEventListener('click', () => overlay.remove());
            modal.appendChild(closeBtn);
        }

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Close on overlay click (if not loading)
        if (!isLoading) {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    overlay.remove();
                }
            });
        }
    }

    // Show analysis result in modal
    function showResult(result) {
        // Remove existing modal if any
        const existingModal = document.getElementById('errorlens-modal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = 'errorlens-modal';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000000;
            font-family: Arial, sans-serif;
        `;

        // Create modal content with gradient style
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 20px;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.5);
            color: white;
        `;

        // Header with icon and title
        const header = document.createElement('div');
        header.style.cssText = 'display: flex; align-items: center; gap: 12px; margin-bottom: 20px;';

        const iconSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        iconSvg.setAttribute('viewBox', '0 0 24 24');
        iconSvg.setAttribute('width', '32');
        iconSvg.setAttribute('height', '32');
        iconSvg.innerHTML = '<path fill="white" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>';
        header.appendChild(iconSvg);

        const title = document.createElement('h2');
        title.textContent = 'Анализ ErrorLens';
        title.style.cssText = `
            margin: 0;
            color: white;
            font-size: 22px;
            font-weight: 600;
        `;
        header.appendChild(title);
        modal.appendChild(header);

        // Severity badge with Russian labels
        const severityColors = {
            low: 'rgba(76, 175, 80, 0.9)',
            medium: 'rgba(255, 152, 0, 0.9)',
            high: 'rgba(255, 87, 34, 0.9)',
            critical: 'rgba(211, 47, 47, 0.9)'
        };
        const severityLabels = {
            low: 'НИЗКИЙ',
            medium: 'СРЕДНИЙ',
            high: 'ВЫСОКИЙ',
            critical: 'КРИТИЧНЫЙ'
        };
        const severity = document.createElement('div');
        severity.textContent = severityLabels[result.severity] || result.severity.toUpperCase();
        severity.style.cssText = `
            display: inline-block;
            padding: 8px 18px;
            border-radius: 25px;
            background: ${severityColors[result.severity] || 'rgba(255,255,255,0.2)'};
            color: white;
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        `;
        modal.appendChild(severity);

        // Summary
        const summary = document.createElement('div');
        summary.innerHTML = `<strong>Итог:</strong><br>${result.summary}`;
        summary.style.cssText = `
            margin: 15px 0;
            padding: 15px;
            background: rgba(255,255,255,0.15);
            border-radius: 12px;
            color: white;
            line-height: 1.6;
        `;
        modal.appendChild(summary);

        // Probable cause
        const cause = document.createElement('div');
        cause.innerHTML = `<strong>Вероятная причина:</strong><br>${result.probable_cause}`;
        cause.style.cssText = `
            margin: 15px 0;
            padding: 15px;
            background: rgba(255,255,255,0.15);
            border-radius: 12px;
            color: white;
            line-height: 1.6;
        `;
        modal.appendChild(cause);

        // Suggested fix
        const fix = document.createElement('div');
        fix.innerHTML = `<strong>Рекомендация:</strong><br>${result.suggested_fix}`;
        fix.style.cssText = `
            margin: 15px 0;
            padding: 15px;
            background: rgba(255,255,255,0.15);
            border-radius: 12px;
            color: white;
            line-height: 1.6;
        `;
        modal.appendChild(fix);

        // Details (collapsible)
        if (result.details) {
            const detailsTitle = document.createElement('div');
            detailsTitle.textContent = '▶ Подробнее';
            detailsTitle.style.cssText = `
                margin: 20px 0 10px 0;
                color: rgba(255,255,255,0.9);
                cursor: pointer;
                font-weight: bold;
                padding: 10px 15px;
                background: rgba(255,255,255,0.1);
                border-radius: 8px;
                transition: background 0.2s;
            `;
            detailsTitle.addEventListener('mouseenter', () => detailsTitle.style.background = 'rgba(255,255,255,0.2)');
            detailsTitle.addEventListener('mouseleave', () => detailsTitle.style.background = 'rgba(255,255,255,0.1)');

            const detailsContent = document.createElement('div');
            detailsContent.textContent = result.details;
            detailsContent.style.cssText = `
                display: none;
                margin: 10px 0;
                padding: 15px;
                background: rgba(0,0,0,0.2);
                border-radius: 8px;
                color: rgba(255,255,255,0.9);
                line-height: 1.6;
                white-space: pre-wrap;
                font-size: 13px;
            `;

            detailsTitle.addEventListener('click', () => {
                if (detailsContent.style.display === 'none') {
                    detailsContent.style.display = 'block';
                    detailsTitle.textContent = '▼ Скрыть подробности';
                } else {
                    detailsContent.style.display = 'none';
                    detailsTitle.textContent = '▶ Подробнее';
                }
            });

            modal.appendChild(detailsTitle);
            modal.appendChild(detailsContent);
        }

        // Button container
        const btnContainer = document.createElement('div');
        btnContainer.style.cssText = 'display: flex; gap: 10px; margin-top: 25px; flex-wrap: wrap;';

        // Common button style helper
        const createStyledBtn = (text, bgColor) => {
            const btn = document.createElement('button');
            btn.textContent = text;
            btn.style.cssText = `
                background: ${bgColor}; color: white; border: none; padding: 12px 20px;
                border-radius: 25px; cursor: pointer; font-size: 14px; font-weight: 500;
                transition: all 0.2s; box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            `;
            btn.addEventListener('mouseenter', () => {
                btn.style.transform = 'translateY(-2px)';
                btn.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3)';
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.transform = 'translateY(0)';
                btn.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
            });
            return btn;
        };

        // Copy button
        const copyBtn = createStyledBtn('Скопировать', 'rgba(255,255,255,0.25)');
        copyBtn.addEventListener('click', () => {
            const text = `Итог: ${result.summary}\n\nВероятная причина: ${result.probable_cause}\n\nРекомендация: ${result.suggested_fix}\n\nКритичность: ${severityLabels[result.severity] || result.severity}`;
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.textContent = 'Скопировано!';
                copyBtn.style.background = 'rgba(76, 175, 80, 0.8)';
                setTimeout(() => {
                    copyBtn.textContent = 'Скопировать';
                    copyBtn.style.background = 'rgba(255,255,255,0.25)';
                }, 2000);
            }).catch(err => {
                console.error('[ErrorLens] Copy failed:', err);
                copyBtn.textContent = 'Ошибка';
                copyBtn.style.background = 'rgba(244, 67, 54, 0.8)';
            });
        });
        btnContainer.appendChild(copyBtn);

        // Export Postman button (only in 'all' mode with recorded requests)
        if (state.recordMode === 'all' && state.recordedRequests.length > 0) {
            const postmanBtn = createStyledBtn('Postman', 'rgba(255, 108, 55, 0.8)');
            postmanBtn.addEventListener('click', async () => {
                postmanBtn.textContent = 'Генерация...';
                postmanBtn.disabled = true;

                try {
                    const response = await fetch(`${CONFIG.BACKEND_URL}/export/postman`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            recorded_requests: state.recordedRequests,
                            collection_name: `ErrorLens - ${new URL(window.location.href).hostname}`,
                            base_url_variable: true,
                            generate_tests: true
                        })
                    });

                    if (!response.ok) throw new Error(`HTTP ${response.status}`);

                    const data = await response.json();
                    const blob = new Blob([JSON.stringify(data.collection, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `errorlens-collection-${new Date().toISOString().slice(0, 10)}.postman_collection.json`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);

                    postmanBtn.textContent = 'Скачано!';
                    postmanBtn.style.background = 'rgba(76, 175, 80, 0.8)';
                    setTimeout(() => {
                        postmanBtn.textContent = 'Postman';
                        postmanBtn.style.background = 'rgba(255, 108, 55, 0.8)';
                        postmanBtn.disabled = false;
                    }, 2000);
                } catch (error) {
                    console.error('[ErrorLens] Postman export failed:', error);
                    postmanBtn.textContent = 'Ошибка';
                    postmanBtn.style.background = 'rgba(244, 67, 54, 0.8)';
                    setTimeout(() => {
                        postmanBtn.textContent = 'Postman';
                        postmanBtn.style.background = 'rgba(255, 108, 55, 0.8)';
                        postmanBtn.disabled = false;
                    }, 2000);
                }
            });
            btnContainer.appendChild(postmanBtn);

            // Export pytest button
            const pytestBtn = createStyledBtn('pytest', 'rgba(0, 150, 136, 0.8)');
            pytestBtn.addEventListener('click', async () => {
                pytestBtn.textContent = 'Генерация...';
                pytestBtn.disabled = true;

                try {
                    const response = await fetch(`${CONFIG.BACKEND_URL}/export/pytest`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            recorded_requests: state.recordedRequests,
                            test_name: `test_${new URL(window.location.href).hostname.replace(/\./g, '_')}`,
                            base_url_variable: true
                        })
                    });

                    if (!response.ok) throw new Error(`HTTP ${response.status}`);

                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `test_session_${new Date().toISOString().slice(0, 10)}.py`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);

                    pytestBtn.textContent = 'Скачано!';
                    pytestBtn.style.background = 'rgba(76, 175, 80, 0.8)';
                    setTimeout(() => {
                        pytestBtn.textContent = 'pytest';
                        pytestBtn.style.background = 'rgba(0, 150, 136, 0.8)';
                        pytestBtn.disabled = false;
                    }, 2000);
                } catch (error) {
                    console.error('[ErrorLens] pytest export failed:', error);
                    pytestBtn.textContent = 'Ошибка';
                    pytestBtn.style.background = 'rgba(244, 67, 54, 0.8)';
                    setTimeout(() => {
                        pytestBtn.textContent = 'pytest';
                        pytestBtn.style.background = 'rgba(0, 150, 136, 0.8)';
                        pytestBtn.disabled = false;
                    }, 2000);
                }
            });
            btnContainer.appendChild(pytestBtn);
        }

        // Export Markdown button
        const exportBtn = createStyledBtn('Markdown', 'rgba(156, 39, 176, 0.8)');
        exportBtn.addEventListener('click', () => {
            const markdown = `## Анализ ошибки ErrorLens

**Критичность:** ${severityLabels[result.severity] || result.severity}

**Итог:** ${result.summary}

**Вероятная причина:** ${result.probable_cause}

**Рекомендация:** ${result.suggested_fix}

${result.details ? `### Подробности\n\`\`\`\n${result.details}\n\`\`\`` : ''}

---
*Сгенерировано ErrorLens*`;

            const blob = new Blob([markdown], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `errorlens-report-${new Date().toISOString().slice(0, 10)}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            exportBtn.textContent = 'Скачано!';
            exportBtn.style.background = 'rgba(76, 175, 80, 0.8)';
            setTimeout(() => {
                exportBtn.textContent = 'Markdown';
                exportBtn.style.background = 'rgba(156, 39, 176, 0.8)';
            }, 2000);
        });
        btnContainer.appendChild(exportBtn);

        // Dashboard link
        const dashboardBtn = createStyledBtn('Dashboard', 'rgba(79, 195, 247, 0.8)');
        dashboardBtn.addEventListener('click', () => {
            window.open(CONFIG.DASHBOARD_URL, '_blank');
        });
        btnContainer.appendChild(dashboardBtn);

        // Close button
        const closeBtn = createStyledBtn('Закрыть', 'rgba(255, 68, 68, 0.8)');
        closeBtn.addEventListener('click', () => overlay.remove());
        btnContainer.appendChild(closeBtn);

        modal.appendChild(btnContainer);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Close on overlay click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
            }
        });
    }

    // Initialize
    function init() {
        console.log('[ErrorLens] Initializing...');
        createWidget();
        console.log('[ErrorLens] Ready! Click the red button to start recording.');
    }

    // Global reset function for re-launch handling
    window.__errorLensReset = function() {
        // Stop recording if active
        if (state.isRecording) {
            state.isRecording = false;
            restoreConsole();
            restoreErrorHandler();
            restoreRejectionHandler();
            restoreFetch();
            restoreXHR();
        }

        // Clear captured data
        state.consoleLogs = [];
        state.networkErrors = [];
        state.jsExceptions = [];
        state.recordedRequests = [];
        state.requestIdCounter = 0;
        state.screenshot = null;
        state.lastResults = null;
        window.__errorLensResults = null;

        // Reset widget to idle state
        if (CONFIG.WIDGET_STYLE === 'new') {
            updateBarToIdle();
        } else {
            const widget = document.getElementById('errorlens-widget');
            if (widget) {
                widget.style.background = '#ff4444';
                widget.style.animation = 'none';
            }
        }

        // Update counter
        updateEventCounter();

        // Close any open modals
        const modal = document.getElementById('errorlens-modal');
        if (modal) modal.remove();

        console.log('[ErrorLens] Reset complete, ready for new recording');
    };

    // Global show results function for re-launch handling
    window.__errorLensShowResults = function() {
        if (window.__errorLensResults) {
            showResult(window.__errorLensResults);
        } else {
            console.log('[ErrorLens] No results to show');
        }
    };

    // Start the bookmarklet
    init();
})();
