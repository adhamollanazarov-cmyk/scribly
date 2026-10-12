export type MascotState =
  | 'idle'
  | 'drawing'
  | 'talking'
  | 'listening'
  | 'thinking'
  | 'happy'
  | 'encouraging'
  // overlay movements (desktop)
  | 'pointing'
  | 'flying'
  | 'appearing'
  | 'disappearing'

export const MASCOT_STATES: readonly MascotState[] = [
  'idle',
  'drawing',
  'talking',
  'listening',
  'thinking',
  'happy',
  'encouraging',
  'pointing',
  'flying',
  'appearing',
  'disappearing',
]
