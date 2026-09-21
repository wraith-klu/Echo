import os
import sys
import argparse
from app.services.language_detection import LanguageDetectionService, SUPPORTED_LANGUAGES

def main():
    # Force UTF-8 output for Windows console support
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
        
    parser = argparse.ArgumentParser(description="Test script for Language Detection (LID) Service.")
    parser.add_argument("--test-wav", type=str, help="Optional path to a local WAV file to run full ASR + LID test")
    parser.add_argument("--model", type=str, default="tiny", help="Whisper model size to use if running WAV test")
    args = parser.parse_args()

    print("=" * 60)
    print("   LANGUAGE DETECTION SERVICE - RUNNING CHECKS")
    print("=" * 60)

    # -------------------------------------------------------------
    # Test Suite 1: Direct Service Detection Unit Tests
    # -------------------------------------------------------------
    print("\n--- Test Suite 1: Auto-detection & Fallback Verification ---")
    
    test_cases = [
        # 1. High Whisper confidence (should bypass langdetect)
        {
            "name": "High Whisper confidence (English)",
            "text": "Hello, how are you today?",
            "whisper_lang": "en",
            "whisper_prob": 0.95,
            "expected_source": "whisper",
            "expected_lang": "en"
        },
        # 2. Low Whisper confidence, but clear text (should trigger langdetect fallback)
        {
            "name": "Low Whisper confidence, clear text (Spanish)",
            "text": "Hola, ¿cómo estás hoy? Espero que muy bien.",
            "whisper_lang": "en",  # Misdetected by whisper initially
            "whisper_prob": 0.35,  # Low probability
            "expected_source": "langdetect",
            "expected_lang": "es"
        },
        # 3. Low Whisper confidence, clear text (French)
        {
            "name": "Low Whisper confidence, clear text (French)",
            "text": "Bonjour, comment ça va aujourd'hui?",
            "whisper_lang": "fr",
            "whisper_prob": 0.40,
            "expected_source": "langdetect",
            "expected_lang": "fr"
        },
        # 4. Low Whisper confidence, no text (should return whisper low confidence)
        {
            "name": "Low Whisper confidence, no text (German)",
            "text": "",
            "whisper_lang": "de",
            "whisper_prob": 0.45,
            "expected_source": "fallback",
            "expected_lang": "de"
        },
        # 5. No Whisper input, clear text (should run langdetect)
        {
            "name": "No Whisper input, clear text (Russian)",
            "text": "Здравствуйте, как у вас дела?",
            "whisper_lang": None,
            "whisper_prob": 0.0,
            "expected_source": "langdetect",
            "expected_lang": "ru"
        },
        # 6. Low Whisper confidence, unsupported text (should run langdetect and resolve sv)
        {
            "name": "Unsupported language auto-detected (Swedish)",
            "text": "Hej, hur mår du idag?",
            "whisper_lang": "en",
            "whisper_prob": 0.20,
            "expected_source": "langdetect",
            "expected_lang": "sv"
        }
    ]

    passed_count = 0
    for idx, tc in enumerate(test_cases):
        print(f"\n[{idx+1}] Case: {tc['name']}")
        print(f"    Input text   : \"{tc['text']}\"")
        print(f"    Whisper inputs: lang={tc['whisper_lang']}, prob={tc['whisper_prob']}")
        
        res = LanguageDetectionService.detect_language(
            text=tc["text"],
            whisper_lang=tc["whisper_lang"],
            whisper_prob=tc["whisper_prob"]
        )
        
        is_supported = LanguageDetectionService.is_language_supported(res["detected_language"])
        
        print(f"    Result       : lang='{res['detected_language']}', conf={res['confidence']:.4f}, source='{res['source']}', supported={is_supported}")
        
        # Validate expectations
        if res["source"] == tc["expected_source"] and res["detected_language"] == tc["expected_lang"]:
            print("    [OK] SUCCESS")
            passed_count += 1
        else:
            print(f"    [FAIL] Expected lang='{tc['expected_lang']}' via source='{tc['expected_source']}')")

    print(f"\nSuite 1 Results: {passed_count}/{len(test_cases)} cases passed.")

    # -------------------------------------------------------------
    # Test Suite 2: Validation Check
    # -------------------------------------------------------------
    print("\n--- Test Suite 2: Language Code Support Verification ---")
    test_languages = ["en", "es", "fr", "de", "zh", "ru", "sv", "hi", "ja", "ko", "xx", ""]
    print(f"Supported list: {sorted(list(SUPPORTED_LANGUAGES))}")
    for lang in test_languages:
        ok = LanguageDetectionService.is_language_supported(lang)
        status_str = "SUPPORTED" if ok else "UNSUPPORTED"
        print(f"    Language '{lang}': {status_str}")

    # -------------------------------------------------------------
    # Test Suite 3: End-to-End ASR + LID Integration Check (Optional)
    # -------------------------------------------------------------
    if args.test_wav:
        print("\n--- Test Suite 3: WAV File ASR + LID Execution ---")
        wav_path = os.path.abspath(args.test_wav)
        if not os.path.exists(wav_path):
            print(f"Error: WAV file not found at: {wav_path}")
            sys.exit(1)
            
        print(f"Loading TranscriptionService (model={args.model})...")
        try:
            from app.services.transcription import TranscriptionService
            service = TranscriptionService(model_name=args.model, device="cpu", compute_type="int8")
        except Exception as e:
            print(f"Error importing/loading TranscriptionService: {e}")
            sys.exit(1)
            
        print(f"Transcribing file: {wav_path} ...")
        try:
            # 1. Run transcription
            asr_res = service.transcribe_audio(wav_path)
            print(f"    ASR Text : \"{asr_res['text']}\"")
            print(f"    ASR Lang : '{asr_res['language']}' (probability: {asr_res['language_probability']:.4f})")
            
            # 2. Run Language Detection
            lid_res = LanguageDetectionService.detect_language(
                text=asr_res["text"],
                whisper_lang=asr_res["language"],
                whisper_prob=asr_res["language_probability"]
            )
            is_supported = LanguageDetectionService.is_language_supported(lid_res["detected_language"])
            
            print("\n    LID Results:")
            print(f"      Detected Language : '{lid_res['detected_language']}'")
            print(f"      Confidence        : {lid_res['confidence']:.4f}")
            print(f"      Source            : '{lid_res['source']}'")
            print(f"      Supported         : {is_supported}")
            
        except Exception as e:
            print(f"ASR + LID integration failed: {e}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("   TEST RUN COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
