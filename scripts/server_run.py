from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app.py"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the Job Hunter backend server.")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to bind the backend server to. Defaults to {DEFAULT_PORT}.",
    )
    return parser.parse_args()


def load_app():
    spec = importlib.util.spec_from_file_location("job_hunter_server_app", APP_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load ASGI app from {APP_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def main() -> int:
    args = parse_args()
    uvicorn.run(load_app(), host=DEFAULT_HOST, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
