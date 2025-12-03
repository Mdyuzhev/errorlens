# Bookmarklet

This directory contains the ErrorLens bookmarklet — a JavaScript snippet that can be saved as a browser bookmark to record errors on any webpage.

## How it works

1. User clicks the bookmarklet
2. Script injects into the current page
3. Starts listening to console, network, and JS errors
4. Shows a floating "Recording" indicator
5. User reproduces the bug
6. User clicks to stop recording
7. Data is sent to backend for AI analysis
8. Results displayed in a popup overlay

## Files

- `recorder.js` — Main bookmarklet source code
- `build.js` — Script to minify and generate bookmarklet URL (coming soon)

## Development

The bookmarklet is vanilla JavaScript with no dependencies. To test locally:

1. Start the backend server
2. Open `recorder.js` and update the API_URL if needed
3. Copy the code and paste into browser console, or create a bookmark manually
