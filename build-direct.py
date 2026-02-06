"""
Direct Nuitka build using subprocess
"""

import os
import subprocess
import sys
from pathlib import Path

print("=" * 80)
print("Building WH Product Manager")
print("=" * 80)
print(f"Python: {sys.executable}")
print(f"Python version: {sys.version}")

root_dir = Path(__file__).parent
main_file = root_dir / "src" / "wh_product_manager" / "test_build.py"
output_dir = root_dir / "dist"

print(f"\n✓ Entry point: {main_file}")
print(f"✓ Output directory: {output_dir}")

# Nuitka command
cmd = [
    sys.executable,
    "-m",
    "nuitka",
    "--onefile",
    "--windows-console-mode=attach",
    "--output-filename=WH-Product-Manager",
    f"--output-dir={output_dir}",
    "--assume-yes-for-downloads",
    "--include-package=wh_product_manager",
    "--include-package=wh_product_manager.core",
    "--enable-plugin=anti-bloat",
    str(main_file),
]

print("\n" + "-" * 80)
print("Running Nuitka compilation...")
print("-" * 80 + "\n")

# Create clean environment
env = os.environ.copy()

# Remove Anaconda from PATH
path_dirs = env.get("PATH", "").split(os.pathsep)
clean_path = [
    p for p in path_dirs if "anaconda" not in p.lower() and "conda" not in p.lower()
]

# Add current Python's directory at the beginning
python_dir = Path(sys.executable).parent
if str(python_dir) not in clean_path:
    clean_path.insert(0, str(python_dir))

env["PATH"] = os.pathsep.join(clean_path)
env["NUITKA_PYTHON_EXE"] = sys.executable

print(f"Using Python: {sys.executable}\n")

# Run Nuitka
result = subprocess.run(cmd, shell=False, env=env)

print("\n" + "-" * 80)

if result.returncode == 0:
    exe_path = output_dir / "WH-Product-Manager.exe"
    print("✅ Build successful!")
    print(f"📁 Output: {exe_path}")
    print(f"\nRun the test: {exe_path}")
    sys.exit(0)
else:
    print(f"❌ Build failed with return code {result.returncode}")
    sys.exit(1)
