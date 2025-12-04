/**
 * ErrorLens Bookmarklet - Entry Point
 *
 * This is the main entry point for the bookmarklet.
 * It initializes the widget or removes it if already loaded.
 */
import { createWidget, removeWidget, isWidgetVisible } from './ui/widget.js';
import { CONFIG } from './core/config.js';
import { getState } from './core/state.js';

// Main initialization
(function init() {
  // Check if already loaded
  if (window.__ERRORLENS_LOADED__) {
    const state = getState();

    // If recording, ask before removing
    if (state.isRecording) {
      if (!confirm('ErrorLens записывает сессию. Остановить и закрыть?')) {
        return;
      }
    }

    // Check for existing results
    if (window.__errorLensResults) {
      const choice = confirm('Есть результаты прошлой записи.\n\nОК = Показать результаты\nОтмена = Новая запись');
      if (choice) {
        // Show existing results - TODO: implement
        console.log('[ErrorLens] Showing existing results');
      }
    }

    console.log('[ErrorLens] Removing existing instance...');
    removeWidget();
    window.__ERRORLENS_LOADED__ = false;
    return;
  }

  // Initialize
  console.log(`[ErrorLens] v${CONFIG.VERSION} initializing...`);
  createWidget();
  window.__ERRORLENS_LOADED__ = true;
})();
