/**
 * ErrorLens Backend API
 */
import { detectApiBaseUrl } from './config.js';
import { getSessionData, getState } from './state.js';

/**
 * Send session data to backend
 */
export async function sendSession() {
  const apiUrl = detectApiBaseUrl();
  const sessionData = getSessionData();

  // Detailed logging for debugging
  console.log('[ErrorLens] ====== SEND SESSION START ======');
  console.log('[ErrorLens] API URL:', `${apiUrl}/sessions`);
  console.log('[ErrorLens] Event counts:', {
    console_logs: sessionData.console_logs?.length || 0,
    network_errors: sessionData.network_errors?.length || 0,
    js_exceptions: sessionData.js_exceptions?.length || 0,
    recorded_requests: sessionData.recorded_requests?.length || 0,
    has_screenshot: !!sessionData.screenshot
  });
  console.log('[ErrorLens] Full payload:', sessionData);

  const headers = {
    'Content-Type': 'application/json'
  };
  console.log('[ErrorLens] Request headers:', headers);

  try {
    const response = await fetch(`${apiUrl}/sessions`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(sessionData)
    });

    console.log('[ErrorLens] Response status:', response.status);
    console.log('[ErrorLens] Response headers:', Object.fromEntries(response.headers.entries()));

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[ErrorLens] API Error:', response.status, errorText);
      throw new Error(`API Error ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    console.log('[ErrorLens] Session created successfully:', result);
    console.log('[ErrorLens] ====== SEND SESSION END ======');
    // Normalize response - backend returns session_id, UI expects id
    if (result.session_id && !result.id) {
      result.id = result.session_id;
    }
    return result;
  } catch (error) {
    console.error('[ErrorLens] ====== SEND SESSION FAILED ======');
    console.error('[ErrorLens] Error type:', error.name);
    console.error('[ErrorLens] Error message:', error.message);
    console.error('[ErrorLens] Full error:', error);
    throw error;
  }
}

/**
 * Load html2canvas library dynamically
 */
export function loadHtml2Canvas() {
  return new Promise((resolve, reject) => {
    if (window.html2canvas) {
      resolve(window.html2canvas);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
    script.onload = () => resolve(window.html2canvas);
    script.onerror = () => reject(new Error('Failed to load html2canvas'));
    document.head.appendChild(script);
  });
}

/**
 * Capture screenshot of current page
 */
export async function captureScreenshot() {
  try {
    const html2canvas = await loadHtml2Canvas();
    const canvas = await html2canvas(document.body, {
      logging: false,
      useCORS: true,
      scale: 0.5,
      windowWidth: document.documentElement.scrollWidth,
      windowHeight: document.documentElement.scrollHeight
    });
    return canvas.toDataURL('image/jpeg', 0.5);
  } catch (e) {
    console.warn('[ErrorLens] Screenshot failed:', e);
    return null;
  }
}

/**
 * Get dashboard URL for redirect
 */
export function getDashboardUrl() {
  return detectApiBaseUrl();
}
