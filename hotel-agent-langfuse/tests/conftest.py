"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add src to path so hotel_agent is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
