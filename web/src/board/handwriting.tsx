import { handRuns } from './handRuns'

export function Handwriting({ text, svg = false }: { text: string; svg?: boolean }) {
  return handRuns(text).map((run, i) => {
    if (run.position === 'normal') return run.text
    if (svg)
      return (
        <tspan key={i} baselineShift={run.position} fontSize="70%">
          {run.text}
        </tspan>
      )
    return run.position === 'super' ? <sup key={i}>{run.text}</sup> : <sub key={i}>{run.text}</sub>
  })
}
