// Type stubs — kept for IDE compatibility.
// The project runs as plain JSX; these types are not imported at runtime.

export interface LanguageOption {
  code: string
  name: string
  flag: string
  devanagari?: boolean
}

export interface LanguageDetection {
  detected_language: string
  confidence: number
}

export interface TranscriptionData {
  text: string
  language_detection?: LanguageDetection
}

export interface TranslationData {
  translated_text?: string
  source_language?: string
  target_language?: string
  error?: string
}

export interface TTSData {
  filename?: string
  duration_sec?: number
}

export interface Latencies {
  asr_sec?: number
  lid_sec?: number
  translation_sec?: number
  tts_sec?: number
  total_sec?: number
}

export interface PipelineResult {
  status: string
  filename?: string
  duration?: number
  message?: string
  transcription?: TranscriptionData
  translation?: TranslationData
  tts?: TTSData
  latencies?: Latencies
  error?: string
  raw?: Record<string, unknown>
}

export interface HistoryItem {
  id: string
  session_id?: string
  device_id: string
  created_at: string
  source_lang: string
  target_lang: string
  original_text: string
  translated_text: string
  status: string
  latencies?: Latencies
}

export interface DeviceItem {
  id: string
  device_id: string
  name?: string
  description?: string
  registered_at?: string
  last_seen_at?: string
  is_active: boolean
  meta?: Record<string, unknown>
}

export interface ServicesStatus {
  ingestion?: string
  asr?: string
  translation?: string
  tts?: string
}

export type ActiveTab = 'translate' | 'history' | 'devices'
