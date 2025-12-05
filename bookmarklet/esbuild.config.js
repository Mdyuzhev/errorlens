/**
 * Build script for ErrorLens Bookmarklet
 * Uses esbuild to bundle ES modules into IIFE
 */
const esbuild = require('esbuild');
const fs = require('fs');

const isWatch = process.argv.includes('--watch');
const isMinify = process.argv.includes('--minify');

const config = {
  entryPoints: ['src/index.js'],
  bundle: true,
  format: 'iife',
  globalName: 'ErrorLens',
  outfile: isMinify ? 'dist/recorder.min.js' : 'dist/recorder.js',
  minify: isMinify,
  sourcemap: !isMinify,
  target: ['es2020'],
  banner: {
    js: `/* ErrorLens Bookmarklet v2.0.0 - ${new Date().toISOString().split('T')[0]} */`
  }
};

// Ensure dist/ directory exists
if (!fs.existsSync('dist')) {
  fs.mkdirSync('dist');
}

if (isWatch) {
  esbuild.context(config).then(ctx => {
    ctx.watch();
    console.log('👀 Watching for changes...');
  });
} else {
  esbuild.build(config).then(() => {
    const stats = fs.statSync(config.outfile);
    const sizeKb = (stats.size / 1024).toFixed(1);
    console.log(`✅ Built: ${config.outfile} (${sizeKb} KB)`);
  }).catch(err => {
    console.error('❌ Build failed:', err);
    process.exit(1);
  });
}
