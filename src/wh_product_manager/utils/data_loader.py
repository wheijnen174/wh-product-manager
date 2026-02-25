"""
Utility for loading data files from the data/ directory
Works for both development and EXE builds
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any


def get_data_dir() -> Path:
    """
    Get the data directory path
    Works for both development and compiled EXE
    """
    file_ext = Path(sys.argv[0]).suffix

    if getattr(sys, "frozen", False) or file_ext in {".exe", ".app"}:
        # Running as compiled EXE
        # EXE is in: dist/WH-Product-Manager.exe
        # Data is in: dist/assets/
        exe_dir = Path(sys.argv[0]).parent
        data_dir = exe_dir / "data"
    else:
        # Running as Python script
        # Script is in: src/wh_product_manager/
        # Data is in: assets/ (at project root)
        project_root = Path(__file__).parent.parent.parent.parent
        data_dir = project_root / "data"

    if not data_dir.exists():
        raise FileNotFoundError(
            f"Data directory not found at {data_dir}\n"
            f"Make sure 'data/' folder exists next to the EXE or at project root"
        )

    return data_dir


def load_json(filename: str) -> dict[Any, Any] | list[Any]:
    """Load a JSON file from the data directory"""
    data_dir = get_data_dir()
    filepath = data_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(
    filename: str,
    data: dict[Any, Any] | list[Any],
    sort_on_keys: bool = False,
    indent: bool = False,
) -> None:
    """Save a JSON file to the data directory"""
    data_dir = get_data_dir()
    filepath = data_dir / filename

    if sort_on_keys and isinstance(data, dict):
        data = dict(sorted(data.items()))

    with open(filepath, "w+", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4 if indent else None)


def load_csv(filename: str) -> list[dict[Any, Any]]:
    """Load a CSV file from the assets directory"""
    data_dir = get_data_dir()
    filepath = data_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Assets file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        return list(reader)


def save_csv(filename: str, data: list[dict[Any, Any]]) -> None:
    """Save a CSV file to the assets directory"""
    data_dir = get_data_dir()
    filepath = data_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Assets file not found: {filepath}")

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(data)


def add_csv_line(filename: str, data: dict[Any, Any]) -> None:
    """Add a line to a CSV file in the assets directory"""
    data_dir = get_data_dir()
    filepath = data_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Assets file not found: {filepath}")

    with open(filepath, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys(), delimiter=";")
        writer.writerow(data)


def save_txt(filename: str, data: str) -> None:
    """Save a text file to the assets directory"""
    data_dir = get_data_dir()
    filepath = data_dir / filename

    with open(filepath, "w+", encoding="utf-8") as f:
        f.write(data)


def get_log_file() -> Path:
    """Get the path to app.log"""
    data_dir = get_data_dir()
    return data_dir / "app.log"
