import React, { useState } from 'react'
import { ENV_PRESETS } from '../utils/constants.js'
import { Activity, Gauge, Server, RefreshCw } from 'lucide-react'

export const Sidebar = ({
  baseUrl,
  setBaseUrl,
  onPing,
  pingResult,
  isPinging,
  servicesStatus,
  lastLatencies,
}) => {
  const [isCustomUrl, setIsCustomUrl] = useState(false)
  const [customInput, setCustomInput] = useState(baseUrl)

  const handleSelectPreset = (e) => {
    const val = e.target.value
    if (val === 'custom') {
      setIsCustomUrl(true)
    } else {
      setIsCustomUrl(false)
      setBaseUrl(val)
      setCustomInput(val)
    }
  }

  const handleCustomChange = (e) => {
    const val = e.target.value
    setCustomInput(val)
    setBaseUrl(val)
  }

  return (
    <aside className="sidebar-panel">
      {/* Backend Environment Control */}
      <div className="glass-card">
        <div className="card-title-row">
          <span className="card-title">
            <Server size={16} color="#6366f1" />
            Backend Environment
          </span>
        </div>

        <select
          id="env-preset-select"
          className="input-select"
          onChange={handleSelectPreset}
          value={isCustomUrl ? 'custom' : baseUrl}
        >
          {ENV_PRESETS.map((preset) => (
            <option key={preset.id} value={preset.url}>
              {preset.label}
            </option>
          ))}
          <option value="custom">⚙️ Custom Endpoint…</option>
        </select>

        {isCustomUrl ? (
          <input
            id="custom-backend-url-input"
            type="text"
            className="input-text"
            placeholder="http://192.168.1.100:8000"
            value={customInput}
            onChange={handleCustomChange}
          />
        ) : (
          <div
            style={{
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              marginTop: '0.45rem',
              fontFamily: 'var(--font-mono)',
              wordBreak: 'break-all',
            }}
          >
            {baseUrl || 'Vite Proxy (localhost:3000 -> 8000)'}
          </div>
        )}

        <div style={{ marginTop: '1rem' }}>
          <button
            id="ping-backend-btn"
            className="btn btn-secondary btn-w100"
            onClick={onPing}
            disabled={isPinging}
          >
            <RefreshCw size={14} className={isPinging ? 'spin' : ''} />
            <span>{isPinging ? 'Checking…' : 'Ping Backend'}</span>
          </button>
        </div>

        {pingResult && (
          <div
            style={{
              marginTop: '0.75rem',
              fontSize: '0.8rem',
              padding: '0.5rem 0.75rem',
              borderRadius: '8px',
              backgroundColor: pingResult.error
                ? 'rgba(244, 63, 94, 0.12)'
                : 'rgba(16, 185, 129, 0.12)',
              border: `1px solid ${
                pingResult.error ? 'rgba(244, 63, 94, 0.3)' : 'rgba(16, 185, 129, 0.3)'
              }`,
              color: pingResult.error ? '#fb7185' : '#34d399',
            }}
          >
            {pingResult.error ? (
              <div>❌ {pingResult.error}</div>
            ) : (
              <div>✅ Online · {pingResult.latencyMs} ms</div>
            )}
          </div>
        )}
      </div>

      {/* Subsystem Readiness Card */}
      <div className="glass-card">
        <div className="card-title-row">
          <span className="card-title">
            <Activity size={16} color="#06b6d4" />
            Pipeline Subsystems
          </span>
        </div>

        <div className="services-list">
          <div className="service-item">
            <span className="service-name">Ingestion & VAD</span>
            <span className="status-badge status-ready">ready</span>
          </div>
          <div className="service-item">
            <span className="service-name">Whisper ASR</span>
            <span
              className={`status-badge ${
                servicesStatus?.asr === 'ready' ? 'status-ready' : 'status-pending'
              }`}
            >
              {servicesStatus?.asr || 'ready'}
            </span>
          </div>
          <div className="service-item">
            <span className="service-name">NLLB-200 MT</span>
            <span
              className={`status-badge ${
                servicesStatus?.translation === 'ready' ? 'status-ready' : 'status-pending'
              }`}
            >
              {servicesStatus?.translation || 'ready'}
            </span>
          </div>
          <div className="service-item">
            <span className="service-name">Piper TTS</span>
            <span
              className={`status-badge ${
                servicesStatus?.tts === 'ready' ? 'status-ready' : 'status-pending'
              }`}
            >
              {servicesStatus?.tts || 'ready'}
            </span>
          </div>
        </div>
      </div>

      {/* Quick Session Stats */}
      <div className="glass-card">
        <div className="card-title-row">
          <span className="card-title">
            <Gauge size={16} color="#f59e0b" />
            Last Run Latency
          </span>
        </div>

        {lastLatencies ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.82rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#fbbf24', fontWeight: 700 }}>
              <span>Total Wall-Clock:</span>
              <span>{(lastLatencies.total_sec ?? 0).toFixed(2)}s</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
              <span>Whisper ASR:</span>
              <span>{(lastLatencies.asr_sec ?? 0).toFixed(2)}s</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
              <span>NLLB-200 MT:</span>
              <span>{(lastLatencies.translation_sec ?? 0).toFixed(2)}s</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
              <span>Piper TTS:</span>
              <span>{(lastLatencies.tts_sec ?? 0).toFixed(2)}s</span>
            </div>
          </div>
        ) : (
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            No translation executed in current session yet.
          </div>
        )}
      </div>

      <div style={{ textAlign: 'center', padding: '0.5rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
        CapsTron v1.0 · ESP32 + FastAPI + NLLB-200
      </div>
    </aside>
  )
}
