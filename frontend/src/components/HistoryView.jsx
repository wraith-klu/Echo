import React, { useState, useEffect, useCallback } from 'react'
import { fetchHistory } from '../utils/api.js'
import { LANG_FLAGS } from '../utils/constants.js'

export const HistoryView = ({ baseUrl }) => {
  const [items, setItems] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')

  const loadData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await fetchHistory(baseUrl, 30)
      setItems(res.items)
    } catch (err) {
      console.error('Failed to load history:', err)
      setError(err instanceof Error ? err.message : 'Could not fetch history')
    } finally {
      setIsLoading(false)
    }
  }, [baseUrl])

  useEffect(() => {
    const timer = setTimeout(() => {
      loadData()
    }, 0)
    return () => clearTimeout(timer)
  }, [loadData])

  const filteredItems = items.filter((item) => {
    const term = searchTerm.toLowerCase()
    return (
      item.original_text?.toLowerCase().includes(term) ||
      item.translated_text?.toLowerCase().includes(term) ||
      item.source_lang?.toLowerCase().includes(term) ||
      item.target_lang?.toLowerCase().includes(term) ||
      item.device_id?.toLowerCase().includes(term)
    )
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.8rem' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '24px', fontWeight: 400, color: 'var(--app-ink)' }}>
            Translation Session History
          </h2>
          <div style={{ fontSize: '13px', color: 'var(--app-ink-subtle)', marginTop: '2px' }}>
            Persisted speech utterances and latency telemetry
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div style={{ position: 'relative' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ position: 'absolute', left: '11px', top: '13px', color: 'var(--app-ink-subtle)' }}>
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              placeholder="Search transcriptions…"
              className="input-text"
              style={{ paddingLeft: '2.1rem', marginTop: 0, width: '220px' }}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <button
            id="refresh-history-btn"
            type="button"
            className="btn btn-secondary"
            onClick={loadData}
            disabled={isLoading}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={isLoading ? 'spin' : ''}>
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
              <path d="M16 21h5v-5" />
            </svg>
            <span>{isLoading ? 'Loading…' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: '1rem',
            borderRadius: '8px',
            backgroundColor: 'rgba(248, 113, 113, 0.12)',
            border: '1px solid var(--state-danger)',
            color: 'var(--state-danger)',
            fontSize: '13px',
          }}
        >
          Failed to load history from backend: {error}
        </div>
      )}

      {filteredItems.length === 0 && !isLoading && !error && (
        <div className="glass-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 0.8rem', color: 'var(--app-ink-subtle)' }}>
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '18px', color: 'var(--app-ink)' }}>No translation sessions found</div>
          <div style={{ fontSize: '13px', color: 'var(--app-ink-subtle)', marginTop: '0.3rem' }}>
            Run speech translations in the Translator tab to record sessions here.
          </div>
        </div>
      )}

      {filteredItems.map((item) => {
        const sFlag = LANG_FLAGS[item.source_lang] || '🌐'
        const tFlag = LANG_FLAGS[item.target_lang] || '🌐'
        const shortId = item.id.substring(0, 8)
        const dateStr = item.created_at ? item.created_at.replace('T', ' ').substring(0, 19) : '—'
        const totalLat = item.latencies?.total_sec

        return (
          <div key={item.id} className="history-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <span style={{ fontSize: '1.2rem' }}>
                  {sFlag} → {tFlag}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--app-ink-subtle)' }}>
                  #{shortId}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--app-ink-subtle)', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                  {dateStr}
                </span>
                <span className="badge-tag" style={{ fontSize: '11px', padding: '2px 8px' }}>
                  {item.device_id}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                {totalLat !== undefined && (
                  <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--app-accent)', fontWeight: 600 }}>
                    {totalLat.toFixed(2)}s
                  </span>
                )}
                <span className="status-badge status-ready">
                  {item.status || 'completed'}
                </span>
              </div>
            </div>

            <div className="history-grid">
              <div>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--app-ink-subtle)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.35rem' }}>
                  Original Speech ({item.source_lang?.toUpperCase()})
                </div>
                <div style={{ background: 'var(--app-surface-hover)', border: '1px solid var(--app-rule)', borderRadius: '7px', padding: '0.8rem 1rem', fontSize: '14px', color: 'var(--app-ink)' }}>
                  {item.original_text || '—'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--app-accent)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.35rem' }}>
                  Translated ({item.target_lang?.toUpperCase()})
                </div>
                <div style={{ background: 'var(--app-surface-hover)', border: '1px solid var(--app-rule)', borderRadius: '7px', padding: '0.8rem 1rem', fontSize: '14px', color: 'var(--app-ink)' }}>
                  {item.translated_text || '—'}
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
export default HistoryView
