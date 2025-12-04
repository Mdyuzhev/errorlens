/**
 * Interceptors Index - Start/Stop all interceptors
 */
import { interceptConsole, restoreConsole } from './console.js';
import { setupErrorHandler, restoreErrorHandler, setupRejectionHandler, restoreRejectionHandler } from './errors.js';
import { interceptFetch, restoreFetch } from './fetch.js';
import { interceptXHR, restoreXHR } from './xhr.js';

/**
 * Start all interceptors
 */
export function startInterceptors() {
  interceptConsole();
  setupErrorHandler();
  setupRejectionHandler();
  interceptFetch();
  interceptXHR();
  console.log('[ErrorLens] Interceptors started');
}

/**
 * Stop all interceptors and restore originals
 */
export function stopInterceptors() {
  restoreConsole();
  restoreErrorHandler();
  restoreRejectionHandler();
  restoreFetch();
  restoreXHR();
  console.log('[ErrorLens] Interceptors stopped');
}

// Re-export individual functions for direct access if needed
export {
  interceptConsole,
  restoreConsole,
  setupErrorHandler,
  restoreErrorHandler,
  setupRejectionHandler,
  restoreRejectionHandler,
  interceptFetch,
  restoreFetch,
  interceptXHR,
  restoreXHR
};
