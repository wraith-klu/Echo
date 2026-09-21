import React, { useState, useEffect, useCallback } from 'react'
import { fetchDevices } from '../utils/api.js'
import { RefreshCw, Radio, HardDrive } from 'lucide-react'

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
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            🛰️ Connected IoT Fleet &amp; Devices
          </h2>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Hardware ESP32-S3 modules, web clients, and test clients communicating with CapsTron
          </div>
        </div>

        <button
          id="refresh-devices-btn"
          type="button"
          className="btn btn-secondary"
          onClick={loadData}
          disabled={isLoading}
        >
          <RefreshCw size={14} className={isLoading ? 'spin' : ''} />
          <span>{isLoading ? 'Loading…' : 'Refresh Fleet'}</span>
        </button>
      </div>

      {/* Hardware Architecture Note */}
      <div
        className="glass-card"
        style={{
          borderLeft: '4px solid var(--accent-violet)',
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.06) 0%, rgba(139, 92, 246, 0.03) 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.45rem' }}>
          <Radio size={18} color="#818cf8" />
          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>ESP32-S3 Real-Time Streaming Interface</span>
        </div>
        <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          ESP32 devices stream raw 16-bit 16kHz mono PCM frames over WebSocket at{' '}
          <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>/ws/audio?device_id=ESP32_001</code>.
          The backend runs on-the-fly Voice Activity Detection (VAD) and streams back synthesized WAV audio directly to the I2S speaker.
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
          Failed to fetch devices: {error}
        </div>
      )}

      {devices.length === 0 && !isLoading && !error ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <HardDrive size={40} color="#64748b" style={{ margin: '0 auto 0.8rem' }} />
          <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>No devices registered yet</div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
            Devices register automatically in PostgreSQL when they connect to the backend or trigger translations.
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
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                    {dev.device_id}
                  </td>
                  <td>{dev.name || dev.description || 'Generic Client'}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {dev.registered_at ? dev.registered_at.replace('T', ' ').substring(0, 19) : '—'}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
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
