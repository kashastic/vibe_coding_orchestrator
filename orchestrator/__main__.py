"""Entry point for `python -m orchestrator`."""
from __future__ import annotations

import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set manually

from orchestrator.orchestrator import main

sys.exit(main())
