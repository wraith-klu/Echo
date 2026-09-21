"""
test_translation.py
-------------------
Standalone test script for the TranslationService (Step 5).

Run from the backend directory with:
    poetry run python test_translation.py

This does NOT require the FastAPI server to be running.
It directly instantiates TranslationService and validates:
  1. NLLB language code mapping
  2. English → Spanish translation
  3. English → French translation
  4. Same-language no-op (en → en)
  5. Unsupported language raises ValueError
  6. Empty text raises ValueError
"""
import sys
import traceback

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

# ──────────────────────────────────────────────────────────────
print("Loading TranslationService (this may download the NLLB model on first run)...")
# ──────────────────────────────────────────────────────────────
try:
    from app.services.translation import TranslationService, NLLB_LANG_MAP
    svc = TranslationService()
except Exception as exc:
    print(f"\n❌ FATAL: Could not load TranslationService.\n{exc}")
    traceback.print_exc()
    sys.exit(1)

print("TranslationService loaded successfully.\n")
all_passed = True

# ── Test 1: Language code mapping ──────────────────────────────
separator("Test 1: NLLB Language Code Mapping")
test_cases = {
    "en": "eng_Latn",
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "zh": "zho_Hans",
}
for iso, expected_nllb in test_cases.items():
    got = TranslationService.get_nllb_code(iso)
    if got == expected_nllb:
        pass_mark(f"'{iso}' → '{got}'")
    else:
        fail_mark(f"'{iso}' should be '{expected_nllb}', got '{got}'", "Mapping mismatch")
        all_passed = False

# ── Test 2: English → Spanish ──────────────────────────────────
separator("Test 2: English → Spanish Translation")
try:
    result = svc.translate_text(
        text="Hello, how are you?",
        source_lang="en",
        target_lang="es"
    )
    assert result["translated_text"], "translated_text is empty"
    assert result["source_lang"] == "en"
    assert result["target_lang"] == "es"
    assert result["latency_sec"] >= 0
    print(f"  Input:   'Hello, how are you?'")
    print(f"  Output:  '{result['translated_text']}'")
    print(f"  Latency: {result['latency_sec']}s")
    pass_mark("English → Spanish")
except Exception as exc:
    fail_mark("English → Spanish", str(exc))
    all_passed = False

# ── Test 3: English → French ──────────────────────────────────
separator("Test 3: English → French Translation")
try:
    result = svc.translate_text(
        text="Good morning! The weather is nice today.",
        source_lang="en",
        target_lang="fr"
    )
    print(f"  Input:   'Good morning! The weather is nice today.'")
    print(f"  Output:  '{result['translated_text']}'")
    print(f"  Latency: {result['latency_sec']}s")
    pass_mark("English → French")
except Exception as exc:
    fail_mark("English → French", str(exc))
    all_passed = False

# ── Test 4: Spanish → English ──────────────────────────────────
separator("Test 4: Spanish → English Translation")
try:
    result = svc.translate_text(
        text="Me llamo Juan. ¿Cómo estás?",
        source_lang="es",
        target_lang="en"
    )
    print(f"  Input:   'Me llamo Juan. ¿Cómo estás?'")
    print(f"  Output:  '{result['translated_text']}'")
    print(f"  Latency: {result['latency_sec']}s")
    pass_mark("Spanish → English")
except Exception as exc:
    fail_mark("Spanish → English", str(exc))
    all_passed = False

# ── Test 5: Same-language no-op ────────────────────────────────
separator("Test 5: Same-Language No-Op (en → en)")
try:
    result = svc.translate_text(
        text="This should not change at all.",
        source_lang="en",
        target_lang="en"
    )
    assert result["translated_text"] == "This should not change at all."
    assert result["latency_sec"] == 0.0
    pass_mark(f"Same-language no-op. Returned original text instantly.")
except AssertionError as ae:
    fail_mark("Same-language no-op", str(ae))
    all_passed = False
except Exception as exc:
    fail_mark("Same-language no-op", str(exc))
    all_passed = False

# ── Test 6: Unsupported source language raises ValueError ──────
separator("Test 6: Unsupported Source Language → ValueError")
try:
    svc.translate_text(text="Test", source_lang="xx", target_lang="en")
    fail_mark("Should have raised ValueError for 'xx'", "No exception raised")
    all_passed = False
except ValueError as ve:
    pass_mark(f"ValueError raised as expected: {ve}")
except Exception as exc:
    fail_mark("Expected ValueError, got different exception", str(exc))
    all_passed = False

# ── Test 7: Unsupported target language raises ValueError ──────
separator("Test 7: Unsupported Target Language → ValueError")
try:
    svc.translate_text(text="Test", source_lang="en", target_lang="zz")
    fail_mark("Should have raised ValueError for 'zz'", "No exception raised")
    all_passed = False
except ValueError as ve:
    pass_mark(f"ValueError raised as expected: {ve}")
except Exception as exc:
    fail_mark("Expected ValueError, got different exception", str(exc))
    all_passed = False

# ── Test 8: Empty text raises ValueError ──────────────────────
separator("Test 8: Empty Text → ValueError")
try:
    svc.translate_text(text="   ", source_lang="en", target_lang="es")
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
    print("  🎉 All translation tests PASSED!")
else:
    print("  ⚠️  Some tests FAILED. Review output above.")
print()
sys.exit(0 if all_passed else 1)
