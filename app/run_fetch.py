#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def bootstrap_project_root() -> None:
    root_str = str(PROJECT_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    # Keep relative imports and output paths anchored to the repository root.
    if Path.cwd() != PROJECT_ROOT:
        os.chdir(PROJECT_ROOT)


bootstrap_project_root()

from fetch_jobs import main


if __name__ == "__main__":
    main()
