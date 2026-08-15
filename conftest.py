"""Put the repo root on sys.path so tests can `import config` / `from src import ...`
the same way notebooks and scripts do."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
