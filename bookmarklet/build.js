/**
 * Build script for ErrorLens Bookmarklet
 * Uses esbuild to bundle ES modules into IIFE
 */
const esbuild = require('esbuild');
const fs = require('fs');
const path = require('path');

const isWatch = process.argv.includes('--watch');

async function build() {
  try {
    const result = await esbuild.build({
      entryPoints: ['src/index.js'],
      bundle: true,
      minify: !isWatch,
      format: 'iife',
      target: ['es2020'],
      outfile: 'recorder.min.js',
      sourcemap: isWatch ? 'inline' : false,
      logLevel: 'info',
    });

    // Get file size
    const stats = fs.statSync('recorder.min.js');
    const sizeKb = (stats.size / 1024).toFixed(1);

    console.log(`\n✅ Bookmarklet built successfully!`);
    console.log(`📦 Output: recorder.min.js (${sizeKb} KB)`);

    // Also create a dev version (unminified)
    if (!isWatch) {
      await esbuild.build({
        entryPoints: ['src/index.js'],
        bundle: true,
        minify: false,
        format: 'iife',
        target: ['es2020'],
        outfile: 'recorder.dev.js',
      });
      console.log(`📦 Dev version: recorder.dev.js`);
    }

  } catch (err) {
    console.error('❌ Build failed:', err);
    process.exit(1);
  }
}

if (isWatch) {
  console.log('👀 Watching for changes...');

  const ctx = esbuild.context({
    entryPoints: ['src/index.js'],
    bundle: true,
    minify: false,
    format: 'iife',
    target: ['es2020'],
    outfile: 'recorder.min.js',
    sourcemap: 'inline',
    logLevel: 'info',
  }).then(ctx => {
    ctx.watch();
  });
} else {
  build();
}
