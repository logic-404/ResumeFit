import os
import sys
from pathlib import Path

# Make `app` importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Provide minimum env vars so app.config.settings can load during tests
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test"
)
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
