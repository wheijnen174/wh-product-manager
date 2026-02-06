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
    VERSION = "1.0.0.0"
    EXE_NAME = "WH-Product-Manager"

    root_dir = Path(__file__).parent
    main_file = root_dir / "src" / "wh_product_manager" / "test_build.py"
    icon_file = root_dir / "assets" / "icon.ico"
    output_dir = root_dir / "dist"

    print("=" * 80)
    print(f"Building {PROJECT_NAME} v{VERSION}")
    print("=" * 80)

    if not main_file.exists():
        print(f"❌ ERROR: test_build.py not found at {main_file}")
        return False

    print(f"✓ Entry point: {main_file}")
    print(f"✓ Using Python: {sys.executable}")

    if icon_file.exists():
        icon_arg = f"--windows-icon-from-ico={icon_file}"
        print("✓ Icon found")
    else:
        icon_arg = None
        print("⚠ Icon not found (optional)")

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--windows-console-mode=attach",
        f"--output-filename={EXE_NAME}",
        f"--windows-company-name={COMPANY_NAME}",
        f"--windows-product-name={PROJECT_NAME}",
        f"--windows-file-version={VERSION}",
        f"--windows-product-version={VERSION}",
        f"--output-dir={output_dir}",
        "--assume-yes-for-downloads",
        "--include-package=wh_product_manager",
        "--include-package=wh_product_manager.core",
        "--enable-plugin=anti-bloat",
        str(main_file),
    ]

    if icon_arg:
        cmd.insert(-1, icon_arg)

    print(f"\n📦 Output directory: {output_dir}\n")
    print("Running Nuitka compilation...")
    print("-" * 80)

    # Create clean environment with only necessary paths
    env = os.environ.copy()

    # Remove Anaconda from PATH to prevent conflicts
    path_dirs = env.get("PATH", "").split(os.pathsep)
    clean_path = []

    for path_dir in path_dirs:
        # Skip Anaconda directories
        if "anaconda" not in path_dir.lower() and "conda" not in path_dir.lower():
            clean_path.append(path_dir)

    # Add current Python's directory at the beginning
    python_dir = Path(sys.executable).parent
    clean_path.insert(0, str(python_dir))

    env["PATH"] = os.pathsep.join(clean_path)

    # Set Python executable for Nuitka
    env["NUITKA_PYTHON_EXE"] = sys.executable

    print(f"Python executable: {sys.executable}")
    print(
        f"Anaconda removed from PATH: {any('anaconda' in p.lower() for p in path_dirs)}"
    )

    result = subprocess.run(cmd, shell=False, env=env)

    print("-" * 80)

    if result.returncode == 0:
        exe_path = output_dir / f"{EXE_NAME}.exe"
        print("\n✅ Build successful!")
        print(f"📁 Output: {exe_path}")
        print(f"\nRun the test: {exe_path}")
        return True
    else:
        print(f"\n❌ Build failed with return code {result.returncode}")
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
