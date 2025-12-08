/**
 * ErrorLens Bookmarklet Configuration
 */
export const CONFIG = {
  VERSION: '2.0.0',
  API_TIMEOUT: 30000,
  MAX_LOGS: 1000,
  MAX_REQUESTS: 500,
  JUNK_URL_PATTERNS: [
    /google-analytics\.com/,
    /googletagmanager\.com/,
    /facebook\.com\/tr/,
    /doubleclick\.net/,
    /hotjar\.com/,
    /clarity\.ms/,
    /mc\.yandex\.ru/,
    /\.png(\?|$)/,
    /\.jpg(\?|$)/,
    /\.gif(\?|$)/,
    /\.svg(\?|$)/,
    /\.css(\?|$)/,
    /\.woff/,
    /favicon\.ico/
  ],
  COLORS: {
    IDLE: '#6366f1',
    RECORDING: '#ef4444',
    DONE: '#22c55e',
    GRADIENT: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  }
};

// URLs
export const PROD_URL = 'https://errorlens-production.up.railway.app';
export const LOCAL_URL = 'http://localhost:8000';
export const LOCAL_DASHBOARD_URL = 'http://localhost:3000';

/**
 * Detect API base URL based on environment
 */
export function detectApiBaseUrl() {
  // Check user config
  const userConfig = window.__ERRORLENS_CONFIG__ || {};
  if (userConfig.apiUrl) return userConfig.apiUrl;

  // Check localStorage
  const saved = localStorage.getItem('errorlens_api_url');
  if (saved) return saved;

  // Auto-detect based on script source or page location
  const currentScript = document.currentScript || document.querySelector('script[src*="recorder.js"]');
  const scriptSrc = currentScript ? currentScript.src : '';
  const isScriptFromLocalhost = scriptSrc.includes('localhost') || scriptSrc.includes('127.0.0.1');
  const isPageOnLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

  return (isScriptFromLocalhost || isPageOnLocalhost) ? LOCAL_URL : PROD_URL;
}

/**
 * Detect Dashboard URL based on environment
 */
export function detectDashboardUrl() {
  // Check user config
  const userConfig = window.__ERRORLENS_CONFIG__ || {};
  if (userConfig.dashboardUrl) return userConfig.dashboardUrl;

  // Check localStorage
  const saved = localStorage.getItem('errorlens_dashboard_url');
  if (saved) return saved;

  // Auto-detect based on script source or page location
  const currentScript = document.currentScript || document.querySelector('script[src*="recorder.js"]');
  const scriptSrc = currentScript ? currentScript.src : '';
  const isScriptFromLocalhost = scriptSrc.includes('localhost') || scriptSrc.includes('127.0.0.1');
  const isPageOnLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

  // In production, API and dashboard are same URL; in dev, dashboard is on port 3000
  return (isScriptFromLocalhost || isPageOnLocalhost) ? LOCAL_DASHBOARD_URL : PROD_URL;
}

/**
 * Check if URL is junk (analytics, tracking, static assets)
 */
export function isJunkUrl(url) {
  if (!url) return true;
  return CONFIG.JUNK_URL_PATTERNS.some(pattern => pattern.test(url));
}
