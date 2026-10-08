import { t } from './i18n'

function App() {
  return (
    <main>
      <h1>{t('app.title')}</h1>
      <p className="muted">{t('app.placeholder')}</p>
    </main>
  )
}

export default App
