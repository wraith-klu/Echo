import React, { useEffect, useState } from 'react'
import { Check, Loader2, AlertCircle, AlertTriangle } from 'lucide-react'

export const PipelineVisualizer = ({ isProcessing, wallTimeSec, pipelineResult }) => {
  const [currentStep, setCurrentStep] = useState(5)

  // Emulate visual progress across the 5 pipeline stages while processing
  useEffect(() => {
    if (!isProcessing) {
      return
    }

    const t0 = setTimeout(() => setCurrentStep(1), 0)
    const t1 = setTimeout(() => setCurrentStep(2), 700)
    const t2 = setTimeout(() => setCurrentStep(3), 1800)
    const t3 = setTimeout(() => setCurrentStep(4), 3200)

    return () => {
      clearTimeout(t0)
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
    }
  }, [isProcessing])

  const translationError = pipelineResult?.translation?.error
  const ttsError = pipelineResult?.tts?.error
  const isPartial = !isProcessing && pipelineResult?.status === 'partial_success'

  const steps = [
    { label: 'Audio Ingest & VAD', desc: 'PCM 16kHz Mono', hasError: false },
    { label: 'Whisper ASR', desc: 'Neural Transcription', hasError: false },
    { label: 'Language ID', desc: 'Fused Confidence', hasError: false },
    { label: 'NLLB-200 MT', desc: 'Meta Multilingual', hasError: Boolean(translationError) },
    { label: 'Piper TTS', desc: 'WAV Synthesis', hasError: Boolean(ttsError) },
  ]

  return (
    <div className="pipeline-visualizer">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {isProcessing ? (
            <>
              <Loader2 size={16} className="spin" color="#818cf8" />
              <span>Processing Translation Pipeline…</span>
            </>
          ) : isPartial ? (
            <>
              <AlertTriangle size={16} color="#fbbf24" />
              <span style={{ color: '#fbbf24' }}>Pipeline Complete (Partial Success)</span>
            </>
          ) : (
            <>
              <Check size={16} color="#34d399" />
              <span>Pipeline Complete</span>
            </>
          )}
        </div>

        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          Elapsed: <span style={{ color: '#fbbf24', fontWeight: 700 }}>{wallTimeSec.toFixed(2)}s</span>
        </div>
      </div>

      <div className="pipeline-steps">
        {steps.map((step, idx) => {
          const stepNum = idx + 1
          const isDone = !isProcessing || currentStep > stepNum
          const isActive = isProcessing && currentStep === stepNum
          const hasError = !isProcessing && step.hasError

          return (
            <React.Fragment key={idx}>
              <div className={`pipeline-step ${isActive ? 'active' : ''} ${isDone ? 'completed' : ''} ${hasError ? 'error' : ''}`}>
                <div
                  className="step-circle"
                  style={hasError ? { background: 'rgba(244, 63, 94, 0.2)', borderColor: '#f43f5e', color: '#fb7185' } : undefined}
                >
                  {hasError ? (
                    <AlertCircle size={16} />
                  ) : isDone ? (
                    <Check size={16} />
                  ) : isActive ? (
                    <Loader2 size={16} className="spin" />
                  ) : (
                    stepNum
                  )}
                </div>
                <div className="step-label" style={hasError ? { color: '#fb7185' } : undefined}>
                  {step.label}
                </div>
                <div style={{ fontSize: '0.68rem', color: hasError ? '#fb7185' : 'var(--text-muted)' }}>
                  {hasError ? 'Failed' : step.desc}
                </div>
              </div>
              {idx < steps.length - 1 && (
                <div
                  className="step-line"
                  style={{
                    backgroundColor: isDone
                      ? hasError
                        ? 'rgba(244, 63, 94, 0.4)'
                        : 'rgba(16, 185, 129, 0.4)'
                      : 'var(--border-subtle)',
                  }}
                />
              )}
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}
