"""Example adapter entrypoint for the demo workflow.

Why this file exists:
It gives the example config its own adapter path while still reusing the root
sample adapter implementation so the demo stays consistent.
"""

from __future__ import annotations

from pathlib import Path
import runpy


if __name__ == "__main__":
    adapter_path = Path(__file__).resolve().parents[3] / "scripts" / "agentci_adapter.py"
    runpy.run_path(str(adapter_path), run_name="__main__")
