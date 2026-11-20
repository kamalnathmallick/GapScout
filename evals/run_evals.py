"""CLI runner for GapScout LLM Evals suite."""

import sys
from pathlib import Path

import pytest


def main() -> int:
    evals_dir = Path(__file__).resolve().parent
    print(f"Running GapScout LLM Evals from {evals_dir}...")
    args = [str(evals_dir), "-v"]
    return pytest.main(args)


if __name__ == "__main__":
    sys.exit(main())
