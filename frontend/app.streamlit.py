# pyrefly: ignore [missing-import]
import streamlit as st
import requests  # type: ignore
import os
import time

# # ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CapsTron — Speech Translation Portal",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

  /* ── Root variables ─────────────────────────────────────────────────── */
  :root {
    --bg-base:      #f7f9fc;
    --bg-panel:     rgba(255, 255, 255, 0.75);
    --bg-card:      rgba(255, 255, 255, 0.70);
    --accent-blue:  #0284c7;
    --accent-indigo:#4f46e5;
    --accent-teal:  #0d9488;
    --accent-violet:#7c3aed;
    --accent-hindi: #d97706;
    --text-primary: #0f172a;
    --text-muted:   #475569;
    --border:       rgba(99, 102, 241, 0.12);
    --success:      #059669;
    --error:        #e11d48;
    --glow:         0 4px 20px rgba(99, 102, 241, 0.08);
  }

  /* ── App-wide font & background ────────────────────────────────────── */
  html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif !important;
    color: #0f172a !important;
  }
  .stApp {
    background:
      radial-gradient(circle at 0% 0%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
      radial-gradient(circle at 100% 0%, rgba(168, 85, 247, 0.06) 0%, transparent 40%),
      radial-gradient(circle at 50% 100%, rgba(14, 165, 233, 0.05) 0%, transparent 50%),
      #f7f9fc !important;
  }

  /* ── Sidebar ─────────────────────────────────────────────────────────── */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f4f6fa 100%) !important;
    border-right: 1px solid rgba(99, 102, 241, 0.12) !important;
    box-shadow: 2px 0 16px rgba(0, 0, 0, 0.03) !important;
  }
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 {
    color: #0f172a !important;
  }

  /* ── Hero header ────────────────────────────────────────────────────── */
  .hero-header {
    text-align: center;
    padding: 2rem 0 0.5rem 0;
  }
  .hero-title {
    font-size: 3.2rem;
    font-weight: 900;
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #0891b2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.03em;
    margin: 0;
  }
  .hero-subtitle {
    color: #475569;
    font-size: 1.1rem;
    margin-top: 0.5rem;
    font-weight: 300;
    letter-spacing: 0.01em;
  }
  .badge-row {
    display: flex;
    justify-content: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin: 1rem 0 0;
  }
  .badge {
    background: rgba(255, 255, 255, 0.90);
    border: 1px solid rgba(99, 102, 241, 0.18);
    border-radius: 999px;
    padding: 0.25rem 1rem;
    font-size: 0.78rem;
    font-weight: 600;
    color: #4f46e5;
    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.05);
  }

  /* ── Cards ───────────────────────────────────────────────────────────── */
  .glass-card {
    background: rgba(255, 255, 255, 0.75);
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 18px;
    padding: 1.5rem 1.8rem;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px 0 rgba(99, 102, 241, 0.04), 0 2px 4px rgba(0, 0, 0, 0.01);
    margin-bottom: 1.2rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .glass-card:hover {
    border-color: rgba(99, 102, 241, 0.22);
    box-shadow: 0 10px 40px 0 rgba(99, 102, 241, 0.08), 0 2px 8px rgba(99, 102, 241, 0.02);
  }
  .glass-card-accent-blue  { border-left: 4px solid #0284c7; }
  .glass-card-accent-green { border-left: 4px solid #059669; }
  .glass-card-accent-hindi { border-left: 4px solid #d97706; }

  /* ── Section labels ─────────────────────────────────────────────────── */
  .section-label {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 0.6rem;
  }

  /* ── Result text boxes ──────────────────────────────────────────────── */
  .result-text {
    font-size: 1.15rem;
    font-weight: 400;
    line-height: 1.7;
    color: #1e293b !important;
    background: rgba(255, 255, 255, 0.40);
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    border: 1px solid rgba(99, 102, 241, 0.10);
    min-height: 100px;
    box-shadow: inset 0 1px 3px rgba(99, 102, 241, 0.03);
  }
  .result-text-hindi {
    font-size: 1.3rem;
    font-family: 'Noto Sans Devanagari', 'Outfit', sans-serif;
    color: #c2410c !important;
  }
  .result-text-translated {
    font-size: 1.15rem;
    color: #4338ca !important;
  }

  /* ── Metric chips ───────────────────────────────────────────────────── */
  .metric-chip {
    background: rgba(255, 255, 255, 0.70);
    border: 1px solid rgba(99, 102, 241, 0.10);
    border-radius: 16px;
    padding: 1.1rem 1rem;
    text-align: center;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.03), inset 0 1px 1px rgba(255, 255, 255, 0.9);
    transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  }
  .metric-chip:hover {
    transform: translateY(-4px);
    border-color: rgba(99, 102, 241, 0.20);
    box-shadow: 0 10px 24px rgba(99, 102, 241, 0.08);
  }
  .metric-chip .chip-label {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #64748b;
  }
  .metric-chip .chip-value {
    font-size: 1.75rem;
    font-weight: 800;
    margin-top: 0.3rem;
  }
  .chip-asr   .chip-value { color: #2563eb; }
  .chip-lid   .chip-value { color: #0d9488; }
  .chip-mt    .chip-value { color: #7c3aed; }
  .chip-tts   .chip-value { color: #059669; }
  .chip-total .chip-value { color: #d97706; }

  /* ── Buttons ─────────────────────────────────────────────────────────── */
  .stButton > button {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
    padding: 0.6rem 1.8rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.25) !important;
  }
  .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 22px rgba(99, 102, 241, 0.40) !important;
  }

  /* ── Selectbox ───────────────────────────────────────────────────────── */
  div[data-testid="stSelectbox"] > div > div {
    background: #ffffff !important;
    border: 1px solid rgba(99, 102, 241, 0.18) !important;
    border-radius: 12px !important;
    color: #0f172a !important;
    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.04) !important;
  }

  /* ── Spinner ─────────────────────────────────────────────────────────── */
  .stSpinner > div > div { border-top-color: #4f46e5 !important; }

  /* ── Alerts ──────────────────────────────────────────────────────────── */
  .stSuccess, .stInfo, .stError, .stWarning {
    background-color: rgba(255, 255, 255, 0.60) !important;
    border: 1px solid rgba(99, 102, 241, 0.12) !important;
    color: #0f172a !important;
    border-radius: 12px !important;
  }

  /* ── Language pills ──────────────────────────────────────────────────── */
  .lang-pill {
    display: inline-block;
    background: rgba(99, 102, 241, 0.06);
    border: 1px solid rgba(99, 102, 241, 0.15);
    border-radius: 999px;
    padding: 0.22rem 0.85rem;
    font-size: 0.80rem;
    font-weight: 600;
    color: #4f46e5;
    margin-right: 0.5rem;
  }
  .lang-pill-hindi {
    background: rgba(217, 119, 6, 0.06);
    border-color: rgba(217, 119, 6, 0.18);
    color: #d97706;
  }

  /* ── History expanders ───────────────────────────────────────────────── */
  details summary { color: #0f172a !important; font-weight: 600; }

  /* ── Divider ──────────────────────────────────────────────────────────── */
  hr { border-color: rgba(99, 102, 241, 0.12) !important; margin: 1.4rem 0 !important; }

  /* ── Audio input widget ──────────────────────────────────────────────── */
  [data-testid="stAudioInput"] {
    background: #ffffff !important;
    border: 1px solid rgba(99, 102, 241, 0.15) !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.04) !important;
  }
</style>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SUPPORTED LANGUAGES  (code → display label and NLLB code hints)
# ─────────────────────────────────────────────────────────────────────────────
SUPPORTED_LANGS = {
    "Auto-Detect": "auto",
    "English":     "en",
    "Hindi 🇮🇳":   "hi",          # ← Added
    "Spanish":     "es",
    "French":      "fr",
    "German":      "de",
    "Italian":     "it",
    "Portuguese":  "pt",
    "Chinese":     "zh",
    "Japanese":    "ja",
    "Korean":      "ko",
    "Russian":     "ru",
    "Arabic":      "ar",
}

# Flag emoji to make the UI warmer
LANG_FLAGS = {
    "en": "🇬🇧", "hi": "🇮🇳", "es": "🇪🇸", "fr": "🇫🇷",
    "de": "🇩🇪", "it": "🇮🇹", "pt": "🇧🇷", "zh": "🇨🇳",
    "ja": "🇯🇵", "ko": "🇰🇷", "ru": "🇷🇺", "ar": "🇸🇦",
}


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "processing" not in st.session_state:
    st.session_state.processing = False


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌐 CapsTron")
    st.markdown("<p style='color:#64748b;font-size:0.82rem;margin-top:-0.6rem'>Real-time speech translation</p>",
                unsafe_allow_html=True)
    st.markdown("---")

    # Environment switcher
    st.markdown("#### ⚙️ Backend Environment")
    ENV_MODES = {
        "🖥️  Localhost (Dev)":       "http://localhost:8000",
        "☁️  Oracle Cloud (Prod)": "https://api.yourdomain.com",
    }
    env_override = os.environ.get("CAPSTRON_BACKEND_URL")
    if env_override:
        ENV_MODES["🔗  Custom (ENV)"] = env_override

    selected_env = st.selectbox("Backend Environment", options=list(ENV_MODES.keys()), label_visibility="collapsed")
    base_url = ENV_MODES[selected_env]
    st.caption(f"`{base_url}`")

    st.markdown("---")

    # Ping
    st.markdown("#### 📡 Connectivity")
    if st.button("Ping Backend", use_container_width=True):
        with st.spinner("Checking…"):
            try:
                t0 = time.perf_counter()
                r = requests.get(f"{base_url}/health", timeout=5)
                ping_ms = (time.perf_counter() - t0) * 1000
                if r.status_code == 200 and r.json().get("status") == "ok":
                    st.success(f"✅ Online  ·  {ping_ms:.0f} ms")
                    status_r = requests.get(f"{base_url}/api/v1/status", timeout=5)
                    if status_r.status_code == 200:
                        svcs = status_r.json().get("services", {})
                        for svc, state in svcs.items():
                            icon = "🟢" if state == "ready" else "🔴"
                            st.markdown(f"{icon} `{svc}` — {state}")
                else:
                    st.error(f"HTTP {r.status_code}")
            except Exception as exc:
                st.error(f"Unreachable: {exc}")

    st.markdown("---")

    # Quick stats from session state
    st.markdown("#### 📊 Session Stats")
    if st.session_state.last_result:
        lat = st.session_state.last_result.get("latencies", {})
        st.metric("Last Total Latency", f"{lat.get('total_sec', 0):.2f}s")
        st.metric("ASR",  f"{lat.get('asr_sec', 0):.2f}s")
        st.metric("MT",   f"{lat.get('translation_sec', 0):.2f}s")
        st.metric("TTS",  f"{lat.get('tts_sec', 0):.2f}s")
    else:
        st.caption("No translation run yet.")

    st.markdown("---")
    st.caption("CapsTron v1.0 · ESP32 + FastAPI + NLLB-200")


# ─────────────────────────────────────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
  <p class="hero-title">🌐 CapsTron Translation Portal</p>
  <p class="hero-subtitle">End-to-end multilingual speech translation · Whisper · NLLB-200 · Piper TTS</p>
  <div class="badge-row">
    <span class="badge">🎙️ Real-time ASR</span>
    <span class="badge">🌍 100+ Languages</span>
    <span class="badge">🔊 Neural TTS</span>
    <span class="badge">🇮🇳 Hindi</span>
    <span class="badge">⚡ Low-latency</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE SELECTION PANEL
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">🔧 Translation Configuration</p>', unsafe_allow_html=True)

lc1, lc2, lc3 = st.columns([5, 1, 5])

with lc1:
    st.markdown('<div class="glass-card glass-card-accent-blue">', unsafe_allow_html=True)
    st.markdown("##### 🎤 Source Language")
    src_label = st.selectbox(
        "source",
        options=list(SUPPORTED_LANGS.keys()),
        index=0,
        label_visibility="collapsed",
        key="src_lang_sel",
    )
    src_lang = SUPPORTED_LANGS[src_label]
    if src_lang != "auto":
        flag = LANG_FLAGS.get(src_lang, "")
        st.markdown(f'<span class="lang-pill">{flag} {src_label}</span> detected by Whisper ASR',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="lang-pill">🤖 Auto-detect via Whisper</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with lc2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;color:#6366f1;margin:0'>⇄</h2>", unsafe_allow_html=True)

with lc3:
    target_options = [l for l in SUPPORTED_LANGS.keys() if l != "Auto-Detect"]
    default_tgt_idx = target_options.index("Hindi 🇮🇳") if "Hindi 🇮🇳" in target_options else 0

    is_hindi_target = False

    st.markdown('<div class="glass-card glass-card-accent-hindi">', unsafe_allow_html=True)
    st.markdown("##### 🎯 Target Language")
    tgt_label = st.selectbox(
        "target",
        options=target_options,
        index=default_tgt_idx,
        label_visibility="collapsed",
        key="tgt_lang_sel",
    )
    tgt_lang = SUPPORTED_LANGS[tgt_label]
    flag = LANG_FLAGS.get(tgt_lang, "")
    pill_class = "lang-pill lang-pill-hindi" if tgt_lang == "hi" else "lang-pill"
    st.markdown(f'<span class="{pill_class}">{flag} {tgt_label}</span> output via NLLB-200 + TTS',
                unsafe_allow_html=True)
    if tgt_lang == "hi":
        st.markdown('<span style="font-size:0.78rem;color:#fdba74">🇮🇳 Devanagari script output enabled</span>',
                    unsafe_allow_html=True)
    is_hindi_target = tgt_lang == "hi"
    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# AUDIO RECORDER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="section-label">🎙️ Audio Input</p>', unsafe_allow_html=True)

rec_col, hint_col = st.columns([3, 2])
with rec_col:
    audio_file = st.audio_input("Record your voice (click mic button, speak, click stop):",
                                key="audio_recorder")
with hint_col:
    st.markdown("""
    <div class="glass-card" style="margin-top:1.8rem">
      <p style="font-size:0.82rem;color:#94a3b8;margin:0">
        <b style="color:#e2e8f0">💡 Tips</b><br><br>
        • Click the 🎙️ button to start recording<br>
        • Speak clearly in your source language<br>
        • Click the ⏹ button to finish<br>
        • Processing starts automatically<br><br>
        <span style="color:#6366f1;font-weight:600">Supported:</span>
        English · Hindi · Spanish · French · German · Chinese · Japanese · Korean · Russian · Arabic
      </p>
    </div>
    """, unsafe_allow_html=True)

audio_bytes = None
if audio_file is not None:
    audio_bytes = audio_file.read()


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE EXECUTION
# ─────────────────────────────────────────────────────────────────────────────
if audio_bytes:
    st.markdown("---")
    st.markdown('<p class="section-label">▶️ Pipeline Processing</p>', unsafe_allow_html=True)

    # Playback of recorded audio
    with st.expander("🔈 Recorded Audio Preview", expanded=False):
        st.audio(audio_bytes, format="audio/wav")

    with st.spinner("🔄  Running Whisper → LID → NLLB-200 → Piper TTS …"):
        try:
            files = {"file": ("recording.wav", audio_bytes, "audio/wav")}
            data  = {"target_language": tgt_lang}
            if src_lang != "auto":
                data["source_language"] = src_lang

            t0 = time.perf_counter()
            response = requests.post(
                f"{base_url}/api/v1/audio/transcribe",
                files=files,
                data=data,
                timeout=180,
            )
            wall_time = time.perf_counter() - t0

            if response.status_code == 200:
                result = response.json()
                st.session_state.last_result = result

                if result.get("status") == "error":
                    st.error(f"❌ Pipeline error: {result.get('message', 'Unknown')}")
                    if "error" in result:
                        st.code(result["error"])
                else:
                    transcription = result.get("transcription", {})
                    translation   = result.get("translation", {})
                    tts           = result.get("tts", {})
                    latencies     = result.get("latencies", {})
                    det_lang      = transcription.get("language_detection", {}).get("detected_language", "?")
                    confidence    = transcription.get("language_detection", {}).get("confidence", 0.0)

                    # ── Success banner ────────────────────────────────────
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,rgba(16,185,129,0.15),rgba(6,182,212,0.10));
                                border:1px solid rgba(16,185,129,0.3);border-radius:12px;
                                padding:0.8rem 1.2rem;display:flex;align-items:center;gap:0.8rem;margin-bottom:1rem">
                      <span style="font-size:1.5rem">✅</span>
                      <div>
                        <span style="font-weight:700;color:#10b981">Translation Complete</span>
                        <span style="color:#64748b;font-size:0.85rem;margin-left:0.6rem">in {wall_time:.2f}s wall-clock</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Results side-by-side ──────────────────────────────
                    res1, res2 = st.columns(2)

                    with res1:
                        orig_text = transcription.get("text", "No speech detected.")
                        flag_src  = LANG_FLAGS.get(det_lang, "🌐")
                        st.markdown(f"""
                        <div class="glass-card glass-card-accent-blue">
                          <div style="font-size:1.05rem;font-weight:700;margin-bottom:0.6rem">
                            📝 Original Speech
                          </div>
                          <div style="margin-bottom:0.7rem">
                            <span class="lang-pill">{flag_src} {det_lang.upper()}</span>
                            <span style="color:#64748b;font-size:0.8rem">confidence {confidence:.1%}</span>
                          </div>
                          <div class="result-text">{orig_text}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with res2:
                        hindi_class = " result-text-hindi" if is_hindi_target else " result-text-translated"
                        card_acc    = "glass-card-accent-hindi" if is_hindi_target else "glass-card-accent-green"
                        flag_tgt    = LANG_FLAGS.get(tgt_lang, "")
                        pill_cls    = "lang-pill lang-pill-hindi" if is_hindi_target else "lang-pill"
                        hindi_note  = "<div style='font-size:0.76rem;color:#fdba74;margin-top:0.4rem'>🇮🇳 Devanagari script</div>" if is_hindi_target else ""

                        if translation and "translated_text" in translation:
                            trans_text  = translation["translated_text"]
                            tts_section = ""
                            if tts and tts.get("filename"):
                                tts_url = f"{base_url}/api/v1/audio/tts/{tts['filename']}"
                                tts_section = '<div style="margin-top:0.8rem;font-size:0.82rem;font-weight:600;color:#64748b">🔊 Synthesized Audio</div>'
                            st.markdown(f"""
                            <div class="glass-card {card_acc}">
                              <div style="font-size:1.05rem;font-weight:700;margin-bottom:0.6rem">
                                🌐 Translated Output
                              </div>
                              <div style="margin-bottom:0.7rem">
                                <span class="{pill_cls}">{flag_tgt} {tgt_label}</span>
                                {hindi_note}
                              </div>
                              <div class="result-text{hindi_class}">{trans_text}</div>
                              {tts_section}
                            </div>
                            """, unsafe_allow_html=True)
                            if tts and tts.get("filename"):
                                tts_url = f"{base_url}/api/v1/audio/tts/{tts['filename']}"
                                try:
                                    tts_resp = requests.get(tts_url, timeout=15)
                                    if tts_resp.status_code == 200:
                                        st.markdown(
                                            "<p style='font-size:0.82rem;font-weight:600;"
                                            "color:#64748b;margin:0.4rem 0 0.2rem'>🔊 Synthesized Audio</p>",
                                            unsafe_allow_html=True,
                                        )
                                        st.audio(tts_resp.content, format="audio/wav")
                                    else:
                                        st.warning(f"TTS audio fetch failed (HTTP {tts_resp.status_code})")
                                except Exception as tts_fetch_err:
                                    st.warning(f"Could not load TTS audio: {tts_fetch_err}")
                        elif translation and "error" in translation:
                            st.markdown(f"""
                            <div class="glass-card {card_acc}">
                              <div style="font-size:1.05rem;font-weight:700;margin-bottom:0.6rem">
                                🌐 Translated Output
                              </div>
                              <span class="{pill_cls}">{flag_tgt} {tgt_label}</span>
                            </div>
                            """, unsafe_allow_html=True)
                            st.warning(f"⚠️ Translation failed: {translation['error']}")
                        else:
                            st.markdown(f"""
                            <div class="glass-card {card_acc}">
                              <div style="font-size:1.05rem;font-weight:700;margin-bottom:0.6rem">
                                🌐 Translated Output
                              </div>
                              <span class="{pill_cls}">{flag_tgt} {tgt_label}</span>
                            </div>
                            """, unsafe_allow_html=True)
                            st.info(f"Translation not returned. Backend response: `{translation}`")

                    # ── Latency metrics row ───────────────────────────────
                    st.markdown("---")
                    st.markdown('<p class="section-label">⏱️ Latency Breakdown</p>', unsafe_allow_html=True)

                    m1, m2, m3, m4, m5 = st.columns(5)
                    chip_data = [
                        (m1, "chip-asr",   "ASR",         latencies.get("asr_sec", 0),         "🎙️"),
                        (m2, "chip-lid",   "Language ID", latencies.get("lid_sec", 0),         "🔍"),
                        (m3, "chip-mt",    "NLLB-200",    latencies.get("translation_sec", 0), "🌍"),
                        (m4, "chip-tts",   "Piper TTS",   latencies.get("tts_sec", 0),         "🔊"),
                        (m5, "chip-total", "Total",       latencies.get("total_sec", 0),       "⚡"),
                    ]
                    for col, cls, label, val, icon in chip_data:
                        with col:
                            st.markdown(f"""
                            <div class="metric-chip {cls}">
                              <div class="chip-label">{icon} {label}</div>
                              <div class="chip-value">{val:.2f}s</div>
                            </div>
                            """, unsafe_allow_html=True)

                    # ── Raw JSON expander ─────────────────────────────────
                    with st.expander("🔬 Raw API Response (debug)", expanded=False):
                        st.json(result)

            else:
                st.error(f"❌ Server error HTTP {response.status_code}")
                st.code(response.text)

        except requests.exceptions.ConnectionError:
            st.error("🔌 Cannot reach backend. Check the sidebar environment URL and make sure the server is running.")
        except Exception as exc:
            st.error(f"💥 Unexpected error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION HISTORY
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="section-label">📜 Translation History</p>', unsafe_allow_html=True)

hist_c1, hist_c2 = st.columns([1, 6])
with hist_c1:
    load_hist = st.button("🔄 Load History", use_container_width=True)

if load_hist:
    with st.spinner("Fetching from database…"):
        try:
            hr = requests.get(f"{base_url}/api/v1/history?limit=10", timeout=5)
            if hr.status_code == 200:
                history = hr.json().get("items", [])
                if not history:
                    st.info("📭 No recorded sessions yet. Run a translation to populate history.")
                else:
                    for item in history:
                        sid   = item.get("id", "")[:8]
                        ts    = item.get("created_at", "")[:19].replace("T", " ")
                        slang = item.get("source_lang", "?")
                        tlang = item.get("target_lang", "?")
                        sflag = LANG_FLAGS.get(slang, "🌐")
                        tflag = LANG_FLAGS.get(tlang, "🌐")
                        with st.expander(f"{sflag} → {tflag}  ·  ID #{sid}  ·  {ts}"):
                            hc1, hc2 = st.columns(2)
                            with hc1:
                                st.markdown(f"**Original ({slang}):**")
                                st.info(item.get("original_text", "—"))
                            with hc2:
                                st.markdown(f"**Translated ({tlang}):**")
                                st.success(item.get("translated_text", "—"))
                            lat = item.get("latencies", {}).get("total_sec", 0)
                            st.caption(f"Status: `{item.get('status')}` · Total: `{lat:.2f}s`")
            else:
                st.error(f"History endpoint returned HTTP {hr.status_code}")
        except Exception as exc:
            st.error(f"Could not load history: {exc}")
