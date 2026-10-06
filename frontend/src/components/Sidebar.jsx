import React, { useState } from 'react'
import { ENV_PRESETS } from '../utils/constants.js'

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
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--app-accent)' }}>
              <rect width="20" height="8" x="2" y="2" rx="2" ry="2" />
              <rect width="20" height="8" x="2" y="14" rx="2" ry="2" />
              <line x1="6" y1="6" x2="6.01" y2="6" />
              <line x1="6" y1="18" x2="6.01" y2="18" />
            </svg>
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
              fontSize: '12px',
              color: 'var(--app-ink-subtle)',
              marginTop: '0.45rem',
              fontFamily: 'var(--font-mono)',
              wordBreak: 'break-all',
            }}
          >
            {baseUrl || 'Vite Proxy (localhost:3000 -> 8000)'}
          </div>
        )}

        <div style={{ marginTop: '0.9rem' }}>
          <button
            id="ping-backend-btn"
            className="btn btn-secondary btn-w100"
            onClick={onPing}
            disabled={isPinging}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={isPinging ? 'spin' : ''}>
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
              <path d="M16 21h5v-5" />
            </svg>
            <span>{isPinging ? 'Checking…' : 'Ping Backend'}</span>
          </button>
        </div>

        {pingResult && (
          <div
            style={{
              marginTop: '0.75rem',
              fontSize: '13px',
              padding: '8px 12px',
              borderRadius: '7px',
              backgroundColor: pingResult.error
                ? 'rgba(248, 113, 113, 0.12)'
                : 'rgba(52, 211, 153, 0.12)',
              border: `1px solid ${
                pingResult.error ? 'var(--state-danger)' : 'var(--state-success)'
              }`,
              color: pingResult.error ? 'var(--state-danger)' : 'var(--state-success)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {pingResult.error ? (
              <div>{pingResult.error}</div>
            ) : (
              <div>Online · {pingResult.latencyMs} ms</div>
            )}
          </div>
        )}
      </div>

      {/* Subsystem Readiness Card */}
      <div className="glass-card">
        <div className="card-title-row">
          <span className="card-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--app-accent)' }}>
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            Pipeline Subsystems
          </span>
        </div>

        <div className="services-list">
          <div className="service-item">
            <span className="service-name">Ingestion &amp; VAD</span>
            <span className="status-badge status-ready">Ready</span>
          </div>
          <div className="service-item">
            <span className="service-name">Whisper ASR</span>
            <span
              className={`status-badge ${
                servicesStatus?.asr === 'ready' ? 'status-ready' : 'status-pending'
              }`}
            >
              {servicesStatus?.asr || 'Ready'}
            </span>
          </div>
          <div className="service-item">
            <span className="service-name">NLLB-200 MT</span>
            <span
              className={`status-badge ${
                servicesStatus?.translation === 'ready' ? 'status-ready' : 'status-pending'
              }`}
            >
              {servicesStatus?.translation || 'Ready'}
            </span>
          </div>
          <div className="service-item">
            <span className="service-name">Piper TTS</span>
            <span
              className={`status-badge ${
                servicesStatus?.tts === 'ready' ? 'status-ready' : 'status-pending'
              }`}
            >
              {servicesStatus?.tts || 'Ready'}
            </span>
          </div>
        </div>
      </div>

      {/* Quick Session Stats */}
      <div className="glass-card">
        <div className="card-title-row">
          <span className="card-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--app-accent)' }}>
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 14 14" />
            </svg>
            Last Run Latency
          </span>
        </div>

        {lastLatencies ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', fontSize: '13px', fontFamily: 'var(--font-mono)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--app-accent)', fontWeight: 600 }}>
              <span>Total Wall-Clock:</span>
              <span>{(lastLatencies.total_sec ?? 0).toFixed(2)}s</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--app-ink-muted)' }}>
              <span>Whisper ASR:</span>
              <span>{(lastLatencies.asr_sec ?? 0).toFixed(2)}s</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--app-ink-muted)' }}>
              <span>NLLB-200 MT:</span>
              <span>{(lastLatencies.translation_sec ?? 0).toFixed(2)}s</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--app-ink-muted)' }}>
              <span>Piper TTS:</span>
              <span>{(lastLatencies.tts_sec ?? 0).toFixed(2)}s</span>
            </div>
          </div>
        ) : (
          <div style={{ fontSize: '13px', color: 'var(--app-ink-subtle)' }}>
            No translation executed in current session yet.
          </div>
        )}
      </div>

      <div style={{ textAlign: 'center', padding: '0.5rem', fontSize: '11px', color: 'var(--app-ink-subtle)', letterSpacing: '0.04em' }}>
        Echo Speech Translation Portal
      </div>
    </aside>
  )
}
export default Sidebar
