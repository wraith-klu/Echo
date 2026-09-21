import React, { useState, useEffect, useCallback } from 'react'
import { fetchHistory } from '../utils/api.js'
import { LANG_FLAGS } from '../utils/constants.js'
import { History, RefreshCw, Search, ArrowRight, Clock, CheckCircle2 } from 'lucide-react'

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
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            📜 Translation Session History
          </h2>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Recorded speech utterances stored in PostgreSQL database
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} color="#64748b" style={{ position: 'absolute', left: '10px', top: '10px' }} />
            <input
              type="text"
              placeholder="Search transcriptions…"
              className="input-text"
              style={{ paddingLeft: '2rem', marginTop: 0, width: '220px' }}
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
            <RefreshCw size={14} className={isLoading ? 'spin' : ''} />
            <span>{isLoading ? 'Loading…' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: '1rem',
            borderRadius: '12px',
            backgroundColor: 'rgba(244, 63, 94, 0.12)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            color: '#fb7185',
            fontSize: '0.88rem',
          }}
        >
          Failed to load history from backend: {error}
        </div>
      )}

      {filteredItems.length === 0 && !isLoading && !error && (
        <div className="glass-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <History size={40} color="#64748b" style={{ margin: '0 auto 0.8rem' }} />
          <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>No translation sessions found</div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
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
                <span style={{ fontSize: '1.25rem' }}>
                  {sFlag} <ArrowRight size={14} style={{ display: 'inline', margin: '0 2px' }} /> {tFlag}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  #{shortId}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                  <Clock size={12} /> {dateStr}
                </span>
                <span className="badge-tag" style={{ fontSize: '0.7rem', padding: '0.15rem 0.55rem' }}>
                  {item.device_id}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                {totalLat !== undefined && (
                  <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: '#d97706', fontWeight: 600 }}>
                    ⚡ {totalLat.toFixed(2)}s
                  </span>
                )}
                <span className="status-badge status-ready" style={{ fontSize: '0.7rem' }}>
                  <CheckCircle2 size={12} />
                  {item.status || 'completed'}
                </span>
              </div>
            </div>

            <div className="history-grid">
              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.65)',
                  padding: '0.85rem 1rem',
                  borderRadius: '10px',
                  border: '1px solid var(--border-card)',
                }}
              >
                <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                  Original ({item.source_lang.toUpperCase()})
                </div>
                <div style={{ fontSize: '0.95rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                  {item.original_text || '—'}
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.65)',
                  padding: '0.85rem 1rem',
                  borderRadius: '10px',
                  border: '1px solid var(--border-card)',
                }}
              >
                <div style={{ fontSize: '0.72rem', fontWeight: 700, color: item.target_lang === 'hi' ? '#d97706' : 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                  Translated ({item.target_lang.toUpperCase()})
                </div>
                <div
                  style={{
                    fontSize: '0.95rem',
                    color: item.target_lang === 'hi' ? '#c2410c' : '#4338ca',
                    lineHeight: 1.5,
                    fontFamily: item.target_lang === 'hi' ? 'var(--font-devanagari)' : 'inherit',
                  }}
                >
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
