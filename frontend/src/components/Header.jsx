import React from 'react'
import { Globe2, History, Radio } from 'lucide-react'

export const Header = ({ activeTab, setActiveTab, isOnline }) => {
  return (
    <header className="header-glass">
      <div className="header-inner">
        {/* Brand */}
        <div className="brand-section">
          <div className="brand-icon">🌐</div>
          <div>
            <div className="brand-title">Echo</div>
            <div className="brand-subtitle">Real-Time Speech & Translation</div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="nav-tabs" aria-label="Main navigation">
          <button
            id="nav-tab-translate"
            type="button"
            className={`nav-tab ${activeTab === 'translate' ? 'active' : ''}`}
            onClick={() => setActiveTab('translate')}
          >
            <Globe2 size={15} />
            Translator
          </button>
          <button
            id="nav-tab-history"
            type="button"
            className={`nav-tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            <History size={15} />
            History
          </button>
          <button
            id="nav-tab-devices"
            type="button"
            className={`nav-tab ${activeTab === 'devices' ? 'active' : ''}`}
            onClick={() => setActiveTab('devices')}
          >
            <Radio size={15} />
            Devices
          </button>
        </nav>

        {/* Online Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div
            style={{
              width: '9px',
              height: '9px',
              borderRadius: '50%',
              backgroundColor:
                isOnline === null
                  ? '#f59e0b'
                  : isOnline
                  ? '#10b981'
                  : '#e11d48',
              boxShadow:
                isOnline === null
                  ? '0 0 6px rgba(245, 158, 11, 0.6)'
                  : isOnline
                  ? '0 0 6px rgba(16, 185, 129, 0.6)'
                  : '0 0 6px rgba(225, 29, 72, 0.6)',
              transition: 'all 0.3s ease',
            }}
          />
          <span
            style={{
              fontSize: '0.78rem',
              fontWeight: 600,
              color: isOnline === null ? '#f59e0b' : isOnline ? '#059669' : '#e11d48',
            }}
          >
            {isOnline === null ? 'Checking…' : isOnline ? 'Backend Online' : 'Backend Offline'}
          </span>
        </div>
      </div>
    </header>
  )
}
