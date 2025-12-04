/**
 * Fetch API Interception
 */
import { getState } from '../core/state.js';
import { isJunkUrl } from '../core/config.js';
import { getTimestamp, isErrorStatus, headersToObject, safeStringify } from '../utils/helpers.js';

const originalFetch = window.fetch;

/**
 * Intercept fetch requests
 */
export function interceptFetch() {
  window.fetch = async function(input, init = {}) {
    const url = typeof input === 'string' ? input : (input.url || String(input));
    const method = (init.method || 'GET').toUpperCase();
    const startTime = Date.now();

    // Skip junk URLs
    if (isJunkUrl(url)) {
      return originalFetch.apply(this, arguments);
    }

    const state = getState();

    try {
      const response = await originalFetch.apply(this, arguments);
      const duration = Date.now() - startTime;

      if (state.isRecording) {
        const shouldRecord = state.recordMode === 'all' || isErrorStatus(response.status);

        if (shouldRecord) {
          // Clone response to read body without consuming it
          const clone = response.clone();
          let responseBody = null;

          try {
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
              responseBody = await clone.json();
            } else if (contentType.includes('text/')) {
              responseBody = await clone.text();
            }
          } catch (e) {
            responseBody = '[Unable to parse body]';
          }

          const record = {
            type: 'fetch',
            method: method,
            url: url,
            status: response.status,
            statusText: response.statusText,
            requestHeaders: headersToObject(init.headers),
            requestBody: safeStringify(init.body),
            responseHeaders: headersToObject(response.headers),
            responseBody: safeStringify(responseBody, 20000),
            duration: duration,
            timestamp: getTimestamp()
          };

          if (isErrorStatus(response.status)) {
            state.networkErrors.push(record);
          }
          state.recordedRequests.push(record);
        }
      }

      return response;
    } catch (error) {
      // Network error (no response)
      if (state.isRecording) {
        state.networkErrors.push({
          type: 'fetch',
          method: method,
          url: url,
          error: error.message || 'Network Error',
          duration: Date.now() - startTime,
          timestamp: getTimestamp()
        });
      }
      throw error;
    }
  };
}

/**
 * Restore original fetch
 */
export function restoreFetch() {
  window.fetch = originalFetch;
}
