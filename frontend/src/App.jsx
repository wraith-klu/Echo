import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Header } from './components/Header.jsx'
import { Sidebar } from './components/Sidebar.jsx'
import { LanguageSelector } from './components/LanguageSelector.jsx'
import { AudioStudio } from './components/AudioStudio.jsx'
import { PipelineVisualizer } from './components/PipelineVisualizer.jsx'
import { ResultsPanel } from './components/ResultsPanel.jsx'
import { LatencyMetrics } from './components/LatencyMetrics.jsx'
import { HistoryView } from './components/HistoryView.jsx'
import { DevicesView } from './components/DevicesView.jsx'
import { RawResponseModal } from './components/RawResponseModal.jsx'
import { pingBackend, fetchServicesStatus, transcribeAudio } from './utils/api.js'
import { AlertTriangle, Sparkles, Mic, Globe2, Volume2, Cpu } from 'lucide-react'

export const App = () => {
  const [activeTab, setActiveTab] = useState('translate')
  const [baseUrl, setBaseUrl] = useState('http://localhost:8000')

  // Backend Health State
  const [isOnline, setIsOnline] = useState(null)
  const [isPinging, setIsPinging] = useState(false)
  const [pingResult, setPingResult] = useState(null)
  const [servicesStatus, setServicesStatus] = useState(null)

  // Language Config State
  const [sourceLang, setSourceLang] = useState('auto')
  const [targetLang, setTargetLang] = useState('hi')

  // Audio State
  const [audioBlob, setAudioBlob] = useState(null)
  const [audioDuration, setAudioDuration] = useState(0)

  // Pipeline Execution State
  const [isProcessing, setIsProcessing] = useState(false)
  const [wallTimeSec, setWallTimeSec] = useState(0)
  const [pipelineResult, setPipelineResult] = useState(null)
  const [pipelineError, setPipelineError] = useState(null)
  const [lastLatencies, setLastLatencies] = useState(null)

  const timerRef = useRef(null)

  const checkHealth = useCallback(async () => {
    setIsPinging(true)
    try {
      const res = await pingBackend(baseUrl)
      setIsOnline(true)
      setPingResult({ latencyMs: res.latencyMs })

      try {
        const services = await fetchServicesStatus(baseUrl)
        setServicesStatus(services)
      } catch {
        // Non-fatal if /status is not yet populated
      }
    } catch (err) {
      setIsOnline(false)
      setPingResult({
        error: err instanceof Error ? err.message : 'Backend unreachable',
      })
      setServicesStatus(null)
    } finally {
      setIsPinging(false)
    }
  }, [baseUrl])

  // Initial Ping on mount & baseUrl change
  useEffect(() => {
    const timer = setTimeout(() => {
      checkHealth()
    }, 0)
    return () => clearTimeout(timer)
  }, [checkHealth])

  const handleAudioReady = (blob, duration) => {
    setAudioBlob(blob)
    setAudioDuration(duration)
    setPipelineError(null)
  }

  const handleExecuteTranslate = async () => {
    if (!audioBlob) return

    setIsProcessing(true)
    setPipelineError(null)
    setWallTimeSec(0)
    const startTime = performance.now()

    timerRef.current = window.setInterval(() => {
      setWallTimeSec((performance.now() - startTime) / 1000)
    }, 100)

    try {
      const result = await transcribeAudio(baseUrl, audioBlob, targetLang, sourceLang)
      const elapsed = (performance.now() - startTime) / 1000
      setWallTimeSec(elapsed)

      const lat = {
        ...result.latencies,
        total_sec: result.latencies?.total_sec ?? elapsed,
      }

      setPipelineResult(result)
      setLastLatencies(lat)
    } catch (err) {
      console.error('Translation pipeline failed:', err)
      setPipelineError(
        err instanceof Error
          ? err.message
          : 'Pipeline execution failed. Please ensure the backend server is running.'
      )
    } finally {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      setIsProcessing(false)
    }
  }

  return (
    <div className="app-container">
      {/* Header Bar */}
      <Header activeTab={activeTab} setActiveTab={setActiveTab} isOnline={isOnline} />

      {/* Hero Header */}
      <div className="hero-box">
        <h1 className="hero-h1">🌐 Echo Translation Portal</h1>
        <p className="hero-p">
          Real-time multilingual speech translation pipeline combining Whisper ASR, Meta NLLB-200, and Piper Neural TTS for edge IoT devices.
        </p>
        <div className="badges-row">
          <span className="badge-tag">
            <Mic size={13} /> Real-time ASR
          </span>
          <span className="badge-tag">
            <Globe2 size={13} /> 100+ Languages
          </span>
          <span className="badge-tag">
            <Volume2 size={13} /> Neural TTS
          </span>
          <span className="badge-tag badge-hindi">
            <Sparkles size={13} /> Hindi Devanagari
          </span>
          <span className="badge-tag">
            <Cpu size={13} /> ESP32 Edge Ready
          </span>
        </div>
      </div>

      {/* Main Content Layout */}
      <main className="main-layout">
        {/* Sidebar Controls */}
        <Sidebar
          baseUrl={baseUrl}
          setBaseUrl={setBaseUrl}
          onPing={checkHealth}
          pingResult={pingResult}
          isPinging={isPinging}
          servicesStatus={servicesStatus}
          lastLatencies={lastLatencies}
        />

        {/* Dynamic Center Panel */}
        <div className="content-area">
          {activeTab === 'translate' && (
            <>
              {/* Language Selection Bar */}
              <LanguageSelector
                sourceLang={sourceLang}
                setSourceLang={setSourceLang}
                targetLang={targetLang}
                setTargetLang={setTargetLang}
              />

              {/* Audio Studio Recorder & Player */}
              <AudioStudio
                onAudioReady={handleAudioReady}
                onExecuteTranslate={handleExecuteTranslate}
                isProcessing={isProcessing}
                hasAudioReady={audioBlob !== null}
                audioBlob={audioBlob}
                audioDuration={audioDuration}
              />

              {/* Pipeline Progress Visualizer */}
              {(isProcessing || wallTimeSec > 0) && (
                <PipelineVisualizer
                  isProcessing={isProcessing}
                  wallTimeSec={wallTimeSec}
                  pipelineResult={pipelineResult}
                />
              )}

              {/* Error Message Display */}
              {pipelineError && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.6rem',
                    background: 'rgba(244, 63, 94, 0.12)',
                    border: '1px solid rgba(244, 63, 94, 0.3)',
                    borderRadius: '14px',
                    padding: '1.1rem 1.4rem',
                    color: '#fb7185',
                    fontSize: '0.9rem',
                  }}
                >
                  <AlertTriangle size={20} />
                  <div>
                    <strong>Pipeline Error:</strong> {pipelineError}
                  </div>
                </div>
              )}

              {/* Translation Output Cards */}
              {pipelineResult && !isProcessing && (
                <>
                  <ResultsPanel
                    result={pipelineResult}
                    baseUrl={baseUrl}
                    targetLang={targetLang}
                  />

                  {pipelineResult.latencies && (
                    <LatencyMetrics latencies={pipelineResult.latencies} />
                  )}

                  <RawResponseModal result={pipelineResult} />
                </>
              )}
            </>
          )}

          {activeTab === 'history' && <HistoryView baseUrl={baseUrl} />}

          {activeTab === 'devices' && <DevicesView baseUrl={baseUrl} />}
        </div>
      </main>
    </div>
  )
}

export default App
