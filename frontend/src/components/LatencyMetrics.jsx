import React from 'react'

export const LatencyMetrics = ({ latencies }) => {
  const metrics = [
    {
      label: 'Whisper ASR',
      val: latencies.asr_sec ?? 0,
      icon: (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="22" />
        </svg>
      ),
      className: 'chip-asr',
    },
    {
      label: 'Language ID',
      val: latencies.lid_sec ?? 0,
      icon: (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      ),
      className: 'chip-lid',
    },
    {
      label: 'NLLB-200 MT',
      val: latencies.translation_sec ?? 0,
      icon: (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
      ),
      className: 'chip-mt',
    },
    {
      label: 'Piper TTS',
      val: latencies.tts_sec ?? 0,
      icon: (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
        </svg>
      ),
      className: 'chip-tts',
    },
    {
      label: 'Total Latency',
      val: latencies.total_sec ?? 0,
      icon: (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
      ),
      className: 'chip-total',
    },
  ]

  return (
    <section aria-labelledby="latency-breakdown-title">
      <div style={{ marginBottom: '0.75rem' }}>
        <h2 id="latency-breakdown-title" className="section-title">
          Latency Analytics
        </h2>
      </div>

      <div className="metrics-row">
        {metrics.map((m, idx) => (
          <div key={idx} className={`metric-chip ${m.className}`}>
            <div className="chip-label">
              {m.icon}
              <span>{m.label}</span>
            </div>
            <div className="chip-value">{m.val.toFixed(2)}s</div>
          </div>
        ))}
      </div>
    </section>
  )
}
export default LatencyMetrics
