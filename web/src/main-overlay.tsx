import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/caveat/500.css'
import './index.css'
import './overlay/overlay.css'
import { devBridge } from './overlay/bridge'
import { OverlayApp } from './overlay/OverlayApp'
import { DEFAULT_SETTINGS } from './overlay/settings'

// Inside Electron the preload provides the bridge; in a browser a demo bridge stands in.
const bridge = window.scribbly ?? devBridge(DEFAULT_SETTINGS)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <OverlayApp bridge={bridge} />
  </StrictMode>,
)
