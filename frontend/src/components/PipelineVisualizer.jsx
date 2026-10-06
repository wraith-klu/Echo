import React, { useEffect, useState } from 'react'

export const PipelineVisualizer = ({ isProcessing, wallTimeSec, pipelineResult }) => {
  const [currentStep, setCurrentStep] = useState(5)

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--app-ink)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {isProcessing ? (
            <>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="spin" style={{ color: 'var(--app-accent)' }}>
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
              <span>Processing Translation Pipeline…</span>
            </>
          ) : isPartial ? (
            <>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--state-warning)' }}>
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <span style={{ color: 'var(--state-warning)' }}>Pipeline Complete (Partial Success)</span>
            </>
          ) : (
            <>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--state-success)' }}>
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span>Pipeline Complete</span>
            </>
          )}
        </div>

        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--app-ink-subtle)' }}>
          Wall Time: <span style={{ color: 'var(--app-ink)', fontWeight: 600 }}>{wallTimeSec.toFixed(2)}s</span>
        </div>
      </div>

      <div className="pipeline-steps">
        {steps.map((step, idx) => {
          const stepNum = idx + 1
          const isDone = !isProcessing || currentStep > stepNum
          const isActive = isProcessing && currentStep === stepNum
          const hasError = !isProcessing && step.hasError

          let stepClass = 'pipeline-step'
          if (isActive) stepClass += ' active'
          if (isDone) stepClass += ' completed'
          if (hasError) stepClass += ' error'

          return (
            <React.Fragment key={idx}>
              <div className={stepClass}>
                <div className="step-circle">
                  {hasError ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--state-danger)' }}>
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                  ) : isDone ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--state-success)' }}>
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : isActive ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="spin" style={{ color: 'var(--app-accent)' }}>
                      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                    </svg>
                  ) : (
                    <span>{stepNum}</span>
                  )}
                </div>
                <div className="step-label">
                  {step.label}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--app-ink-subtle)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {hasError ? 'Failed' : step.desc}
                </div>
              </div>
              {idx < steps.length - 1 && <div className="step-line" />}
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}
export default PipelineVisualizer
