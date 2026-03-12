#!/usr/bin/env python3
"""Run basedpyright for pre-commit hook."""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Run basedpyright using uv."""
    backend_dir = Path(__file__).parent.parent.parent / "backend"
    os.chdir(backend_dir)

    try:
        result = subprocess.run(
            ["uv", "run", "basedpyright"],
            check=False,
        )
        sys.exit(result.returncode)
    except FileNotFoundError:
        result = subprocess.run(
            [sys.executable, "-m", "basedpyright"],
            check=False,
        )
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
