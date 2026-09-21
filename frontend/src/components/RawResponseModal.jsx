import React from 'react'
import { Code, Copy, Check } from 'lucide-react'

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
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
          <Code size={15} color="#0284c7" />
          <span>🔬 Raw JSON Response (Inspect & Debug)</span>
        </span>
        <button
          type="button"
          className="copy-btn"
          onClick={(e) => {
            e.preventDefault()
            copyJson()
          }}
        >
          {copied ? <Check size={12} color="#34d399" /> : <Copy size={12} />}
          <span>{copied ? 'Copied' : 'Copy JSON'}</span>
        </button>
      </summary>
      <pre>{jsonStr}</pre>
    </details>
  )
}
