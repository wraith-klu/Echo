import os
import sys
import argparse
from app.services.transcription import TranscriptionService

def main():
    parser = argparse.ArgumentParser(description="Test script for speech-to-text (ASR) transcription.")
    parser.add_argument("--file", type=str, required=True, help="Path to local WAV file to transcribe")
    parser.add_argument("--model", type=str, default="base", help="Whisper model size to use (tiny, base, small, medium)")
    args = parser.parse_args()

    file_path = os.path.abspath(args.file)
    if not os.path.exists(file_path):
        print(f"Error: Audio file not found at: {file_path}")
        sys.exit(1)

    print(f"Initializing TranscriptionService with model '{args.model}'...")
    try:
        # Load the transcription service (force CPU and int8 for optimization)
        service = TranscriptionService(model_name=args.model, device="cpu", compute_type="int8")
    except Exception as e:
        print(f"Error initializing TranscriptionService: {e}")
        sys.exit(1)

    print(f"\nTranscribing file: {file_path} ...")
    try:
        result = service.transcribe_audio(file_path)
        print("\n" + "="*50)
        print(" TRANSCRIPTION RESULT ")
        print("="*50)
        print(f"Detected Language : {result['language']} (Probability: {result['language_probability']:.4f})")
        print(f"Latency           : {result['latency_sec']:.3f} seconds")
        print(f"Full Text         :\n{result['text']}\n")
        
        print("Segments Details  :")
        for idx, seg in enumerate(result['segments']):
            print(f"  [{idx+1}] {seg['start']}s - {seg['end']}s | Confidence: {seg['confidence']} | {seg['text']}")
        print("="*50)
        
    except Exception as e:
        print(f"Transcription failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
