/**
 * Error Handlers (window.onerror, unhandledrejection)
 */
import { getState } from '../core/state.js';
import { getTimestamp } from '../utils/helpers.js';

let originalOnError = null;
let originalOnRejection = null;

/**
 * Setup window.onerror handler
 */
export function setupErrorHandler() {
  originalOnError = window.onerror;

  window.onerror = function(message, source, lineno, colno, error) {
    const state = getState();

    if (state.isRecording) {
      state.jsExceptions.push({
        type: 'error',
        message: String(message),
        source: source,
        lineno: lineno,
        colno: colno,
        stack: error?.stack || '',
        timestamp: getTimestamp()
      });
    }

    if (originalOnError) {
      return originalOnError.apply(this, arguments);
    }
    return false;
  };
}

/**
 * Restore original onerror handler
 */
export function restoreErrorHandler() {
  if (originalOnError !== null) {
    window.onerror = originalOnError;
    originalOnError = null;
  }
}

/**
 * Setup unhandledrejection handler
 */
export function setupRejectionHandler() {
  originalOnRejection = window.onunhandledrejection;

  window.onunhandledrejection = function(event) {
    const state = getState();

    if (state.isRecording) {
      const reason = event.reason;
      state.jsExceptions.push({
        type: 'unhandledrejection',
        message: 'Unhandled Promise Rejection: ' + (reason?.message || String(reason)),
        stack: reason?.stack || '',
        timestamp: getTimestamp()
      });
    }

    if (originalOnRejection) {
      return originalOnRejection.apply(this, arguments);
    }
  };
}

/**
 * Restore original rejection handler
 */
export function restoreRejectionHandler() {
  if (originalOnRejection !== null) {
    window.onunhandledrejection = originalOnRejection;
    originalOnRejection = null;
  }
}
