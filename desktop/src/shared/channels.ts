/** IPC channel names shared by main and the preload. */
export const CHANNEL = {
  mode: 'overlay:mode',
  select: 'overlay:select',
  interactive: 'overlay:interactive',
  close: 'overlay:close',
} as const
