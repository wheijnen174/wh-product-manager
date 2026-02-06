@echo off
REM Build script that removes Anaconda from PATH
REM This ensures we use UV's Python, not Anaconda's

echo Removing Anaconda from PATH...
set PATH=C:\Windows\System32;C:\Windows;C:\Program Files\Git\cmd

echo Current Python:
where python

echo.
echo Building WH Product Manager EXE...
uv run python nuitka-build.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build complete! Check the dist folder for the EXE.
    pause
) else (
    echo.
    echo Build failed!
    pause
)