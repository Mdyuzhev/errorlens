/**
 * ErrorLens Widget UI
 */
import { getState, resetState, getEventCounts } from '../core/state.js';
import { sendSession, captureScreenshot, getDashboardUrl } from '../core/api.js';
import { injectStyles, removeStyles } from './styles.js';
import { startInterceptors, stopInterceptors } from '../interceptors/index.js';

let widgetElement = null;
let counterInterval = null;
let currentModeMenu = null;

/**
 * Create and show the widget
 */
export function createWidget() {
  injectStyles();

  // Remove existing widget if any
  if (widgetElement) {
    widgetElement.remove();
  }

  widgetElement = document.createElement('div');
  widgetElement.id = 'errorlens-widget';
  widgetElement.innerHTML = `
    <div class="el-pill" id="el-pill">
      <span class="el-logo">🔍</span>
      <span class="el-label">ErrorLens</span>
      <button class="el-btn" id="el-record-btn" title="Start Recording">⚫</button>
      <span class="el-counter" id="el-counter" style="display:none">0</span>
      <button class="el-btn" id="el-dashboard-btn" title="Open Dashboard">📊</button>
      <button class="el-btn" id="el-close-btn" title="Close">✕</button>
    </div>
  `;

  document.body.appendChild(widgetElement);

  // Make widget draggable
  makeWidgetDraggable(widgetElement);

  // Restore position from localStorage
  restoreWidgetPosition();

  // Event listeners
  document.getElementById('el-record-btn').addEventListener('click', handleRecordClick);
  document.getElementById('el-dashboard-btn').addEventListener('click', () => window.open(getDashboardUrl(), '_blank'));
  document.getElementById('el-close-btn').addEventListener('click', removeWidget);

  return widgetElement;
}

/**
 * Make widget draggable
 */
function makeWidgetDraggable(widget) {
  let isDragging = false;
  let hasMoved = false;
  let startX, startY, startLeft, startTop;

  function startDrag(e) {
    if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;

    isDragging = true;
    hasMoved = false;

    const touch = e.touches ? e.touches[0] : e;
    startX = touch.clientX;
    startY = touch.clientY;

    const rect = widget.getBoundingClientRect();
    startLeft = rect.left;
    startTop = rect.top;

    e.preventDefault();
  }

  function drag(e) {
    if (!isDragging) return;

    const touch = e.touches ? e.touches[0] : e;
    const dx = touch.clientX - startX;
    const dy = touch.clientY - startY;

    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
      hasMoved = true;
    }

    widget.style.left = (startLeft + dx) + 'px';
    widget.style.top = (startTop + dy) + 'px';
    widget.style.right = 'auto';
  }

  function stopDrag() {
    if (isDragging && hasMoved) {
      // Save position
      localStorage.setItem('errorlens_widget_pos', JSON.stringify({
        left: widget.style.left,
        top: widget.style.top
      }));
    }
    isDragging = false;
  }

  widget.addEventListener('mousedown', startDrag);
  widget.addEventListener('touchstart', startDrag, { passive: false });
  document.addEventListener('mousemove', drag);
  document.addEventListener('touchmove', drag, { passive: false });
  document.addEventListener('mouseup', stopDrag);
  document.addEventListener('touchend', stopDrag);
}

/**
 * Restore widget position from localStorage
 */
function restoreWidgetPosition() {
  const saved = localStorage.getItem('errorlens_widget_pos');
  if (saved && widgetElement) {
    try {
      const pos = JSON.parse(saved);
      widgetElement.style.left = pos.left;
      widgetElement.style.top = pos.top;
      widgetElement.style.right = 'auto';
    } catch (e) {
      // Ignore parse errors
    }
  }
}

/**
 * Handle record button click
 */
async function handleRecordClick(event) {
  event.stopPropagation();
  const state = getState();

  if (!state.isRecording) {
    // Show mode selection menu
    showModeMenu();
  } else {
    // Stop recording
    await stopRecording();
  }
}

/**
 * Show mode selection menu
 */
function showModeMenu() {
  // Remove existing menu
  if (currentModeMenu) {
    currentModeMenu.remove();
    currentModeMenu = null;
    return;
  }

  const menu = document.createElement('div');
  menu.className = 'el-mode-menu';
  menu.innerHTML = `
    <h3>🎯 Выберите режим записи</h3>
    <button class="el-mode-option" data-mode="errors">
      <strong>🐛 Только ошибки</strong>
      <span>Console.error, сетевые ошибки (4xx/5xx), JS exceptions</span>
    </button>
    <button class="el-mode-option" data-mode="all">
      <strong>📡 Все запросы</strong>
      <span>Все HTTP запросы + все console логи + ошибки</span>
    </button>
  `;

  document.body.appendChild(menu);
  currentModeMenu = menu;

  // Handle mode selection
  menu.querySelectorAll('.el-mode-option').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const mode = e.currentTarget.dataset.mode;
      startRecording(mode);
      menu.remove();
      currentModeMenu = null;
    });
  });

  // Close on outside click
  setTimeout(() => {
    document.addEventListener('click', function closeMenu(e) {
      if (!menu.contains(e.target) && !e.target.closest('#el-record-btn')) {
        menu.remove();
        currentModeMenu = null;
        document.removeEventListener('click', closeMenu);
      }
    });
  }, 100);
}

/**
 * Start recording
 */
function startRecording(mode) {
  const state = getState();
  state.isRecording = true;
  state.recordMode = mode;
  state.startTime = Date.now();

  startInterceptors();
  updateWidgetState('recording');
  startCounterUpdate();

  console.log(`[ErrorLens] Recording started (mode: ${mode})`);
}

/**
 * Stop recording and send data
 */
async function stopRecording() {
  const state = getState();
  state.isRecording = false;
  stopInterceptors();
  stopCounterUpdate();

  updateWidgetState('sending');

  // Capture screenshot
  try {
    state.screenshot = await captureScreenshot();
  } catch (e) {
    console.warn('[ErrorLens] Screenshot failed:', e);
  }

  // Send to API
  try {
    const result = await sendSession();
    updateWidgetState('done');
    showResultModal(result);
    console.log('[ErrorLens] Session saved:', result.id);
  } catch (error) {
    updateWidgetState('idle');
    showErrorModal(error);
    console.error('[ErrorLens] Failed to save session:', error);
  }
}

/**
 * Update widget visual state
 */
function updateWidgetState(newState) {
  const pill = document.getElementById('el-pill');
  const btn = document.getElementById('el-record-btn');
  const counter = document.getElementById('el-counter');
  const label = widgetElement.querySelector('.el-label');

  if (!pill) return;

  pill.classList.remove('recording', 'done', 'sending');

  switch (newState) {
    case 'recording':
      pill.classList.add('recording');
      btn.textContent = '⏹';
      btn.title = 'Stop Recording';
      counter.style.display = 'inline';
      label.textContent = 'Recording...';
      break;
    case 'sending':
      pill.classList.add('sending');
      label.textContent = 'Sending...';
      btn.innerHTML = '<span class="el-spinner"></span>';
      break;
    case 'done':
      pill.classList.add('done');
      btn.textContent = '✓';
      label.textContent = 'Done!';
      counter.style.display = 'none';
      break;
    default: // idle
      btn.textContent = '⚫';
      btn.title = 'Start Recording';
      label.textContent = 'ErrorLens';
      counter.style.display = 'none';
  }
}

/**
 * Start counter update interval
 */
function startCounterUpdate() {
  stopCounterUpdate();

  counterInterval = setInterval(() => {
    const counter = document.getElementById('el-counter');
    const state = getState();

    if (counter && state.isRecording) {
      const counts = getEventCounts();
      counter.textContent = counts.total;
    }
  }, 500);
}

/**
 * Stop counter update interval
 */
function stopCounterUpdate() {
  if (counterInterval) {
    clearInterval(counterInterval);
    counterInterval = null;
  }
}

/**
 * Show success result modal
 */
function showResultModal(result) {
  const counts = getEventCounts();
  const dashboardUrl = getDashboardUrl();
  const sessionUrl = result.id ? `${dashboardUrl}/#/sessions/${result.id}` : dashboardUrl;

  const modal = document.createElement('div');
  modal.className = 'el-modal';
  modal.innerHTML = `
    <div class="el-modal-content">
      <h2>✅ Сессия записана!</h2>
      <p><strong>ID:</strong> ${result.id?.substring(0, 8) || 'N/A'}...</p>
      <p><strong>События:</strong> ${counts.total} (ошибок: ${counts.errors}, запросов: ${counts.requests})</p>
      <div class="el-modal-actions">
        <button class="el-modal-btn" onclick="window.open('${sessionUrl}', '_blank'); this.closest('.el-modal').remove();">
          📊 Открыть сессию
        </button>
        <button class="el-modal-btn secondary" onclick="this.closest('.el-modal').remove();">
          Закрыть
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Click outside to close
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });

  resetState();
}

/**
 * Show error modal
 */
function showErrorModal(error) {
  const modal = document.createElement('div');
  modal.className = 'el-modal';
  modal.innerHTML = `
    <div class="el-modal-content">
      <h2>❌ Ошибка</h2>
      <p>${error.message || 'Не удалось сохранить сессию'}</p>
      <div class="el-modal-actions">
        <button class="el-modal-btn" onclick="this.closest('.el-modal').remove();">
          Закрыть
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);
}

/**
 * Remove widget and cleanup
 */
export function removeWidget() {
  stopCounterUpdate();
  stopInterceptors();

  if (currentModeMenu) {
    currentModeMenu.remove();
    currentModeMenu = null;
  }

  if (widgetElement) {
    widgetElement.remove();
    widgetElement = null;
  }

  removeStyles();
  resetState();

  window.__ERRORLENS_LOADED__ = false;
  console.log('[ErrorLens] Widget removed');
}

/**
 * Check if widget exists
 */
export function isWidgetVisible() {
  return !!widgetElement;
}
