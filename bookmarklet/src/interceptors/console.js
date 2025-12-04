/**
 * Console Interception
 */
import { getState } from '../core/state.js';
import { getTimestamp, getStackTrace } from '../utils/helpers.js';

// Store original console methods
const originalConsole = {
  log: console.log,
  warn: console.warn,
  error: console.error,
  info: console.info,
  debug: console.debug
};

/**
 * Intercept console methods to capture logs
 */
export function interceptConsole() {
  ['log', 'warn', 'error', 'info', 'debug'].forEach(method => {
    console[method] = function(...args) {
      const state = getState();

      if (state.isRecording) {
        try {
          const message = args.map(arg => {
            try {
              if (arg instanceof Error) {
                return `${arg.name}: ${arg.message}`;
              }
              return typeof arg === 'object' ? JSON.stringify(arg) : String(arg);
            } catch {
              return String(arg);
            }
          }).join(' ');

          state.consoleLogs.push({
            type: method,
            message: message.substring(0, 5000), // Limit message size
            timestamp: getTimestamp(),
            stack: method === 'error' ? getStackTrace() : undefined
          });
        } catch (e) {
          // Silently ignore logging errors
        }
      }

      // Call original method
      originalConsole[method].apply(console, args);
    };
  });
}

/**
 * Restore original console methods
 */
export function restoreConsole() {
  Object.keys(originalConsole).forEach(method => {
    console[method] = originalConsole[method];
  });
}
