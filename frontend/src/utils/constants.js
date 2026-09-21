export const SOURCE_LANGUAGES = [
  { code: 'auto', name: 'Auto-Detect', flag: '🤖' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'hi', name: 'Hindi 🇮🇳', flag: '🇮🇳', devanagari: true },
  { code: 'es', name: 'Spanish', flag: '🇪🇸' },
  { code: 'fr', name: 'French', flag: '🇫🇷' },
  { code: 'de', name: 'German', flag: '🇩🇪' },
  { code: 'it', name: 'Italian', flag: '🇮🇹' },
  { code: 'pt', name: 'Portuguese', flag: '🇧🇷' },
  { code: 'zh', name: 'Chinese', flag: '🇨🇳' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵' },
  { code: 'ko', name: 'Korean', flag: '🇰🇷' },
  { code: 'ru', name: 'Russian', flag: '🇷🇺' },
  { code: 'ar', name: 'Arabic', flag: '🇸🇦' },
]

export const TARGET_LANGUAGES = SOURCE_LANGUAGES.filter((l) => l.code !== 'auto')

export const LANG_FLAGS = {
  auto: '🤖',
  en: '🇬🇧',
  hi: '🇮🇳',
  es: '🇪🇸',
  fr: '🇫🇷',
  de: '🇩🇪',
  it: '🇮🇹',
  pt: '🇧🇷',
  zh: '🇨🇳',
  ja: '🇯🇵',
  ko: '🇰🇷',
  ru: '🇷🇺',
  ar: '🇸🇦',
}

export const LANG_NAMES = {
  auto: 'Auto-Detect',
  en: 'English',
  hi: 'Hindi',
  es: 'Spanish',
  fr: 'French',
  de: 'German',
  it: 'Italian',
  pt: 'Portuguese',
  zh: 'Chinese',
  ja: 'Japanese',
  ko: 'Korean',
  ru: 'Russian',
  ar: 'Arabic',
}

export const ENV_PRESETS = [
  { id: 'dev', label: 'Localhost (Dev)', url: 'http://localhost:8000' },
  { id: 'render', label: 'Render Cloud (Prod)', url: import.meta.env.VITE_BACKEND_URL || 'https://echo-speech-backend.onrender.com' },
  { id: 'proxy', label: 'Vite Proxy (Local)', url: '' },
  { id: 'custom_prod', label: 'Custom Domain', url: 'https://api.yourdomain.com' },
]
