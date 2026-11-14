"""Convenience launcher: ``python main.py``.

Equivalent to ``python -m salahbot``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from salahbot.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
