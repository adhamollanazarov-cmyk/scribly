import katex from 'katex'
import 'katex/dist/katex.min.css'

const caches = { html: new Map<string, string>(), mathml: new Map<string, string>() }

/** KaTeX HTML for a formula. Bad LaTeX renders as red source text, never throws. */
export function renderLatex(latex: string, output: 'html' | 'mathml' = 'html'): string {
  const cache = caches[output]
  let html = cache.get(latex)
  if (html === undefined) {
    html = katex.renderToString(latex, { throwOnError: false, strict: 'ignore', output })
    cache.set(latex, html)
  }
  return html
}
