#!/usr/bin/env python3
"""
Nuitka build script for WH Product Manager
Compiles FastAPI app into standalone Windows EXE
"""

import subprocess
import sys
from pathlib import Path


def build():
    """Build the application with Nuitka"""

    # Project settings
    PROJECT_NAME = "WH Product Manager"
    COMPANY_NAME = "WH-IT"
    VERSION = "1.0.0.0"
    EXE_NAME = "WH-Product-Manager"

    # Paths
    root_dir = Path(__file__).parent
    main_file = root_dir / "src" / "wh_product_manager" / "run.py"
    icon_file = root_dir / "assets" / "icon.ico"
    output_dir = root_dir / "dist"

    print("=" * 80)
    print(f"Building {PROJECT_NAME} v{VERSION}")
    print("=" * 80)

    # Verify main file exists
    if not main_file.exists():
        print(f"❌ ERROR: run.py not found at {main_file}")
        return False

    # Check for icon
    if icon_file.exists():
        icon_arg = f"--windows-icon-from-ico={icon_file}"
        print(f"✓ Icon found: {icon_file}")
    else:
        icon_arg = None
        print(f"⚠ Warning: Icon not found at {icon_file} (optional)")

    # Build command
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--windows-console-mode=attach",  # Shows console for debugging
        f"--output-filename={EXE_NAME}",
        f"--windows-company-name={COMPANY_NAME}",
        f"--windows-product-name={PROJECT_NAME}",
        f"--windows-file-version={VERSION}",
        f"--windows-product-version={VERSION}",
        f"--output-dir={output_dir}",
        "--assume-yes-for-downloads",
        # IMPORTANT: Include the entire package
        "--include-package=wh_product_manager",
        # Include subpackages
        "--include-package=wh_product_manager.core",
        "--include-package=wh_product_manager.api",
        "--include-package=wh_product_manager.shopify",
        "--include-package=wh_product_manager.suppliers",
        "--include-package=wh_product_manager.utils",
        str(main_file),
    ]

    # Add icon if available
    if icon_arg:
        cmd.insert(-1, icon_arg)

    print(f"\n📦 Output directory: {output_dir}\n")
    print("Running Nuitka compilation...")
    print("-" * 80)

    # Run build
    result = subprocess.run(cmd, shell=False)

    print("-" * 80)

    if result.returncode == 0:
        exe_path = output_dir / f"{EXE_NAME}.exe"
        print("\n✅ Build successful!")
        print(f"📁 Output: {exe_path}")
        print(f"\nYou can now run: {exe_path}")
        return True
    else:
        print(f"\n❌ Build failed with return code {result.returncode}")
        print("Try running with: uv run python nuitka-build.py")
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
