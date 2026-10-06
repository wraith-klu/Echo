import React from 'react'
import { SOURCE_LANGUAGES, TARGET_LANGUAGES } from '../utils/constants.js'

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h2 id="lang-config-title" className="section-title">
          Configuration &amp; Pairings
        </h2>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          <button type="button" className="badge-tag" style={{ cursor: 'pointer' }} onClick={() => applyPair('auto', 'hi')}>
            Auto → 🇮🇳 Hindi
          </button>
          <button type="button" className="badge-tag" style={{ cursor: 'pointer' }} onClick={() => applyPair('en', 'hi')}>
            🇬🇧 English → 🇮🇳 Hindi
          </button>
          <button type="button" className="badge-tag" style={{ cursor: 'pointer' }} onClick={() => applyPair('hi', 'en')}>
            🇮🇳 Hindi → 🇬🇧 English
          </button>
          <button type="button" className="badge-tag" style={{ cursor: 'pointer' }} onClick={() => applyPair('auto', 'es')}>
            Auto → 🇪🇸 Spanish
          </button>
        </div>
      </div>

      <div className="lang-selector-grid">
        {/* Source Language Card */}
        <div className="lang-card lang-card-source">
          <div className="lang-header">
            <span className="lang-label">Source Language</span>
            <span style={{ fontSize: '12px', color: 'var(--app-ink-subtle)', fontFamily: 'var(--font-sans)' }}>Input Audio</span>
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
              {sourceLang === 'auto' ? ' (Whisper Auto-Detect)' : ' (Pre-Selected)'}
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
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m16 3 4 4-4 4" />
              <path d="M20 7H4" />
              <path d="m8 21-4-4 4-4" />
              <path d="M4 17h16" />
            </svg>
          </button>
        </div>

        {/* Target Language Card */}
        <div className={`lang-card lang-card-target ${isHindiTarget ? 'is-hindi' : ''}`}>
          <div className="lang-header">
            <span className="lang-label">Target Language</span>
            <span style={{ fontSize: '12px', color: isHindiTarget ? 'var(--app-accent)' : 'var(--app-ink-subtle)', fontFamily: 'var(--font-sans)' }}>
              {isHindiTarget ? 'Primary Model Pair' : 'NLLB-200 + TTS'}
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
              <span style={{ fontSize: '12px', color: 'var(--app-accent)', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z" />
                </svg>
                Devanagari enabled
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
export default LanguageSelector
