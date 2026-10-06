import React, { useState, useEffect, useCallback } from 'react'
import { fetchDevices } from '../utils/api.js'

export const DevicesView = ({ baseUrl }) => {
  const [devices, setDevices] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await fetchDevices(baseUrl)
      setDevices(res.items)
    } catch (err) {
      console.error('Failed to load devices:', err)
      setError(err instanceof Error ? err.message : 'Could not fetch registered devices')
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.8rem' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '24px', fontWeight: 400, color: 'var(--app-ink)' }}>
            Connected IoT Fleet &amp; Devices
          </h2>
          <div style={{ fontSize: '13px', color: 'var(--app-ink-subtle)', marginTop: '2px' }}>
            ESP32-S3 modules and client terminals connected to Echo
          </div>
        </div>

        <button
          id="refresh-devices-btn"
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
          <span>{isLoading ? 'Loading…' : 'Refresh Fleet'}</span>
        </button>
      </div>

      {/* Hardware Architecture Note */}
      <div
        className="glass-card"
        style={{
          borderLeft: '3px solid var(--app-accent)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.45rem' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--app-accent)' }}>
            <circle cx="12" cy="12" r="2" />
            <path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14" />
          </svg>
          <span style={{ fontWeight: 600, fontSize: '14px', color: 'var(--app-ink)' }}>ESP32-S3 Real-Time Streaming Interface</span>
        </div>
        <div style={{ fontSize: '13px', color: 'var(--app-ink-muted)', lineHeight: 1.6 }}>
          ESP32 devices stream raw 16-bit 16kHz mono PCM frames over WebSocket at{' '}
          <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--app-accent)' }}>/ws/audio?device_id=ESP32_001</code>.
          The backend runs on-the-fly Voice Activity Detection (VAD) and streams back synthesized WAV audio directly to the I2S speaker.
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
          Failed to fetch devices: {error}
        </div>
      )}

      {devices.length === 0 && !isLoading && !error ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 0.8rem', color: 'var(--app-ink-subtle)' }}>
            <rect width="20" height="8" x="2" y="2" rx="2" ry="2" />
            <rect width="20" height="8" x="2" y="14" rx="2" ry="2" />
            <line x1="6" y1="6" x2="6.01" y2="6" />
            <line x1="6" y1="18" x2="6.01" y2="18" />
          </svg>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '18px', color: 'var(--app-ink)' }}>No devices registered yet</div>
          <div style={{ fontSize: '13px', color: 'var(--app-ink-subtle)', marginTop: '0.3rem' }}>
            Devices register automatically in database when they connect to the backend or trigger translations.
          </div>
        </div>
      ) : (
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Device ID</th>
                <th>Name / Type</th>
                <th>Registered At</th>
                <th>Last Seen</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((dev) => (
                <tr key={dev.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--app-accent)' }}>
                    {dev.device_id}
                  </td>
                  <td>{dev.name || dev.description || 'Generic Client'}</td>
                  <td style={{ color: 'var(--app-ink-subtle)', fontSize: '12px' }}>
                    {dev.registered_at ? dev.registered_at.replace('T', ' ').substring(0, 19) : '—'}
                  </td>
                  <td style={{ color: 'var(--app-ink-subtle)', fontSize: '12px' }}>
                    {dev.last_seen_at ? dev.last_seen_at.replace('T', ' ').substring(0, 19) : '—'}
                  </td>
                  <td>
                    <span className={`status-badge ${dev.is_active ? 'status-ready' : 'status-offline'}`}>
                      {dev.is_active ? 'Active' : 'Offline'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
export default DevicesView
