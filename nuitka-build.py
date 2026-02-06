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
    VERSION = "1.0.0"

    # Paths
    root_dir = Path(__file__).parent
    main_file = root_dir / "src" / "wh_product_manager" / "main.py"
    icon_file = root_dir / "assets" / "icon.ico"
    output_dir = root_dir / "dist"

    # Verify files exist
    if not main_file.exists():
        print(f"ERROR: main.py not found at {main_file}")
        return False

    if not icon_file.exists():
        print(f"WARNING: icon.ico not found at {icon_file}")
        icon_arg = ""
    else:
        icon_arg = f'--windows-icon-from-ico="{icon_file}"'

    # Build command
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        str(main_file),
        "--onefile",
        "--noinclude-default-mode=nofollow",
        "--include-module=wh_product_manager",
        f'--windows-company-name="{COMPANY_NAME}"',
        f'--windows-product-name="{PROJECT_NAME}"',
        f'--windows-file-version="{VERSION}"',
        f"--output-dir={output_dir}",
        "--assume-yes-for-downloads",  # Auto-download Nuitka's dependencies
        "--follow-imports",  # Follow all imports
    ]

    # Add icon if it exists
    if icon_arg:
        cmd.append(icon_arg)

    # Add these for faster/cleaner builds
    cmd.extend(
        [
            "--follow-import-to=wh_product_manager",  # Only follow our package
            "--nofollow-import-to=tests",  # Don't include tests
        ]
    )

    print(f"Building {PROJECT_NAME} v{VERSION}...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 80)

    # Run build
    result = subprocess.run(cmd, shell=False)

    if result.returncode == 0:
        print("-" * 80)
        print("✅ Build successful!")
        print(f"📦 Output: {output_dir}")
        return True
    else:
        print("-" * 80)
        print(f"❌ Build failed with return code {result.returncode}")
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
