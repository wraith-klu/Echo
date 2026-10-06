import React from 'react'
import { LANG_FLAGS, LANG_NAMES } from '../utils/constants.js'
import { getTTSAudioUrl } from '../utils/api.js'

export const ResultsPanel = ({ result, baseUrl, targetLang }) => {
  const [copiedOriginal, setCopiedOriginal] = React.useState(false)
  const [copiedTranslated, setCopiedTranslated] = React.useState(false)

  const transcription = result.transcription
  const translation = result.translation
  const tts = result.tts

  const detLang = transcription?.language_detection?.detected_language || 'auto'
  const confidence = transcription?.language_detection?.confidence ?? 1.0
  const isHindiTarget = targetLang === 'hi' || translation?.target_language === 'hi'

  const origText = transcription?.text || 'No speech detected.'
  const transText = translation?.translated_text || ''

  const copyToClipboard = async (text, isOriginal) => {
    try {
      await navigator.clipboard.writeText(text)
      if (isOriginal) {
        setCopiedOriginal(true)
        setTimeout(() => setCopiedOriginal(false), 2000)
      } else {
        setCopiedTranslated(true)
        setTimeout(() => setCopiedTranslated(false), 2000)
      }
    } catch (e) {
      console.error('Failed to copy text', e)
    }
  }

  const ttsAudioUrl = tts?.filename ? getTTSAudioUrl(baseUrl, tts.filename) : null

  return (
    <section aria-labelledby="results-title">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <h2 id="results-title" className="section-title">
          Speech Translation Output
        </h2>
      </div>

      <div className="results-grid">
        {/* Original Speech Card */}
        <div className="result-card result-card-original">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span style={{ fontFamily: 'var(--font-serif)', fontSize: '18px', fontWeight: 400, color: 'var(--app-ink)' }}>
              Original Transcription
            </span>
            <button
              type="button"
              className="copy-btn"
              onClick={() => copyToClipboard(origText, true)}
              title="Copy transcription"
            >
              {copiedOriginal ? (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--state-success)' }}>
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                  <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                </svg>
              )}
              <span>{copiedOriginal ? 'Copied' : 'Copy'}</span>
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.85rem' }}>
            <span className="lang-pill">
              {LANG_FLAGS[detLang] || '🌐'} {detLang.toUpperCase()} ({LANG_NAMES[detLang] || detLang})
            </span>
            <span style={{ fontSize: '12px', color: 'var(--app-ink-subtle)', fontFamily: 'var(--font-mono)' }}>
              Confidence: {(confidence * 100).toFixed(1)}%
            </span>
          </div>

          <div className="result-box-text">
            {origText}
          </div>
        </div>

        {/* Translated Output Card */}
        <div className={`result-card result-card-translated ${isHindiTarget ? 'is-hindi' : ''}`}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span style={{ fontFamily: 'var(--font-serif)', fontSize: '18px', fontWeight: 400, color: 'var(--app-ink)' }}>
              Translated Output
            </span>
            {transText && (
              <button
                type="button"
                className="copy-btn"
                onClick={() => copyToClipboard(transText, false)}
                title="Copy translated text"
              >
                {copiedTranslated ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--state-success)' }}>
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                    <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                  </svg>
                )}
                <span>{copiedTranslated ? 'Copied' : 'Copy'}</span>
              </button>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.85rem', flexWrap: 'wrap' }}>
            <span className={isHindiTarget ? 'lang-pill lang-pill-hindi' : 'lang-pill'}>
              {LANG_FLAGS[targetLang] || '🌐'} {targetLang.toUpperCase()} ({LANG_NAMES[targetLang] || targetLang})
            </span>
            {isHindiTarget && (
              <span style={{ fontSize: '12px', color: 'var(--app-accent)', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                Devanagari Script
              </span>
            )}
          </div>

          {translation?.error ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'rgba(248, 113, 113, 0.12)',
                border: '1px solid var(--state-danger)',
                borderRadius: '8px',
                padding: '1rem',
                color: 'var(--state-danger)',
                fontSize: '13px',
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>Translation error: {translation.error}</span>
            </div>
          ) : (
            <div className={`result-box-text ${isHindiTarget ? 'result-box-hindi' : ''}`}>
              {transText || 'Translation pending or not available.'}
            </div>
          )}

          {/* Synthesized Audio Player */}
          {ttsAudioUrl && (
            <div
              style={{
                marginTop: '1rem',
                padding: '0.85rem',
                background: 'var(--app-surface-hover)',
                border: '1px solid var(--app-rule)',
                borderRadius: '8px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--app-ink)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--state-success)' }}>
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                  </svg>
                  <span>Synthesized Speech (Piper TTS)</span>
                </span>
                <a
                  href={ttsAudioUrl}
                  download={tts?.filename || 'translation_tts.wav'}
                  className="copy-btn"
                  style={{ textDecoration: 'none' }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  <span>Download WAV</span>
                </a>
              </div>
              <audio controls src={ttsAudioUrl} style={{ width: '100%', height: '36px' }} />
            </div>
          )}

          {tts?.error && (
            <div
              style={{
                marginTop: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'rgba(248, 113, 113, 0.12)',
                border: '1px solid var(--state-danger)',
                borderRadius: '8px',
                padding: '0.85rem',
                color: 'var(--state-danger)',
                fontSize: '13px',
              }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>TTS synthesis error: {tts.error}</span>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
export default ResultsPanel
