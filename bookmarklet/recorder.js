/**
 * ErrorLens Bookmarklet Recorder
 *
 * Stories 2.1 + 2.4:
 * - Intercepts console.log/warn/error
 * - Captures window.onerror and unhandledrejection
 * - Records timestamps for each event
 * - Floating UI widget (red dot = recording)
 * - Click to start/stop and send to backend
 * - Shows result in modal
 */
(function() {
    'use strict';

    // Configuration
    const BACKEND_URL = 'http://localhost:8000';
    const WIDGET_SIZE = 60;

    // State
    const state = {
        isRecording: false,
        startTime: null,
        consoleLogs: [],
        jsExceptions: [],
        networkErrors: [],
        originalConsole: {
            log: console.log,
            warn: console.warn,
            error: console.error,
            info: console.info,
            debug: console.debug
        },
        originalOnError: window.onerror,
        originalOnUnhandledRejection: window.onunhandledrejection
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
    function handleWidgetClick() {
        if (!state.isRecording) {
            startRecording();
        } else {
            stopRecordingAndSend();
        }
    }

    // Start recording
    function startRecording() {
        state.isRecording = true;
        state.startTime = Date.now();
        state.consoleLogs = [];
        state.jsExceptions = [];
        state.networkErrors = [];

        // Setup interceptors
        interceptConsole();
        setupErrorHandler();
        setupRejectionHandler();

        // Update widget UI
        const widget = document.getElementById('errorlens-widget');
        if (widget) {
            widget.style.background = '#ff0000';
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
    function stopRecordingAndSend() {
        state.isRecording = false;
        const duration = Date.now() - state.startTime;

        // Restore original handlers
        restoreConsole();
        restoreErrorHandler();
        restoreRejectionHandler();

        // Update widget UI
        const widget = document.getElementById('errorlens-widget');
        if (widget) {
            widget.style.background = '#ffaa00';
            widget.style.animation = 'none';
        }

        console.log('[ErrorLens] Recording stopped. Duration:', duration, 'ms');
        console.log('[ErrorLens] Events captured:', {
            consoleLogs: state.consoleLogs.length,
            jsExceptions: state.jsExceptions.length,
            networkErrors: state.networkErrors.length
        });

        // Send to backend
        sendToBackend(duration);
    }

    // Send collected data to backend
    async function sendToBackend(duration) {
        const payload = {
            url: window.location.href,
            user_agent: navigator.userAgent,
            console_logs: state.consoleLogs,
            network_errors: state.networkErrors,
            js_exceptions: state.jsExceptions,
            screenshot: null, // TODO: Story 2.4.1 - Add html2canvas integration
            recording_duration_ms: duration
        };

        console.log('[ErrorLens] Sending to backend:', payload);

        // Show loading state
        showModal('Analyzing...', 'Please wait while ErrorLens analyzes your errors.', true);

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
            showModal('Error', `Failed to analyze errors: ${error.message}`, false);
        } finally {
            // Reset widget UI
            const widget = document.getElementById('errorlens-widget');
            if (widget) {
                widget.style.background = '#ff4444';
            }
            updateEventCounter();
        }
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
            closeBtn.textContent = 'Close';
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
        title.textContent = 'ErrorLens Analysis';
        title.style.cssText = `
            margin-top: 0;
            color: #333;
        `;
        modal.appendChild(title);

        // Severity badge
        const severityColors = {
            low: '#4CAF50',
            medium: '#FF9800',
            high: '#FF5722',
            critical: '#D32F2F'
        };
        const severity = document.createElement('div');
        severity.textContent = result.severity.toUpperCase();
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
        summary.innerHTML = `<strong>Summary:</strong><br>${result.summary}`;
        summary.style.cssText = `
            margin: 15px 0;
            color: #333;
            line-height: 1.6;
        `;
        modal.appendChild(summary);

        // Probable cause
        const cause = document.createElement('div');
        cause.innerHTML = `<strong>Probable Cause:</strong><br>${result.probable_cause}`;
        cause.style.cssText = `
            margin: 15px 0;
            color: #333;
            line-height: 1.6;
        `;
        modal.appendChild(cause);

        // Suggested fix
        const fix = document.createElement('div');
        fix.innerHTML = `<strong>Suggested Fix:</strong><br>${result.suggested_fix}`;
        fix.style.cssText = `
            margin: 15px 0;
            color: #333;
            line-height: 1.6;
        `;
        modal.appendChild(fix);

        // Details (collapsible)
        if (result.details) {
            const detailsTitle = document.createElement('div');
            detailsTitle.textContent = 'Show Details';
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
                    detailsTitle.textContent = 'Hide Details';
                } else {
                    detailsContent.style.display = 'none';
                    detailsTitle.textContent = 'Show Details';
                }
            });

            modal.appendChild(detailsTitle);
            modal.appendChild(detailsContent);
        }

        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.textContent = 'Close';
        closeBtn.style.cssText = `
            background: #ff4444;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 20px;
        `;
        closeBtn.addEventListener('click', () => overlay.remove());
        modal.appendChild(closeBtn);

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
