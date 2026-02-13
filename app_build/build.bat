@echo off
REM Build script for WH Product Manager
REM Uses UV's managed Python environment
echo Building WH Product Manager EXE...
uv run python app_build/nuitka-build.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build complete! Check the dist folder for the EXE.
) else (
    echo.
    echo Build failed!
    pause
)