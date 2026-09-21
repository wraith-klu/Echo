import React from 'react'
import { LANG_FLAGS, LANG_NAMES } from '../utils/constants.js'
import { getTTSAudioUrl } from '../utils/api.js'
import { Copy, Check, Volume2, Download, AlertTriangle } from 'lucide-react'

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
        <h2 id="results-title" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)' }}>
          📊 Speech Translation Output
        </h2>
      </div>

      <div className="results-grid">
        {/* Original Speech Card */}
        <div className="result-card result-card-original">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
            <span style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              📝 Original Speech
            </span>
            <button
              type="button"
              className="copy-btn"
              onClick={() => copyToClipboard(origText, true)}
              title="Copy transcription"
            >
              {copiedOriginal ? <Check size={13} color="#34d399" /> : <Copy size={13} />}
              <span>{copiedOriginal ? 'Copied' : 'Copy'}</span>
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.8rem' }}>
            <span className="lang-pill">
              {LANG_FLAGS[detLang] || '🌐'} {detLang.toUpperCase()} ({LANG_NAMES[detLang] || detLang})
            </span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Whisper confidence: <strong style={{ color: '#0284c7' }}>{(confidence * 100).toFixed(1)}%</strong>
            </span>
          </div>

          <div className="result-box-text">
            {origText}
          </div>
        </div>

        {/* Translated Output Card */}
        <div className={`result-card result-card-translated ${isHindiTarget ? 'is-hindi' : ''}`}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
            <span style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              🌐 Translated Output
            </span>
            {transText && (
              <button
                type="button"
                className="copy-btn"
                onClick={() => copyToClipboard(transText, false)}
                title="Copy translated text"
              >
                {copiedTranslated ? <Check size={13} color="#34d399" /> : <Copy size={13} />}
                <span>{copiedTranslated ? 'Copied' : 'Copy'}</span>
              </button>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.8rem', flexWrap: 'wrap' }}>
            <span className={isHindiTarget ? 'lang-pill lang-pill-hindi' : 'lang-pill'}>
              {LANG_FLAGS[targetLang] || '🌐'} {targetLang.toUpperCase()} ({LANG_NAMES[targetLang] || targetLang})
            </span>
            {isHindiTarget && (
              <span style={{ fontSize: '0.75rem', color: '#fbbf24', fontWeight: 600 }}>
                🇮🇳 Devanagari Script
              </span>
            )}
          </div>

          {translation?.error ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'rgba(244, 63, 94, 0.12)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                borderRadius: '12px',
                padding: '1rem',
                color: '#fb7185',
                fontSize: '0.85rem',
              }}
            >
              <AlertTriangle size={18} />
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
                background: 'rgba(255, 255, 255, 0.60)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Volume2 size={16} color="#10b981" />
                  <span>Synthesized Speech (Piper TTS)</span>
                </span>
                <a
                  href={ttsAudioUrl}
                  download={tts?.filename || 'translation_tts.wav'}
                  className="copy-btn"
                  style={{ textDecoration: 'none' }}
                >
                  <Download size={13} />
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
                background: 'rgba(244, 63, 94, 0.12)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                borderRadius: '12px',
                padding: '0.85rem',
                color: '#fb7185',
                fontSize: '0.82rem',
              }}
            >
              <AlertTriangle size={16} />
              <span>TTS synthesis error: {tts.error}</span>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
