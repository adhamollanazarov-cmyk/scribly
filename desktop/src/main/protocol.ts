// The packaged overlay page is served from app://scribbly/. Same-origin requests to
// /explain-region and /audio/* are proxied to the Scribbly server, like Vite's dev proxy, so
// the page uses relative URLs, lip sync can read the audio, and the CSP stays 'self'.
import { readFile } from 'node:fs/promises'
import { extname, resolve, sep } from 'node:path'
import { net, protocol } from 'electron'

export const SCHEME = 'app'
export const HOST = 'scribbly'
export const PAGE_URL = `${SCHEME}://${HOST}/overlay.html`

export const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'", // KaTeX writes inline styles
  "img-src 'self' data:",
  "font-src 'self' data:",
  "media-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'",
].join('; ')

const TYPES: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.ttf': 'font/ttf',
  '.map': 'application/json',
}

export type Route = { kind: 'proxy' } | { kind: 'file'; path: string } | { kind: 'deny' }

/** What a request to app://scribbly/ may do. Only two server paths are proxied. */
export function routeFor(method: string, pathname: string): Route {
  if (pathname === '/explain-region') {
    return method === 'POST' ? { kind: 'proxy' } : { kind: 'deny' }
  }
  if (/^\/audio\/[0-9a-f]{64}\.mp3$/.test(pathname)) {
    return method === 'GET' ? { kind: 'proxy' } : { kind: 'deny' }
  }
  if (method !== 'GET') return { kind: 'deny' }
  let path: string
  try {
    path = decodeURIComponent(pathname).replace(/^\/+/, '')
  } catch {
    return { kind: 'deny' }
  }
  return { kind: 'file', path: path || 'overlay.html' }
}

/** `relative` inside `root`, or null if it escapes it. */
export function resolveInside(root: string, relative: string): string | null {
  const base = resolve(root)
  const full = resolve(base, relative)
  return full.startsWith(base + sep) ? full : null
}

export function registerScheme(): void {
  protocol.registerSchemesAsPrivileged([
    {
      scheme: SCHEME,
      privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true },
    },
  ])
}

async function serveFile(root: string, relative: string): Promise<Response> {
  const file = resolveInside(root, relative)
  if (!file) return new Response('Not found', { status: 404 })
  try {
    const body = await readFile(file)
    return new Response(body, {
      headers: {
        'Content-Type': TYPES[extname(file).toLowerCase()] ?? 'application/octet-stream',
        'Content-Security-Policy': CSP,
        'X-Content-Type-Options': 'nosniff',
      },
    })
  } catch {
    return new Response('Not found', { status: 404 })
  }
}

async function proxy(request: Request, server: string, url: URL): Promise<Response> {
  const headers: Record<string, string> = {}
  for (const name of ['content-type', 'accept', 'range']) {
    const value = request.headers.get(name)
    if (value) headers[name] = value
  }
  const body = request.method === 'POST' ? await request.arrayBuffer() : undefined
  try {
    return await net.fetch(new URL(url.pathname, server).toString(), {
      method: request.method,
      headers,
      body,
    })
  } catch {
    return new Response('Scribbly server unreachable', { status: 502 })
  }
}

export function handleScheme(root: string, server: string): void {
  protocol.handle(SCHEME, (request) => {
    const url = new URL(request.url)
    if (url.host !== HOST) return new Response('Not found', { status: 404 })
    const route = routeFor(request.method, url.pathname)
    if (route.kind === 'proxy') return proxy(request, server, url)
    if (route.kind === 'file') return serveFile(root, route.path)
    return new Response('Forbidden', { status: 403 })
  })
}
