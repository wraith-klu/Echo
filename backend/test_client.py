import os
import sys
import time
import argparse
import asyncio
import numpy as np
import soundfile as sf
import websockets
import json

# Setup argument parser
parser = argparse.ArgumentParser(description="Simulate ESP32 audio streaming client over WebSockets end-to-end.")
parser.add_argument("--file", type=str, required=True, help="Path to local .wav file to stream")
parser.add_argument("--url", type=str, default="ws://localhost:8000/api/v1/ws/audio", help="WebSocket URL of the ingestion endpoint")
parser.add_argument("--device-id", type=str, default="simulated_esp32_client", help="Device ID query parameter")
parser.add_argument("--chunk-size", type=int, default=1024, help="Number of audio samples per chunk (1 sample = 2 bytes in 16-bit PCM)")
parser.add_argument("--no-realtime", action="store_true", help="Send chunks as fast as possible instead of simulating real-time recording")
parser.add_argument("--source-lang", type=str, default=None, help="Optional source language override (e.g. 'en', 'es')")
parser.add_argument("--target-lang", type=str, default=None, help="Optional target language override (e.g. 'es', 'fr')")
parser.add_argument("--save-audio", type=str, default=None, help="Local file path to save received TTS translated audio WAV")

# Track binary audio state
audio_follows = False
audio_size_expected = 0
audio_file_path = None

async def receive_messages(websocket, save_path):
    """
    Listens for responses from the server.
    Handles text (JSON) and binary (WAV audio) frames sequentially.
    """
    global audio_follows, audio_size_expected
    
    try:
        async for message in websocket:
            if isinstance(message, str):
                # Handle text JSON message
                try:
                    response = json.loads(message)
                    print(f"\n[Server Response JSON] {json.dumps(response, indent=2)}")
                    
                    # Check if audio frame follows
                    if response.get("audio_follows"):
                        audio_follows = True
                        audio_size_expected = response.get("audio_size_bytes", 0)
                        print(f"[Client] Expecting binary audio payload next: {audio_size_expected} bytes.")
                    else:
                        # If pipeline finished processing and no audio follows, we can exit
                        status = response.get("status")
                        if status in ["success", "partial_success", "error"]:
                            print("[Client] Pipeline finished without audio. Exiting.")
                            return
                except json.JSONDecodeError:
                    print(f"\n[Server Raw Text Response] {message}")
                    
            elif isinstance(message, bytes):
                # Handle binary WAV audio frame
                if audio_follows:
                    print(f"\n[Client] Received binary audio frame of {len(message)} bytes.")
                    if save_path:
                        parent_dir = os.path.dirname(os.path.abspath(save_path))
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)
                        with open(save_path, "wb") as f:
                            f.write(message)
                        print(f"✅ [Client] Saved translated TTS audio to: {save_path}")
                    else:
                        print("⚠️ [Client] Received audio bytes but no --save-audio path was provided to save it.")
                    audio_follows = False
                    audio_size_expected = 0
                    # Exit once we've successfully received and saved the audio response
                    return
                else:
                    print(f"\n[Client] Warning: Received unexpected binary message of {len(message)} bytes (audio_follows was False).")
                    
    except websockets.exceptions.ConnectionClosed:
        print("\n[Client] Connection closed by server.")
    except Exception as e:
        print(f"\n[Client] Error receiving message: {e}")

async def send_audio(websocket, file_path, chunk_samples, simulate_realtime):
    """
    Reads the audio file, formats it to 16kHz mono 16-bit PCM, and streams it.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return

    print(f"[Client] Loading and processing file '{file_path}'...")
    # Load audio file using soundfile
    data, samplerate = sf.read(file_path)

    # 1. Convert to mono if stereo
    if len(data.shape) > 1 and data.shape[1] > 1:
        print("[Client] Mixing stereo to mono...")
        data = np.mean(data, axis=1)

    # 2. Resample to 16000Hz if needed
    if samplerate != 16000:
        print(f"[Client] Resampling from {samplerate}Hz to 16000Hz...")
        duration = len(data) / samplerate
        target_length = int(duration * 16000)
        data = np.interp(
            np.linspace(0, len(data), target_length, endpoint=False),
            np.arange(len(data)),
            data
        )
        samplerate = 16000

    # 3. Convert floats to signed 16-bit PCM bytes
    pcm_data = (data * 32767.0).astype(np.int16)
    raw_bytes = pcm_data.tobytes()

    total_bytes = len(raw_bytes)
    chunk_bytes_size = chunk_samples * 2  # 2 bytes per sample in 16-bit
    total_chunks = (total_bytes + chunk_bytes_size - 1) // chunk_bytes_size

    chunk_duration_sec = chunk_samples / 16000
    print(f"[Client] Ready to stream {total_bytes} bytes (~{len(data)/16000:.2f}s of audio).")
    print(f"[Client] Stream configuration: {samplerate}Hz, mono, 16-bit PCM")
    print(f"[Client] Chunks: {total_chunks} of size {chunk_bytes_size} bytes ({chunk_duration_sec*1000:.1f}ms each)")
    print(f"[Client] Realtime Simulation: {'ON' if simulate_realtime else 'OFF'}")

    await asyncio.sleep(1.0)  # Wait for receive loop to start

    bytes_sent = 0
    start_time = time.time()

    for i in range(total_chunks):
        start_chunk_offset = i * chunk_bytes_size
        end_chunk_offset = min((i + 1) * chunk_bytes_size, total_bytes)
        chunk = raw_bytes[start_chunk_offset:end_chunk_offset]

        # Send raw PCM bytes
        await websocket.send(chunk)
        bytes_sent += len(chunk)

        # Print quick progress
        progress_pct = (bytes_sent / total_bytes) * 100
        print(f"\rStreaming: {progress_pct:.1f}% ({bytes_sent}/{total_bytes} bytes)", end="", flush=True)

        if simulate_realtime:
            # Sleep to match audio duration of the chunk
            await asyncio.sleep(chunk_duration_sec)

    end_time = time.time()
    print(f"\n[Client] Finished streaming in {end_time - start_time:.2f}s.")
    
    # Send end of speech command to trigger processing instantly (rather than waiting for VAD silence)
    print("[Client] Sending 'end_of_speech' command to trigger processing...")
    await websocket.send(json.dumps({"command": "end_of_speech"}))
    
    # Wait for processing and response
    print("[Client] Waiting 6 seconds for server to compile the pipeline outputs...")
    await asyncio.sleep(6.0)

async def main():
    args = parser.parse_args()
    
    # Construct URL with query parameters
    params = [f"device_id={args.device_id}"]
    if args.source_lang:
        params.append(f"source_language={args.source_lang}")
    if args.target_lang:
        params.append(f"target_language={args.target_lang}")
        
    ws_url = f"{args.url}?{'&'.join(params)}"
    print(f"[Client] Connecting to WebSocket endpoint: {ws_url} ...")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("[Client] Connected successfully!")
            
            # Start message receiver task concurrently
            receiver_task = asyncio.create_task(receive_messages(websocket, args.save_audio))
            
            # Run audio sender
            await send_audio(websocket, args.file, args.chunk_size, not args.no_realtime)
            
            # Wait for receiver task to finish processing and receiving responses
            print("[Client] Waiting for server response...")
            try:
                # Wait up to 15 seconds for responses (allows time for server inference)
                await asyncio.wait_for(receiver_task, timeout=15.0)
            except asyncio.TimeoutError:
                print("[Client] Timeout waiting for server response. Closing connection.")
                receiver_task.cancel()
            except asyncio.CancelledError:
                pass
            
    except Exception as e:
        print(f"[Client] Failed to complete connection or stream: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
