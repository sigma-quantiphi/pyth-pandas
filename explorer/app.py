"""CLI entry point for the pyth-pandas Streamlit explorer."""

import os
import sys
from pathlib import Path


def main() -> None:
    home = Path(__file__).parent / "home.py"
    os.execvp("streamlit", ["streamlit", "run", str(home), *sys.argv[1:]])


if __name__ == "__main__":
    main()
