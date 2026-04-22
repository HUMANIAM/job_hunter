from __future__ import annotations

import sys
from pathlib import Path

# Ensure package imports work when Streamlit is launched from within `ui/`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.app import candidate_profile_service
from ui.candidate.ui import main


if __name__ == "__main__":
    main(candidate_profile_service)
