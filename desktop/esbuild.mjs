// Bundles Electron's main process and the preload into one CommonJS file each.
// The sandboxed preload cannot require local files, so bundling is required; main also
// pulls pure helpers (geometry, settings, i18n) from ../web/src.
import { build } from 'esbuild'

const common = {
  bundle: true,
  platform: 'node',
  format: 'cjs',
  target: 'node22',
  external: ['electron'],
  sourcemap: true,
  logLevel: 'warning',
}

await Promise.all([
  build({ ...common, entryPoints: ['src/main/main.ts'], outfile: 'dist/main.js' }),
  build({ ...common, entryPoints: ['src/preload/preload.ts'], outfile: 'dist/preload.js' }),
])
