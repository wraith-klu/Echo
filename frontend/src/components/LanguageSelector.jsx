import React from 'react'
import { SOURCE_LANGUAGES, TARGET_LANGUAGES } from '../utils/constants.js'
import { ArrowLeftRight, Sparkles } from 'lucide-react'

export const LanguageSelector = ({
  sourceLang,
  setSourceLang,
  targetLang,
  setTargetLang,
}) => {
  const isHindiTarget = targetLang === 'hi'
  const currentSource = SOURCE_LANGUAGES.find((l) => l.code === sourceLang)
  const currentTarget = TARGET_LANGUAGES.find((l) => l.code === targetLang)

  const handleSwap = () => {
    if (sourceLang === 'auto') {
      setSourceLang(targetLang)
      setTargetLang(targetLang === 'en' ? 'hi' : 'en')
    } else {
      const prevSource = sourceLang
      setSourceLang(targetLang)
      setTargetLang(prevSource)
    }
  }

  const applyPair = (src, tgt) => {
    setSourceLang(src)
    setTargetLang(tgt)
  }

  return (
    <section aria-labelledby="lang-config-title">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
        <h2 id="lang-config-title" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)' }}>
          🔧 Translation Configuration
        </h2>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          <button type="button" className="badge-tag" style={{ cursor: 'pointer', border: 'none' }} onClick={() => applyPair('auto', 'hi')}>
            Auto → 🇮🇳 Hindi
          </button>
          <button type="button" className="badge-tag" style={{ cursor: 'pointer', border: 'none' }} onClick={() => applyPair('en', 'hi')}>
            🇬🇧 English → 🇮🇳 Hindi
          </button>
          <button type="button" className="badge-tag" style={{ cursor: 'pointer', border: 'none' }} onClick={() => applyPair('hi', 'en')}>
            🇮🇳 Hindi → 🇬🇧 English
          </button>
          <button type="button" className="badge-tag" style={{ cursor: 'pointer', border: 'none' }} onClick={() => applyPair('auto', 'es')}>
            Auto → 🇪🇸 Spanish
          </button>
        </div>
      </div>

      <div className="lang-selector-grid">
        {/* Source Language Card */}
        <div className="lang-card lang-card-source">
          <div className="lang-header">
            <span className="lang-label">🎤 Source Language</span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Input Audio</span>
          </div>
          <select
            id="source-language-select"
            className="input-select"
            value={sourceLang}
            onChange={(e) => setSourceLang(e.target.value)}
          >
            {SOURCE_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.flag} {lang.name}
              </option>
            ))}
          </select>
          <div>
            <span className="lang-pill">
              {currentSource?.flag} {currentSource?.name}
              {sourceLang === 'auto' ? ' (Whisper Auto-Detection)' : ' (Pre-Selected)'}
            </span>
          </div>
        </div>

        {/* Swap Button */}
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <button
            id="swap-languages-btn"
            type="button"
            className="swap-button"
            onClick={handleSwap}
            title="Swap source and target languages"
            aria-label="Swap Languages"
          >
            <ArrowLeftRight size={18} />
          </button>
        </div>

        {/* Target Language Card */}
        <div className={`lang-card lang-card-target ${isHindiTarget ? 'is-hindi' : ''}`}>
          <div className="lang-header">
            <span className="lang-label">🎯 Target Language</span>
            <span style={{ fontSize: '0.78rem', color: isHindiTarget ? '#fbbf24' : 'var(--text-muted)' }}>
              {isHindiTarget ? '✨ High Priority Target' : 'NLLB-200 + TTS'}
            </span>
          </div>
          <select
            id="target-language-select"
            className="input-select"
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
          >
            {TARGET_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.flag} {lang.name}
              </option>
            ))}
          </select>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span className={isHindiTarget ? 'lang-pill lang-pill-hindi' : 'lang-pill'}>
              {currentTarget?.flag} {currentTarget?.name}
            </span>
            {isHindiTarget && (
              <span style={{ fontSize: '0.76rem', color: '#fbbf24', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                <Sparkles size={13} /> Devanagari script enabled
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
