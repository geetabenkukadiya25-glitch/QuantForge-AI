"""
QuantForge AI - project launcher.

Usage:
    python main.py api                 # run the FastAPI server
    python main.py ui                  # run the Streamlit dashboard
    python main.py init-db             # initialize the SQLite database
"""

import argparse
import subprocess
import sys
from pathlib import Path

from app.config.settings import get_settings
from app.database.db_manager import get_database_manager
from app.utils.logger import get_logger

logger = get_logger("launcher")


def run_api() -> None:
    import uvicorn

    settings = get_settings()
    get_database_manager().initialize()
    logger.info("Launching FastAPI server on %s:%s", settings.api_host, settings.api_port)
    uvicorn.run("app.api.server:app", host=settings.api_host, port=settings.api_port, reload=settings.debug)


def run_ui() -> None:
    settings = get_settings()
    dashboard_path = Path(__file__).resolve().parent / "app" / "ui" / "dashboard.py"
    logger.info("Launching Streamlit dashboard on port %s", settings.streamlit_port)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(dashboard_path),
            "--server.port",
            str(settings.streamlit_port),
        ],
        check=True,
    )


def run_init_db() -> None:
    manager = get_database_manager()
    manager.initialize()
    logger.info("Database initialized at %s", manager.db_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="QuantForge AI project launcher")
    parser.add_argument(
        "command",
        choices=["api", "ui", "init-db"],
        help="Which component to launch",
    )
    args = parser.parse_args()

    commands = {
        "api": run_api,
        "ui": run_ui,
        "init-db": run_init_db,
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
