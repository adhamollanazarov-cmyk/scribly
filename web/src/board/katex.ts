import katex from 'katex'
import 'katex/dist/katex.min.css'

const cache = new Map<string, string>()

/** KaTeX HTML for a formula. Bad LaTeX renders as red source text, never throws. */
export function renderLatex(latex: string): string {
  let html = cache.get(latex)
  if (html === undefined) {
    html = katex.renderToString(latex, { throwOnError: false, strict: 'ignore', output: 'html' })
    cache.set(latex, html)
  }
  return html
}
