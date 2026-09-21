/**
 * Client-side Web Audio API Recorder & 16kHz 16-bit Mono WAV Encoder.
 * Produces standard PCM WAV files that FastAPI + Soundfile + Whisper accept directly.
 */

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i))
  }
}

/**
 * Encodes Float32 mono audio samples into a 16-bit PCM WAV Blob at the target sample rate.
 */
export function encodeWAV(samples, sampleRate = 16000) {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)

  // 1. RIFF chunk descriptor
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true) // file length - 8
  writeString(view, 8, 'WAVE')

  // 2. "fmt " sub-chunk
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true) // SubChunk1Size (16 for PCM)
  view.setUint16(20, 1, true)  // AudioFormat (1 for PCM)
  view.setUint16(22, 1, true)  // NumChannels (1 = mono)
  view.setUint32(24, sampleRate, true) // SampleRate
  view.setUint32(28, sampleRate * 2, true) // ByteRate (SampleRate * NumChannels * BitsPerSample/8)
  view.setUint16(32, 2, true)  // BlockAlign (NumChannels * BitsPerSample/8)
  view.setUint16(34, 16, true) // BitsPerSample (16-bit)

  // 3. "data" sub-chunk
  writeString(view, 36, 'data')
  view.setUint32(40, samples.length * 2, true) // SubChunk2Size

  // 4. Write 16-bit PCM samples with clipping protection
  let offset = 44
  for (let i = 0; i < samples.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

/**
 * Resamples Float32 audio samples from sourceRate to targetRate using linear interpolation.
 */
export function resampleAudio(audioData, sourceRate, targetRate) {
  if (sourceRate === targetRate) {
    return audioData
  }

  const ratio = sourceRate / targetRate
  const newLength = Math.round(audioData.length / ratio)
  const result = new Float32Array(newLength)

  for (let i = 0; i < newLength; i++) {
    const originalPos = i * ratio
    const leftIndex = Math.floor(originalPos)
    const rightIndex = Math.min(leftIndex + 1, audioData.length - 1)
    const interpolationFactor = originalPos - leftIndex

    result[i] =
      audioData[leftIndex] * (1 - interpolationFactor) +
      audioData[rightIndex] * interpolationFactor
  }

  return result
}

/**
 * Starts recording from the microphone and streams audio data into an internal buffer.
 * Also runs an AnalyserNode to provide continuous volume / waveform levels to the UI.
 * @returns {Promise<{stop: () => Promise<{blob: Blob, duration: number}>, cancel: () => void}>}
 */
export async function startAudioRecording(onVolumeChange) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  })

  // Create AudioContext
  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  const audioCtx = new AudioContextClass()
  const source = audioCtx.createMediaStreamSource(stream)

  // Analyser node for UI visualization
  const analyser = audioCtx.createAnalyser()
  analyser.fftSize = 256
  source.connect(analyser)

  // ScriptProcessor for raw sample capture (universally supported)
  const bufferSize = 4096
  const scriptProcessor = audioCtx.createScriptProcessor(bufferSize, 1, 1)
  source.connect(scriptProcessor)
  scriptProcessor.connect(audioCtx.destination)

  const rawChunks = []
  let totalLength = 0
  const startTime = Date.now()

  // Visualization loop
  const pcmData = new Uint8Array(analyser.frequencyBinCount)
  let animationFrameId = null

  const monitorVolume = () => {
    analyser.getByteFrequencyData(pcmData)
    let sum = 0
    for (let i = 0; i < pcmData.length; i++) {
      sum += pcmData[i]
    }
    const avg = sum / pcmData.length
    const normalized = Math.min(1, avg / 128)
    if (onVolumeChange) {
      onVolumeChange(normalized)
    }
    animationFrameId = requestAnimationFrame(monitorVolume)
  }
  animationFrameId = requestAnimationFrame(monitorVolume)

  scriptProcessor.onaudioprocess = (e) => {
    const input = e.inputBuffer.getChannelData(0)
    // Make a copy
    const chunk = new Float32Array(input.length)
    chunk.set(input)
    rawChunks.push(chunk)
    totalLength += chunk.length
  }

  const cleanup = () => {
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId)
    }
    scriptProcessor.disconnect()
    source.disconnect()
    stream.getTracks().forEach((t) => t.stop())
    if (audioCtx.state !== 'closed') {
      audioCtx.close()
    }
  }

  return {
    stop: async () => {
      const duration = (Date.now() - startTime) / 1000
      cleanup()

      // Merge recorded chunks into a single Float32Array
      const merged = new Float32Array(totalLength)
      let offset = 0
      for (const chunk of rawChunks) {
        merged.set(chunk, offset)
        offset += chunk.length
      }

      // Resample to 16,000 Hz if necessary
      const resampled = resampleAudio(merged, audioCtx.sampleRate, 16000)

      // Encode to 16-bit mono PCM WAV
      const blob = encodeWAV(resampled, 16000)
      return { blob, duration }
    },
    cancel: () => {
      cleanup()
    },
  }
}
