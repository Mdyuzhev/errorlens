/**
 * ErrorLens Utility Functions
 */

/**
 * Get ISO timestamp
 */
export function getTimestamp() {
  return new Date().toISOString();
}

/**
 * Check if HTTP status is an error
 */
export function isErrorStatus(status) {
  return status >= 400;
}

/**
 * Convert Headers object to plain object
 */
export function headersToObject(headers) {
  const obj = {};
  if (headers instanceof Headers) {
    headers.forEach((value, key) => {
      obj[key] = value;
    });
  } else if (headers && typeof headers === 'object') {
    Object.assign(obj, headers);
  }
  return obj;
}

/**
 * Truncate string to max length
 */
export function truncate(str, maxLength = 10000) {
  if (!str) return str;
  if (typeof str !== 'string') return str;
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength) + '... [truncated]';
}

/**
 * Safe JSON stringify with truncation
 */
export function safeStringify(obj, maxLength = 50000) {
  if (obj === undefined || obj === null) return null;
  try {
    const str = JSON.stringify(obj);
    return truncate(str, maxLength);
  } catch (e) {
    return '[Unable to stringify]';
  }
}

/**
 * Get stack trace from current location
 */
export function getStackTrace() {
  try {
    throw new Error();
  } catch (e) {
    return e.stack?.split('\n').slice(2).join('\n') || '';
  }
}

/**
 * Format duration in ms to human readable
 */
export function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}
