"""
test_tts.py
-----------
Verification script for TTSService (Step 6).

Run from the backend directory with:
    poetry run python test_tts.py

Instantiates TTSService directly, synthesizes test phrases in English,
Spanish, and French, saves the resulting normalized audio to test_output/,
and checks files using the standard wave library to verify normalization parameters.
"""
import os
import sys
import traceback
import wave

OUTPUT_DIR = "test_output"

def separator(title: str):
    width = 60
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}")

def pass_mark(label: str):
    print(f"  ✅ PASS: {label}")

def fail_mark(label: str, err: str):
    print(f"  ❌ FAIL: {label}")
    print(f"       Error: {err}")

# Create output folder
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ──────────────────────────────────────────────────────────────
print("Loading TTSService (will download voice models on demand)...")
# ──────────────────────────────────────────────────────────────
try:
    from app.services.tts import TTSService
    service = TTSService()
except Exception as exc:
    print(f"\n❌ FATAL: Could not load TTSService.\n{exc}")
    traceback.print_exc()
    sys.exit(1)

print("TTSService loaded successfully.\n")
all_passed = True

# Helper to verify WAV file properties
def verify_wav_properties(file_path: str) -> bool:
    try:
        with wave.open(file_path, "rb") as w:
            params = w.getparams()
            print(f"  WAV Properties for {os.path.basename(file_path)}:")
            print(f"    Channels    : {params.nchannels} (Expected: 1/Mono)")
            print(f"    Sample Rate : {params.framerate}Hz (Expected: 16000Hz)")
            print(f"    Sample Width: {params.sampwidth} bytes ({params.sampwidth*8} bits, Expected: 2 bytes/16-bit)")
            print(f"    Total Frames: {params.nframes}")
            
            # Check conditions
            assert params.nchannels == 1, "Not mono"
            assert params.framerate == 16000, "Sample rate not 16000Hz"
            assert params.sampwidth == 2, "Not 16-bit depth"
            return True
    except Exception as e:
        print(f"  WAV Validation Error: {e}")
        return False

# ── Test 1: English Synthesis ──────────────────────────────────
separator("Test 1: English TTS Synthesis")
try:
    text = "Hello, this is a test of the Piper Text to Speech service. It is running completely offline."
    out_path = os.path.join(OUTPUT_DIR, "test_en.wav")
    
    # Synthesize
    wav_bytes = service.synthesize_speech(text, "en")
    
    with open(out_path, "wb") as f:
        f.write(wav_bytes)
        
    print(f"  WAV file saved to: {out_path} ({len(wav_bytes)} bytes)")
    
    if verify_wav_properties(out_path):
        pass_mark("English synthesis & formatting")
    else:
        raise AssertionError("Audio formatting check failed")
except Exception as exc:
    fail_mark("English synthesis", str(exc))
    all_passed = False

# ── Test 2: Spanish Synthesis ──────────────────────────────────
separator("Test 2: Spanish TTS Synthesis")
try:
    text = "Hola, esta es una prueba del servicio de síntesis de voz en español."
    out_path = os.path.join(OUTPUT_DIR, "test_es.wav")
    
    wav_bytes = service.synthesize_speech(text, "es")
    
    with open(out_path, "wb") as f:
        f.write(wav_bytes)
        
    print(f"  WAV file saved to: {out_path} ({len(wav_bytes)} bytes)")
    
    if verify_wav_properties(out_path):
        pass_mark("Spanish synthesis & formatting")
    else:
        raise AssertionError("Audio formatting check failed")
except Exception as exc:
    fail_mark("Spanish synthesis", str(exc))
    all_passed = False

# ── Test 3: French Synthesis ──────────────────────────────────
separator("Test 3: French TTS Synthesis")
try:
    text = "Bonjour, ceci est un test de synthèse vocale en français."
    out_path = os.path.join(OUTPUT_DIR, "test_fr.wav")
    
    wav_bytes = service.synthesize_speech(text, "fr")
    
    with open(out_path, "wb") as f:
        f.write(wav_bytes)
        
    print(f"  WAV file saved to: {out_path} ({len(wav_bytes)} bytes)")
    
    if verify_wav_properties(out_path):
        pass_mark("French synthesis & formatting")
    else:
        raise AssertionError("Audio formatting check failed")
except Exception as exc:
    fail_mark("French synthesis", str(exc))
    all_passed = False

# ── Test 4: Error handling - Unsupported language ──────────────
separator("Test 4: Error Handling - Unsupported Language")
try:
    service.synthesize_speech("Hello", "xx")
    fail_mark("Should have raised ValueError for 'xx'", "No exception raised")
    all_passed = False
except ValueError as ve:
    pass_mark(f"ValueError raised as expected: {ve}")
except Exception as exc:
    fail_mark("Expected ValueError, got different exception", str(exc))
    all_passed = False

# ── Test 5: Error handling - Empty text ────────────────────────
separator("Test 5: Error Handling - Empty Text")
try:
    service.synthesize_speech("   ", "en")
    fail_mark("Should have raised ValueError for empty text", "No exception raised")
    all_passed = False
except ValueError as ve:
    pass_mark(f"ValueError raised as expected: {ve}")
except Exception as exc:
    fail_mark("Expected ValueError, got different exception", str(exc))
    all_passed = False

# ── Summary ────────────────────────────────────────────────────
separator("SUMMARY")
if all_passed:
    print("  🎉 All TTS synthesis tests PASSED!")
    print(f"  Check the synthesized WAV files in the '{OUTPUT_DIR}/' folder.")
else:
    print("  ⚠️  Some tests FAILED. Review output above.")
print()
sys.exit(0 if all_passed else 1)
