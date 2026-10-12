// Render Unicode exponents with Caveat's ordinary glyphs. Its font lacks U+207B.
const SUPER = '⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺⁼⁽⁾'
const SUB = '₀₁₂₃₄₅₆₇₈₉₋₊₌₍₎'
const PLAIN = '0123456789-+=()'

export interface HandRun {
  text: string
  position: 'normal' | 'super' | 'sub'
}

export function handRuns(text: string): HandRun[] {
  const runs: HandRun[] = []
  for (const char of text) {
    const sup = SUPER.indexOf(char)
    const sub = SUB.indexOf(char)
    const position = sup >= 0 ? 'super' : sub >= 0 ? 'sub' : 'normal'
    const glyph = sup >= 0 ? PLAIN[sup] : sub >= 0 ? PLAIN[sub] : char
    if (runs.at(-1)?.position === position) runs.at(-1)!.text += glyph
    else runs.push({ text: glyph, position })
  }
  return runs
}
