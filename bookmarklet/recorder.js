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

    // Configuration
    const BACKEND_URL = 'http://localhost:8000';
    const WIDGET_SIZE = 60;

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
        originalXHRSend: XMLHttpRequest.prototype.send
    };

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
            const url = typeof input === 'string' ? input : input.url;

            // Skip junk URLs in record-all mode
            if (state.recordMode === 'all' && isJunkUrl(url)) {
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
            this._errorlens = {
                method: method,
                url: url,
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

                // Skip junk URLs in record-all mode
                if (state.recordMode === 'all' && isJunkUrl(xhr._errorlens.url)) return;

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

    // UI Widget
    function createWidget() {
        // Check if widget already exists
        if (document.getElementById('errorlens-widget')) {
            console.log('[ErrorLens] Widget already exists');
            return;
        }

        // Create widget container
        const widget = document.createElement('div');
        widget.id = 'errorlens-widget';
        widget.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: ${WIDGET_SIZE}px;
            height: ${WIDGET_SIZE}px;
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

        // Add to page
        document.body.appendChild(widget);

        console.log('[ErrorLens] Widget created');
    }

    // Update event counter in widget
    function updateEventCounter() {
        const counter = document.getElementById('errorlens-counter');
        if (counter) {
            const total = state.consoleLogs.length + state.jsExceptions.length + state.networkErrors.length;
            counter.textContent = total.toString();
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
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            z-index: 1000000;
            font-family: Arial, sans-serif;
            overflow: hidden;
        `;

        // Option 1: Record errors only
        const errorsOption = document.createElement('div');
        errorsOption.style.cssText = `
            padding: 12px 20px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
            transition: background 0.2s;
        `;
        errorsOption.innerHTML = `
            <div style="font-weight: bold; color: #ff4444;">Только ошибки</div>
            <div style="font-size: 12px; color: #666;">Записывать 4xx/5xx ошибки</div>
        `;
        errorsOption.addEventListener('mouseenter', () => errorsOption.style.background = '#f5f5f5');
        errorsOption.addEventListener('mouseleave', () => errorsOption.style.background = 'white');
        errorsOption.addEventListener('click', () => {
            menu.remove();
            startRecording('errors');
        });

        // Option 2: Record all requests
        const allOption = document.createElement('div');
        allOption.style.cssText = `
            padding: 12px 20px;
            cursor: pointer;
            transition: background 0.2s;
        `;
        allOption.innerHTML = `
            <div style="font-weight: bold; color: #2196F3;">Все запросы</div>
            <div style="font-size: 12px; color: #666;">Для генерации тестов</div>
        `;
        allOption.addEventListener('mouseenter', () => allOption.style.background = '#f5f5f5');
        allOption.addEventListener('mouseleave', () => allOption.style.background = 'white');
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

        // Update widget UI - red for errors, blue for all
        const widget = document.getElementById('errorlens-widget');
        if (widget) {
            widget.style.background = mode === 'all' ? '#2196F3' : '#ff0000';
            widget.style.animation = 'pulse 1.5s infinite';
        }

        // Add pulse animation
        if (!document.getElementById('errorlens-style')) {
            const style = document.createElement('style');
            style.id = 'errorlens-style';
            style.textContent = `
                @keyframes pulse {
                    0%, 100% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.1); opacity: 0.8; }
                }
            `;
            document.head.appendChild(style);
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
            record_mode: state.recordMode
        };

        console.log('[ErrorLens] Sending to backend:', payload);

        // Show loading state
        const retryText = retryCount > 0 ? ` (попытка ${retryCount + 1}/${MAX_RETRIES})` : '';
        showModal('Анализирую...' + retryText, 'Подождите, ErrorLens анализирует ваши ошибки.', true);

        try {
            const response = await fetch(`${BACKEND_URL}/analyze`, {
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

            const result = await response.json();
            console.log('[ErrorLens] Analysis result:', result);

            // Show result in modal
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
            // Reset widget UI
            const widget = document.getElementById('errorlens-widget');
            if (widget) {
                widget.style.background = '#ff4444';
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

    // Show modal with message
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
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000000;
            font-family: Arial, sans-serif;
        `;

        // Create modal content
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 10px;
            max-width: 500px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        `;

        const titleEl = document.createElement('h2');
        titleEl.textContent = title;
        titleEl.style.cssText = `
            margin-top: 0;
            color: #333;
        `;
        modal.appendChild(titleEl);

        const messageEl = document.createElement('div');
        messageEl.textContent = message;
        messageEl.style.cssText = `
            color: #666;
            margin: 20px 0;
            line-height: 1.5;
        `;
        modal.appendChild(messageEl);

        if (!isLoading) {
            const closeBtn = document.createElement('button');
            closeBtn.textContent = 'Закрыть';
            closeBtn.style.cssText = `
                background: #ff4444;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
            `;
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

        // Create modal content
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 10px;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        `;

        // Title
        const title = document.createElement('h2');
        title.textContent = 'Анализ ErrorLens';
        title.style.cssText = `
            margin-top: 0;
            color: #333;
        `;
        modal.appendChild(title);

        // Severity badge with Russian labels
        const severityColors = {
            low: '#4CAF50',
            medium: '#FF9800',
            high: '#FF5722',
            critical: '#D32F2F'
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
            padding: 5px 15px;
            border-radius: 20px;
            background: ${severityColors[result.severity] || '#999'};
            color: white;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 20px;
        `;
        modal.appendChild(severity);

        // Summary
        const summary = document.createElement('div');
        summary.innerHTML = `<strong>Итог:</strong><br>${result.summary}`;
        summary.style.cssText = `
            margin: 15px 0;
            color: #333;
            line-height: 1.6;
        `;
        modal.appendChild(summary);

        // Probable cause
        const cause = document.createElement('div');
        cause.innerHTML = `<strong>Вероятная причина:</strong><br>${result.probable_cause}`;
        cause.style.cssText = `
            margin: 15px 0;
            color: #333;
            line-height: 1.6;
        `;
        modal.appendChild(cause);

        // Suggested fix
        const fix = document.createElement('div');
        fix.innerHTML = `<strong>Рекомендация:</strong><br>${result.suggested_fix}`;
        fix.style.cssText = `
            margin: 15px 0;
            color: #333;
            line-height: 1.6;
        `;
        modal.appendChild(fix);

        // Details (collapsible)
        if (result.details) {
            const detailsTitle = document.createElement('div');
            detailsTitle.textContent = 'Подробнее';
            detailsTitle.style.cssText = `
                margin: 20px 0 10px 0;
                color: #ff4444;
                cursor: pointer;
                font-weight: bold;
            `;

            const detailsContent = document.createElement('div');
            detailsContent.textContent = result.details;
            detailsContent.style.cssText = `
                display: none;
                margin: 10px 0;
                padding: 15px;
                background: #f5f5f5;
                border-radius: 5px;
                color: #666;
                line-height: 1.6;
                white-space: pre-wrap;
            `;

            detailsTitle.addEventListener('click', () => {
                if (detailsContent.style.display === 'none') {
                    detailsContent.style.display = 'block';
                    detailsTitle.textContent = 'Скрыть подробности';
                } else {
                    detailsContent.style.display = 'none';
                    detailsTitle.textContent = 'Подробнее';
                }
            });

            modal.appendChild(detailsTitle);
            modal.appendChild(detailsContent);
        }

        // Button container
        const btnContainer = document.createElement('div');
        btnContainer.style.cssText = 'display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap;';

        // Copy button
        const copyBtn = document.createElement('button');
        copyBtn.textContent = 'Скопировать';
        copyBtn.style.cssText = `
            background: #2196F3; color: white; border: none; padding: 10px 20px;
            border-radius: 5px; cursor: pointer; font-size: 14px;
        `;
        copyBtn.addEventListener('click', () => {
            const text = `Итог: ${result.summary}\n\nВероятная причина: ${result.probable_cause}\n\nРекомендация: ${result.suggested_fix}\n\nКритичность: ${severityLabels[result.severity] || result.severity}`;
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.textContent = 'Скопировано!';
                copyBtn.style.background = '#4CAF50';
                setTimeout(() => {
                    copyBtn.textContent = 'Скопировать';
                    copyBtn.style.background = '#2196F3';
                }, 2000);
            }).catch(err => {
                console.error('[ErrorLens] Copy failed:', err);
                copyBtn.textContent = 'Ошибка';
                copyBtn.style.background = '#f44336';
            });
        });
        btnContainer.appendChild(copyBtn);

        // Export Postman button (only in 'all' mode with recorded requests)
        if (state.recordMode === 'all' && state.recordedRequests.length > 0) {
            const postmanBtn = document.createElement('button');
            postmanBtn.textContent = 'Экспорт в Postman';
            postmanBtn.style.cssText = `
                background: #FF6C37; color: white; border: none; padding: 10px 20px;
                border-radius: 5px; cursor: pointer; font-size: 14px;
            `;
            postmanBtn.addEventListener('click', async () => {
                postmanBtn.textContent = 'Генерация...';
                postmanBtn.disabled = true;

                try {
                    const response = await fetch(`${BACKEND_URL}/export/postman`, {
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
                    postmanBtn.style.background = '#4CAF50';
                    setTimeout(() => {
                        postmanBtn.textContent = 'Экспорт в Postman';
                        postmanBtn.style.background = '#FF6C37';
                        postmanBtn.disabled = false;
                    }, 2000);
                } catch (error) {
                    console.error('[ErrorLens] Postman export failed:', error);
                    postmanBtn.textContent = 'Ошибка';
                    postmanBtn.style.background = '#f44336';
                    setTimeout(() => {
                        postmanBtn.textContent = 'Экспорт в Postman';
                        postmanBtn.style.background = '#FF6C37';
                        postmanBtn.disabled = false;
                    }, 2000);
                }
            });
            btnContainer.appendChild(postmanBtn);
        }

        // Export Markdown button
        const exportBtn = document.createElement('button');
        exportBtn.textContent = 'Экспорт в Markdown';
        exportBtn.style.cssText = `
            background: #9C27B0; color: white; border: none; padding: 10px 20px;
            border-radius: 5px; cursor: pointer; font-size: 14px;
        `;
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
            exportBtn.style.background = '#4CAF50';
            setTimeout(() => {
                exportBtn.textContent = 'Экспорт в Markdown';
                exportBtn.style.background = '#9C27B0';
            }, 2000);
        });
        btnContainer.appendChild(exportBtn);

        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.textContent = 'Закрыть';
        closeBtn.style.cssText = `
            background: #ff4444; color: white; border: none; padding: 10px 20px;
            border-radius: 5px; cursor: pointer; font-size: 14px;
        `;
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

    // Start the bookmarklet
    init();
})();
