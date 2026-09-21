"""
Quick standalone ASR verification script.
Downloads the tiny Whisper model, creates a test WAV, and runs transcription.
"""
import sys
import time
import numpy as np
import soundfile as sf
import os

print("=" * 55)
print("  Step 3 - ASR Integration Verification")
print("=" * 55)

# Step 1: Import faster-whisper
print("\n[1/4] Importing faster-whisper...")
try:
    from faster_whisper import WhisperModel
    import faster_whisper
    print(f"      faster-whisper v{faster_whisper.__version__} imported OK")
except ImportError as e:
    print(f"      FAIL: {e}")
    sys.exit(1)

# Step 2: Load the tiny model (smallest, fastest to download ~39MB)
print("\n[2/4] Loading WhisperModel (tiny, cpu, int8)...")
start = time.time()
try:
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    load_time = time.time() - start
    print(f"      Model loaded in {load_time:.2f}s")
except Exception as e:
    print(f"      FAIL: {e}")
    sys.exit(1)

# Step 3: Create a minimal test WAV (2s sine wave at 440Hz simulating speech-like audio)
print("\n[3/4] Generating test audio file...")
sample_rate = 16000
duration = 2
t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 440Hz tone
test_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "audio_uploads", "verify_test.wav")
)
os.makedirs(os.path.dirname(test_path), exist_ok=True)
sf.write(test_path, audio, sample_rate)
print(f"      WAV written: {test_path}")

# Step 4: Run transcription
print("\n[4/4] Running transcription...")
start = time.time()
try:
    segments, info = model.transcribe(test_path, beam_size=5)
    segs = list(segments)
    elapsed = time.time() - start
    text = " ".join(s.text for s in segs).strip()
    print(f"      Latency       : {elapsed:.3f}s")
    print(f"      Language      : {info.language} (prob={info.language_probability:.4f})")
    print(f"      Transcription : \"{text}\"")
    print(f"      Segments      : {len(segs)}")
except Exception as e:
    print(f"      FAIL: {e}")
    sys.exit(1)

print("\n" + "=" * 55)
print("  ALL CHECKS PASSED - ASR Service is working!")
print("=" * 55)
