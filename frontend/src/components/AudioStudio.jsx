import React, { useState, useRef, useEffect, useMemo } from 'react'
import { startAudioRecording } from '../utils/wavEncoder.js'

export const AudioStudio = ({
  onAudioReady,
  onExecuteTranslate,
  isProcessing,
  hasAudioReady,
  audioBlob,
  audioDuration,
}) => {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [volumeLevel, setVolumeLevel] = useState(0)
  const [activeMode, setActiveMode] = useState('mic')
  const [recordError, setRecordError] = useState(null)

  const recorderRef = useRef(null)
  const timerRef = useRef(null)
  const fileInputRef = useRef(null)

  const audioUrl = useMemo(() => {
    return audioBlob ? URL.createObjectURL(audioBlob) : null
  }, [audioBlob])

  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl)
      }
    }
  }, [audioUrl])

  const startRecording = async () => {
    setRecordError(null)
    try {
      setRecordingSeconds(0)
      const recorder = await startAudioRecording((vol) => {
        setVolumeLevel(vol)
      })
      recorderRef.current = recorder
      setIsRecording(true)

      timerRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => prev + 1)
      }, 1000)
    } catch (err) {
      console.error('Microphone error:', err)
      setRecordError(
        err instanceof Error ? err.message : 'Microphone access was denied or is unavailable.'
      )
    }
  }

  const stopRecording = async () => {
    if (!recorderRef.current) return
    if (timerRef.current !== null) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }

    try {
      const { blob, duration } = await recorderRef.current.stop()
      setIsRecording(false)
      recorderRef.current = null
      setVolumeLevel(0)
      onAudioReady(blob, duration)
    } catch (err) {
      console.error('Stop recording failed:', err)
      setRecordError('Failed to capture audio from microphone.')
      setIsRecording(false)
    }
  }

  const cancelRecording = () => {
    if (recorderRef.current) {
      recorderRef.current.cancel()
      recorderRef.current = null
    }
    if (timerRef.current !== null) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    setIsRecording(false)
    setRecordingSeconds(0)
    setVolumeLevel(0)
  }

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const tempUrl = URL.createObjectURL(file)
    const tempAudio = new Audio(tempUrl)
    tempAudio.onloadedmetadata = () => {
      const duration = tempAudio.duration || 0
      URL.revokeObjectURL(tempUrl)
      onAudioReady(file, duration)
    }
    tempAudio.onerror = () => {
      URL.revokeObjectURL(tempUrl)
      onAudioReady(file, 0)
    }
  }

  const formatTimer = (totalSeconds) => {
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <section aria-labelledby="audio-input-title">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h2 id="audio-input-title" className="section-title">
          Audio Input Studio
        </h2>
        <div style={{ display: 'flex', gap: '0.35rem' }}>
          <button
            type="button"
            className={`btn btn-secondary ${activeMode === 'mic' ? 'active' : ''}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
            onClick={() => setActiveMode('mic')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
            Record Voice
          </button>
          <button
            type="button"
            className={`btn btn-secondary ${activeMode === 'upload' ? 'active' : ''}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
            onClick={() => setActiveMode('upload')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Upload File
          </button>
        </div>
      </div>

      <div className="studio-container">
        {/* Main Recorder / Upload Box */}
        <div className="glass-card recorder-box">
          {activeMode === 'mic' ? (
            <>
              <div className="record-btn-wrapper">
                {isRecording && <div className="pulse-ring" />}
                <button
                  id="record-mic-btn"
                  type="button"
                  className={`record-btn ${isRecording ? 'recording' : ''}`}
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={isProcessing}
                  title={isRecording ? 'Click to stop recording' : 'Click to start recording'}
                >
                  {isRecording ? (
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
                      <rect width="18" height="18" x="3" y="3" rx="2" />
                    </svg>
                  ) : (
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                      <line x1="12" y1="19" x2="12" y2="22" />
                    </svg>
                  )}
                </button>
              </div>

              {isRecording ? (
                <>
                  <div className="timer-tag">{formatTimer(recordingSeconds)}</div>
                  <div style={{ fontSize: '13px', color: 'var(--state-danger)', fontWeight: 500 }}>
                    Recording in progress… Speak now
                  </div>

                  {/* Real-time Dynamic Waveform visualizer */}
                  <div className="waveform-bars">
                    {Array.from({ length: 24 }).map((_, idx) => {
                      const dynamicHeight = Math.max(
                        6,
                        Math.sin(idx * 0.5 + recordingSeconds * 4) * 20 * volumeLevel +
                          volumeLevel * 42
                      )
                      return (
                        <div
                          key={idx}
                          className="wave-bar active"
                          style={{ height: `${dynamicHeight}px` }}
                        />
                      )
                    })}
                  </div>

                  <button
                    type="button"
                    className="btn btn-outline-danger"
                    style={{ marginTop: '0.5rem', padding: '6px 14px', fontSize: '12px' }}
                    onClick={cancelRecording}
                  >
                    Cancel Recording
                  </button>
                </>
              ) : (
                <>
                  <div style={{ fontFamily: 'var(--font-serif)', fontSize: '20px', color: 'var(--app-ink)', fontWeight: 400 }}>
                    Click microphone to start recording
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--app-ink-subtle)', marginTop: '0.25rem' }}>
                    Web Audio API auto-encodes to 16kHz mono 16-bit PCM WAV
                  </div>
                </>
              )}

              {recordError && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    background: 'rgba(248, 113, 113, 0.12)',
                    border: '1px solid var(--state-danger)',
                    borderRadius: '7px',
                    padding: '8px 12px',
                    marginTop: '0.9rem',
                    color: 'var(--state-danger)',
                    fontSize: '13px',
                  }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>{recordError}</span>
                </div>
              )}
            </>
          ) : (
            /* Upload Mode */
            <div
              className="dropzone"
              style={{ width: '100%' }}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*,.wav,.mp3,.m4a,.ogg,.flac"
                style={{ display: 'none' }}
                onChange={handleFileUpload}
              />
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 0.5rem', color: 'var(--app-accent)' }}>
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <div style={{ fontWeight: 500, fontSize: '14px', color: 'var(--app-ink)' }}>
                Drop an audio file here or click to browse
              </div>
              <div style={{ fontSize: '12px', color: 'var(--app-ink-subtle)', marginTop: '0.25rem' }}>
                Accepts WAV, MP3, M4A, OGG, FLAC (16kHz mono recommended)
              </div>
            </div>
          )}

          {/* Audio Preview and Execute Trigger */}
          {hasAudioReady && audioUrl && (
            <div className="audio-preview-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--app-ink)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--app-accent)' }}>
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                  </svg>
                  Audio Ready ({audioDuration.toFixed(1)}s)
                </span>
                <span className="status-badge status-ready">
                  Ready to translate
                </span>
              </div>

              <audio controls src={audioUrl} style={{ width: '100%', marginTop: '0.4rem' }} />

              <button
                id="run-translation-btn"
                type="button"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '0.5rem', padding: '12px' }}
                onClick={onExecuteTranslate}
                disabled={isProcessing}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z" />
                </svg>
                <span>{isProcessing ? 'Translating Speech…' : 'Run Speech Translation Pipeline'}</span>
              </button>
            </div>
          )}
        </div>

        {/* Hints and Instructions Box */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--app-ink)', marginBottom: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--state-success)' }}>
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <span>Best Practices</span>
          </div>

          <ul style={{ listStyle: 'none', fontSize: '13px', color: 'var(--app-ink-muted)', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            <li>• Speak clearly at a natural, conversational pace</li>
            <li>• Keep recording within 2 to 15 seconds for optimal latency</li>
            <li>• Whisper ASR will automatically detect language if set to Auto</li>
            <li>• For Hindi target, NLLB-200 produces authentic Devanagari script output</li>
            <li>• Synthesized audio will be generated via Piper neural TTS</li>
          </ul>

          <div style={{ marginTop: '1rem', paddingTop: '0.85rem', borderTop: '1px solid var(--app-rule)', fontSize: '12px', color: 'var(--app-ink-subtle)', fontFamily: 'var(--font-mono)' }}>
            Pipeline: VAD → Whisper ASR → Language ID → NLLB-200 → Piper TTS
          </div>
        </div>
      </div>
    </section>
  )
}
export default AudioStudio
