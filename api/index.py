import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "Backend"
DATA_PARSING_DIR = ROOT_DIR / "Data-Parsing"

for dir_path in [ROOT_DIR, BACKEND_DIR, DATA_PARSING_DIR]:
    if str(dir_path) not in sys.path:
        sys.path.insert(0, str(dir_path))

from Backend.main import app
