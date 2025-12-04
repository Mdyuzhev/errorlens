/**
 * ErrorLens Session State Management
 */

export const state = {
  isRecording: false,
  recordMode: 'errors', // 'errors' | 'all'
  startTime: null,
  consoleLogs: [],
  networkErrors: [],
  jsExceptions: [],
  recordedRequests: [],
  screenshot: null
};

// Store in window for persistence across script reloads
window.__errorLensState = window.__errorLensState || state;

/**
 * Get current state (from window if available)
 */
export function getState() {
  return window.__errorLensState || state;
}

/**
 * Reset state to initial values
 */
export function resetState() {
  const s = getState();
  s.isRecording = false;
  s.startTime = null;
  s.consoleLogs = [];
  s.networkErrors = [];
  s.jsExceptions = [];
  s.recordedRequests = [];
  s.screenshot = null;
}

/**
 * Get session data for API submission
 */
export function getSessionData() {
  const s = getState();
  return {
    console_logs: s.consoleLogs.slice(0, 1000),
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

/**
 * Get event counts for display
 */
export function getEventCounts() {
  const s = getState();
  return {
    logs: s.consoleLogs.length,
    errors: s.networkErrors.length + s.jsExceptions.length,
    requests: s.recordedRequests.length,
    total: s.consoleLogs.length + s.networkErrors.length + s.jsExceptions.length + s.recordedRequests.length
  };
}
