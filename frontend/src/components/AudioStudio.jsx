import React, { useState, useRef, useEffect, useMemo } from 'react'
import { startAudioRecording } from '../utils/wavEncoder.js'
import { Mic, Square, Upload, CheckCircle2, AlertCircle, Sparkles, Volume2 } from 'lucide-react'

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

  // Derive audio preview URL cleanly
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
        <h2 id="audio-input-title" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)' }}>
          🎙️ Audio Input Studio
        </h2>
        <div style={{ display: 'flex', gap: '0.35rem' }}>
          <button
            type="button"
            className={`btn btn-secondary ${activeMode === 'mic' ? 'active' : ''}`}
            style={{ padding: '0.3rem 0.8rem', fontSize: '0.78rem' }}
            onClick={() => setActiveMode('mic')}
          >
            <Mic size={14} /> Record Voice
          </button>
          <button
            type="button"
            className={`btn btn-secondary ${activeMode === 'upload' ? 'active' : ''}`}
            style={{ padding: '0.3rem 0.8rem', fontSize: '0.78rem' }}
            onClick={() => setActiveMode('upload')}
          >
            <Upload size={14} /> Upload File
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
                  {isRecording ? <Square size={34} /> : <Mic size={38} />}
                </button>
              </div>

              {isRecording ? (
                <>
                  <div className="timer-tag">{formatTimer(recordingSeconds)}</div>
                  <div style={{ fontSize: '0.85rem', color: '#fb7185', fontWeight: 600 }}>
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
                    style={{ marginTop: '0.5rem', padding: '0.4rem 0.9rem', fontSize: '0.8rem' }}
                    onClick={cancelRecording}
                  >
                    Cancel Recording
                  </button>
                </>
              ) : (
                <>
                  <div style={{ fontWeight: 600, fontSize: '1.05rem', color: 'var(--text-primary)' }}>
                    Click microphone to start recording
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
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
                    background: 'rgba(244, 63, 94, 0.12)',
                    border: '1px solid rgba(244, 63, 94, 0.3)',
                    borderRadius: '10px',
                    padding: '0.6rem 0.9rem',
                    marginTop: '0.9rem',
                    color: '#fb7185',
                    fontSize: '0.82rem',
                  }}
                >
                  <AlertCircle size={16} />
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
              <Upload size={32} color="#4f46e5" style={{ margin: '0 auto 0.5rem' }} />
              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                Drop an audio file here or click to browse
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Accepts WAV, MP3, M4A, OGG, FLAC (16kHz mono recommended)
              </div>
            </div>
          )}

          {/* Audio Preview and Execute Trigger */}
          {hasAudioReady && audioUrl && (
            <div className="audio-preview-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Volume2 size={15} color="#0284c7" /> Audio Preview ({audioDuration.toFixed(1)}s)
                </span>
                <span className="status-badge status-ready" style={{ fontSize: '0.7rem' }}>
                  Ready to translate
                </span>
              </div>

              <audio controls src={audioUrl} style={{ width: '100%', marginTop: '0.4rem' }} />

              <button
                id="run-translation-btn"
                type="button"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '0.5rem', padding: '0.85rem' }}
                onClick={onExecuteTranslate}
                disabled={isProcessing}
              >
                <Sparkles size={18} />
                <span>{isProcessing ? 'Translating Speech…' : 'Run Speech Translation Pipeline'}</span>
              </button>
            </div>
          )}
        </div>

        {/* Hints and Instructions Box */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <CheckCircle2 size={16} color="#34d399" />
            <span>Best Practices</span>
          </div>

          <ul style={{ listStyle: 'none', fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            <li>• Speak clearly at a normal conversational pace</li>
            <li>• Keep recording within 2 to 15 seconds for optimal latency</li>
            <li>• Whisper ASR will automatically detect language if set to Auto</li>
            <li>• For Hindi target, NLLB-200 produces authentic Devanagari script output</li>
            <li>• Synthesized audio will be generated via Piper neural TTS</li>
          </ul>

          <div style={{ marginTop: '1rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border-subtle)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            ⚡ Pipeline: VAD → Whisper ASR → Language ID → NLLB-200 → Piper TTS
          </div>
        </div>
      </div>
    </section>
  )
}
