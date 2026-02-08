"""
Utility for loading data files from the data/ directory
Works for both development and EXE builds
"""

import csv
import json
import sys
from pathlib import Path


def get_data_dir() -> Path:
    """
    Get the data directory path
    Works for both development and compiled EXE
    """
    if getattr(sys, "frozen", False):
        # Running as compiled EXE
        # EXE is in: dist/WH-Product-Manager.exe
        # Data is in: dist/data/
        exe_dir = Path(sys.executable).parent
        data_dir = exe_dir / "data"
    else:
        # Running as Python script
        # Script is in: src/wh_product_manager/
        # Data is in: data/ (at project root)
        project_root = Path(__file__).parent.parent.parent.parent
        data_dir = project_root / "data"

    if not data_dir.exists():
        raise FileNotFoundError(
            f"Data directory not found at {data_dir}\n"
            f"Make sure 'data/' folder exists next to the EXE or at project root"
        )

    return data_dir


def load_json(filename: str) -> dict:
    """Load a JSON file from the data directory"""
    data_dir = get_data_dir()
    filepath = data_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(filename: str) -> list[dict]:
    """Load a CSV file from the data directory"""
    data_dir = get_data_dir()
    filepath = data_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_log_file() -> Path:
    """Get the path to app.log"""
    data_dir = get_data_dir()
    return data_dir / "app.log"
