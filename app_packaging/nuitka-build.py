#!/usr/bin/env python3
"""
Nuitka build script for WH Product Manager
Compiles FastAPI app into standalone Windows EXE
"""

import os
import subprocess
import sys
from pathlib import Path


def build():
    """Build the application with Nuitka"""

    PROJECT_NAME = "WH Product Manager"
    COMPANY_NAME = "WH-IT"
    VERSION = "1.0.0"
    EXE_NAME = "WH-Product-Manager"

    root_dir = Path(__file__).parent.parent
    main_file = root_dir / "src" / "wh_product_manager" / "main_build.py"
    icon_file = root_dir / "assets" / "icon.ico"
    output_dir = root_dir / "dist"

    print("=" * 80)
    print(f"Building {PROJECT_NAME} v{VERSION}")
    print("=" * 80)

    if not main_file.exists():
        print(f"ERROR: {main_file.name} not found at {main_file}")
        return False

    print(f"Entry point: {main_file}")
    print(f"Using Python: {sys.executable}")

    if icon_file.exists():
        icon_arg = f"--windows-icon-from-ico={icon_file}"
        print("Icon found")
    else:
        icon_arg = None
        print("Icon not found (optional)")

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        str(main_file),
        "--onefile",
        "--noinclude-default-mode=nofollow",
        "--include-module=wh_product_manager.main",
        f"--output-filename={EXE_NAME}",
        f"--windows-company-name={COMPANY_NAME}",
        f"--windows-product-name={PROJECT_NAME}",
        f"--windows-file-version={VERSION}",
        f"--windows-product-version={VERSION}",
        f"--output-dir={output_dir}",
        "--assume-yes-for-downloads",
    ]

    if icon_arg:
        cmd.insert(-1, icon_arg)

    print(f"\nOutput directory: {output_dir}\n")
    print("Running Nuitka compilation...")
    print("-" * 80)

    # Create clean environment with only necessary paths
    env = os.environ.copy()

    # Set Python executable for Nuitka
    env["NUITKA_PYTHON_EXE"] = sys.executable

    print(f"Python executable: {sys.executable}")

    result = subprocess.run(cmd, shell=False, env=env)

    print("-" * 80)

    if result.returncode == 0:
        exe_path = output_dir / f"{EXE_NAME}.exe"
        print("\nBuild successful!")
        print(f"Output: {exe_path}")
        print(f"\nRun the test: {exe_path}")
        return True
    else:
        print(f"\nBuild failed with return code {result.returncode}")
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
