import sys
from pathlib import Path

# Ensure the 'backend' directory is in sys.path so 'app.*' imports resolve cleanly
_backend_dir = Path(__file__).resolve().parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.main import app  # type: ignore # noqa: F401
