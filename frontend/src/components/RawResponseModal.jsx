import React from 'react'

export const RawResponseModal = ({ result }) => {
  const [copied, setCopied] = React.useState(false)
  const jsonStr = JSON.stringify(result.raw || result, null, 2)

  const copyJson = async () => {
    try {
      await navigator.clipboard.writeText(jsonStr)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <details className="debug-expander">
      <summary style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--app-accent)' }}>
            <polyline points="16 18 22 12 16 6" />
            <polyline points="8 6 2 12 8 18" />
          </svg>
          <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 500, color: 'var(--app-ink)' }}>
            Raw JSON Response (Inspect &amp; Telemetry)
          </span>
        </span>
        <button
          type="button"
          className="copy-btn"
          onClick={(e) => {
            e.preventDefault()
            copyJson()
          }}
        >
          {copied ? (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--state-success)' }}>
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
              <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
            </svg>
          )}
          <span>{copied ? 'Copied' : 'Copy JSON'}</span>
        </button>
      </summary>
      <pre>{jsonStr}</pre>
    </details>
  )
}
export default RawResponseModal
