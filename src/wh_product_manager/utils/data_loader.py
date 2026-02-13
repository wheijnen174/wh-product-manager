"""
Utility for loading data files from the data/ directory
Works for both development and EXE builds
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any


def get_assets_dir() -> Path:
    """
    Get the assets directory path
    Works for both development and compiled EXE
    """
    file_ext = Path(sys.argv[0]).suffix

    if getattr(sys, "frozen", False) or file_ext in {".exe", ".app"}:
        # Running as compiled EXE
        # EXE is in: dist/WH-Product-Manager.exe
        # Data is in: dist/assets/
        exe_dir = Path(sys.argv[0]).parent
        data_dir = exe_dir / "assets"
    else:
        # Running as Python script
        # Script is in: src/wh_product_manager/
        # Data is in: assets/ (at project root)
        project_root = Path(__file__).parent.parent.parent.parent
        data_dir = project_root / "assets"

    if not data_dir.exists():
        raise FileNotFoundError(
            f"Assets directory not found at {data_dir}\n"
            f"Make sure 'assets/' folder exists next to the EXE or at project root"
        )

    return data_dir


def load_json(filename: str) -> dict[Any, Any]:
    """Load a JSON file from the assets directory"""
    data_dir = get_assets_dir()
    filepath = data_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Assets file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(
    filename: str,
    data: dict[Any, Any],
    sort_on_keys: bool = False,
    indent: bool = False,
) -> None:
    """Save a JSON file to the assets directory"""
    data_dir = get_assets_dir()
    filepath = data_dir / filename

    if sort_on_keys:
        data = dict(sorted(data.items()))

    with open(filepath, "w+", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4 if indent else None)


def load_csv(filename: str, delimiter: str = ",") -> list[dict[Any, Any]]:
    """Load a CSV file from the assets directory"""
    data_dir = get_assets_dir()
    filepath = data_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Assets file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return list(reader)


def get_log_file() -> Path:
    """Get the path to app.log"""
    data_dir = get_assets_dir()
    return data_dir / "app.log"
