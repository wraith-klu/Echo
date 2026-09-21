import sys
from pathlib import Path

# Ensure the backend directory is in sys.path
_current_dir = Path(__file__).resolve().parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from app.main import app  # type: ignore # noqa: F401
