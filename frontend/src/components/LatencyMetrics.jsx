import React from 'react'
import { Mic, Search, Globe, Volume2, Zap } from 'lucide-react'

export const LatencyMetrics = ({ latencies }) => {
  const metrics = [
    {
      label: 'Whisper ASR',
      val: latencies.asr_sec ?? 0,
      icon: <Mic size={14} color="#38bdf8" />,
      className: 'chip-asr',
    },
    {
      label: 'Language ID',
      val: latencies.lid_sec ?? 0,
      icon: <Search size={14} color="#2dd4bf" />,
      className: 'chip-lid',
    },
    {
      label: 'NLLB-200 MT',
      val: latencies.translation_sec ?? 0,
      icon: <Globe size={14} color="#a78bfa" />,
      className: 'chip-mt',
    },
    {
      label: 'Piper TTS',
      val: latencies.tts_sec ?? 0,
      icon: <Volume2 size={14} color="#34d399" />,
      className: 'chip-tts',
    },
    {
      label: 'Total Latency',
      val: latencies.total_sec ?? 0,
      icon: <Zap size={14} color="#fbbf24" />,
      className: 'chip-total',
    },
  ]

  return (
    <section aria-labelledby="latency-breakdown-title">
      <div style={{ marginBottom: '0.6rem' }}>
        <h2 id="latency-breakdown-title" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)' }}>
          ⏱️ Latency Analytics
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
