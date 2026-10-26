"""Check that required packages import and report the status of the optional models.

Usage: python scripts/verify_installation.py
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REQUIRED = ("fastapi", "pandas", "sklearn", "httpx", "uvicorn")


def main() -> None:
    for module in REQUIRED:
        try:
            importlib.import_module(module)
            print(f"ok       {module}")
        except ImportError:
            print(f"MISSING  {module}")

    from backend.adapters.tabpfn_adapter import TabPFNAdapter
    from backend.main import get_gemma

    print("TabPFN:", TabPFNAdapter().status())
    print("Gemma :", get_gemma().check())
    print("Run the evaluation with: python scripts/run_evaluation.py --version <vN>")


if __name__ == "__main__":
    main()
