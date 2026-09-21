import os
import sys
import time

os.environ["HF_HUB_VERBOSITY"] = "debug"

log_path = r"P:\CapsTron Project - 1\backend\download_log.txt"

def log(msg):
    print(msg, flush=True)
    with open(log_path, "a") as f:
        f.write(msg + "\n")

log(f"=== NLLB Download Script starting at {time.strftime('%H:%M:%S')} ===")

try:
    from huggingface_hub import hf_hub_download
    log("huggingface_hub imported OK")
except ImportError as e:
    log(f"IMPORT ERROR: {e}")
    sys.exit(1)

try:
    log("Starting hf_hub_download for pytorch_model.bin ...")
    path = hf_hub_download(
        repo_id="facebook/nllb-200-distilled-600M",
        filename="pytorch_model.bin",
        local_files_only=False,
    )
    size_mb = os.path.getsize(path) / 1e6
    log(f"SUCCESS: Downloaded to {path}")
    log(f"Size: {size_mb:.1f} MB")
except Exception as e:
    log(f"ERROR ({type(e).__name__}): {e}")
    import traceback
    log(traceback.format_exc())
    sys.exit(1)

log("=== Done ===")
