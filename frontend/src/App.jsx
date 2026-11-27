import { useState, useCallback } from 'react'
import UploadPanel from './components/UploadPanel.jsx'
import ResultsDashboard from './components/ResultsDashboard.jsx'
import LoadingState from './components/LoadingState.jsx'
import { verifyDocuments, loadDemo, DEMO_MODE } from './api.js'
import './App.css'
import PortfolioBadge from './components/PortfolioBadge'

export default function App() {
  const [idFile, setIdFile] = useState(null)
  const [supportFile, setSupportFile] = useState(null)
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleAnalyze = useCallback(async () => {
    if (!idFile) return
    setStatus('loading')
    setResult(null)
    setError(null)

    try {
      const data = await verifyDocuments(idFile, supportFile)
      setResult(data)
      setStatus('done')
    } catch (e) {
      setError(e.message)
      setStatus('error')
    }
  }, [idFile, supportFile])

  const handleDemo = useCallback(async (scenarioId) => {
    setStatus('loading')
    setResult(null)
    setError(null)
    try {
      const data = await loadDemo(scenarioId)
      setResult(data)
      setStatus('done')
    } catch (e) {
      setError(e.message)
      setStatus('error')
    }
  }, [])

  const handleReset = () => {
    setStatus('idle')
    setResult(null)
    setError(null)
  }

  return (
    <div className="app-shell">
      <header className="app-header fade-up">
        <div className="header-left">
          <div className="logo-mark">🔐</div>
          <div>
            <h1 className="app-title">ID Verify <span>AI</span></h1>
            <p className="app-sub">VillageHacks 2026 · Notary Everyday</p>
          </div>
        </div>
        <div className="header-right">
          <div className="level-chips">
            {['LV1 AUTHENTIC', 'LV2 EXTRACT', 'LV3 CROSS-DOC', 'LV4 COMPLY'].map((l, i) => (
              <span key={i} className={`chip chip-${i + 1}`}>{l}</span>
            ))}
          </div>
        </div>
      </header>

      <main className="app-main">
        {status === 'idle' || status === 'error' ? (
          <UploadPanel
            idFile={idFile}
            supportFile={supportFile}
            onIdFile={setIdFile}
            onSupportFile={setSupportFile}
            onAnalyze={handleAnalyze}
            onDemo={handleDemo}
            error={error}
            demoMode={DEMO_MODE}
          />
        ) : status === 'loading' ? (
          <LoadingState />
        ) : (
          <ResultsDashboard result={result} onReset={handleReset} />
        )}
      </main>
      <footer className="sm-badge-row"><PortfolioBadge /></footer>
    </div>
  )
}