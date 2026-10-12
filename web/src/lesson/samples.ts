import type { MessageKey } from '../i18n'
import type { LessonRequest } from './types'

/** Requests whose text matches a golden fixture, so mock mode serves that lesson. */
export const SAMPLES: { label: MessageKey; request: LessonRequest }[] = [
  { label: 'sample.gauss', request: { type: 'topic', text: "Explain Gauss's law" } },
  {
    label: 'sample.series',
    request: {
      type: 'problem',
      text:
        'An ideal 9.0 V battery is connected to three resistors in series: R1 = 100 ohm, ' +
        'R2 = 200 ohm and R3 = 300 ohm. Find the current in the circuit and the voltage across R2.',
    },
  },
]
