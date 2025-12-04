/**
 * XMLHttpRequest Interception
 */
import { getState } from '../core/state.js';
import { isJunkUrl } from '../core/config.js';
import { getTimestamp, isErrorStatus, safeStringify } from '../utils/helpers.js';

const XHRProto = XMLHttpRequest.prototype;
const originalOpen = XHRProto.open;
const originalSend = XHRProto.send;
const originalSetHeader = XHRProto.setRequestHeader;

/**
 * Intercept XMLHttpRequest
 */
export function interceptXHR() {
  XHRProto.open = function(method, url) {
    this._errorlens = {
      method: method,
      url: url,
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
    const state = getState();

    if (this._errorlens && !isJunkUrl(this._errorlens.url)) {
      this._errorlens.requestBody = body;
      this._errorlens.startTime = Date.now();

      const xhr = this;

      this.addEventListener('load', function() {
        if (state.isRecording) {
          const duration = Date.now() - xhr._errorlens.startTime;
          const shouldRecord = state.recordMode === 'all' || isErrorStatus(xhr.status);

          if (shouldRecord) {
            const record = {
              type: 'xhr',
              method: xhr._errorlens.method.toUpperCase(),
              url: xhr._errorlens.url,
              status: xhr.status,
              statusText: xhr.statusText,
              requestHeaders: xhr._errorlens.requestHeaders,
              requestBody: safeStringify(xhr._errorlens.requestBody),
              responseBody: safeStringify(xhr.responseText, 20000),
              duration: duration,
              timestamp: getTimestamp()
            };

            if (isErrorStatus(xhr.status)) {
              state.networkErrors.push(record);
            }
            state.recordedRequests.push(record);
          }
        }
      });

      this.addEventListener('error', function() {
        if (state.isRecording) {
          state.networkErrors.push({
            type: 'xhr',
            method: xhr._errorlens.method.toUpperCase(),
            url: xhr._errorlens.url,
            error: 'Network Error',
            duration: Date.now() - xhr._errorlens.startTime,
            timestamp: getTimestamp()
          });
        }
      });

      this.addEventListener('timeout', function() {
        if (state.isRecording) {
          state.networkErrors.push({
            type: 'xhr',
            method: xhr._errorlens.method.toUpperCase(),
            url: xhr._errorlens.url,
            error: 'Request Timeout',
            duration: Date.now() - xhr._errorlens.startTime,
            timestamp: getTimestamp()
          });
        }
      });
    }

    return originalSend.apply(this, arguments);
  };
}

/**
 * Restore original XHR methods
 */
export function restoreXHR() {
  XHRProto.open = originalOpen;
  XHRProto.send = originalSend;
  XHRProto.setRequestHeader = originalSetHeader;
}
