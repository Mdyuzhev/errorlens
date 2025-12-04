/**
 * ErrorLens Widget Styles (CSS-in-JS)
 */
import { CONFIG } from '../core/config.js';

const STYLES_ID = 'errorlens-styles';

/**
 * Get all CSS styles for the widget
 */
function getStyles() {
  return `
    #errorlens-widget {
      position: fixed;
      top: 10px;
      right: 10px;
      z-index: 2147483647;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      user-select: none;
    }

    .el-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 16px;
      background: ${CONFIG.COLORS.GRADIENT};
      border-radius: 24px;
      color: white;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
      transition: background 0.3s ease, box-shadow 0.3s ease;
    }

    .el-pill:hover {
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
    }

    .el-pill.recording {
      background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
      box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
      animation: el-pulse 1.5s infinite;
    }

    .el-pill.done {
      background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
      box-shadow: 0 4px 15px rgba(34, 197, 94, 0.4);
    }

    .el-pill.sending {
      background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
      box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
    }

    @keyframes el-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.8; }
    }

    .el-logo {
      font-size: 16px;
    }

    .el-label {
      font-weight: 600;
      font-size: 13px;
    }

    .el-btn {
      background: rgba(255, 255, 255, 0.2);
      border: none;
      border-radius: 50%;
      width: 28px;
      height: 28px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 14px;
      transition: background 0.2s;
    }

    .el-btn:hover {
      background: rgba(255, 255, 255, 0.3);
    }

    .el-counter {
      background: rgba(255, 255, 255, 0.25);
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      min-width: 20px;
      text-align: center;
    }

    /* Modal */
    .el-modal {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2147483647;
      animation: el-fade-in 0.2s ease;
    }

    @keyframes el-fade-in {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .el-modal-content {
      background: linear-gradient(145deg, #1a1a2e 0%, #16213e 100%);
      border-radius: 16px;
      padding: 28px;
      max-width: 420px;
      width: 90%;
      color: white;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    }

    .el-modal h2 {
      margin: 0 0 16px;
      font-size: 20px;
      background: ${CONFIG.COLORS.GRADIENT};
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .el-modal p {
      margin: 8px 0;
      color: #a0a0b0;
      font-size: 14px;
    }

    .el-modal-actions {
      display: flex;
      gap: 10px;
      margin-top: 20px;
      flex-wrap: wrap;
    }

    .el-modal-btn {
      background: ${CONFIG.COLORS.GRADIENT};
      border: none;
      padding: 12px 20px;
      border-radius: 10px;
      color: white;
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      transition: transform 0.2s, opacity 0.2s;
    }

    .el-modal-btn:hover {
      transform: translateY(-1px);
      opacity: 0.95;
    }

    .el-modal-btn.secondary {
      background: rgba(255, 255, 255, 0.1);
    }

    /* Mode Menu */
    .el-mode-menu {
      position: fixed;
      top: 60px;
      right: 16px;
      background: ${CONFIG.COLORS.GRADIENT};
      border-radius: 16px;
      padding: 20px;
      box-shadow: 0 10px 40px rgba(102, 126, 234, 0.5);
      z-index: 2147483647;
      animation: el-slide-down 0.2s ease;
      min-width: 280px;
    }

    @keyframes el-slide-down {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .el-mode-menu h3 {
      color: white;
      margin: 0 0 16px;
      font-size: 16px;
      font-weight: 600;
    }

    .el-mode-option {
      background: rgba(255, 255, 255, 0.15);
      border: none;
      border-radius: 12px;
      padding: 14px 16px;
      margin-bottom: 10px;
      width: 100%;
      text-align: left;
      cursor: pointer;
      transition: background 0.2s;
      color: white;
    }

    .el-mode-option:hover {
      background: rgba(255, 255, 255, 0.25);
    }

    .el-mode-option:last-child {
      margin-bottom: 0;
    }

    .el-mode-option strong {
      display: block;
      font-size: 14px;
      margin-bottom: 4px;
    }

    .el-mode-option span {
      font-size: 12px;
      opacity: 0.8;
    }

    /* Spinner */
    .el-spinner {
      width: 20px;
      height: 20px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: el-spin 0.8s linear infinite;
    }

    @keyframes el-spin {
      to { transform: rotate(360deg); }
    }
  `;
}

/**
 * Inject styles into document
 */
export function injectStyles() {
  if (document.getElementById(STYLES_ID)) return;

  const style = document.createElement('style');
  style.id = STYLES_ID;
  style.textContent = getStyles();
  document.head.appendChild(style);
}

/**
 * Remove injected styles
 */
export function removeStyles() {
  const style = document.getElementById(STYLES_ID);
  if (style) style.remove();
}
