# KerfCut — Compilation Instructions

This document outlines how to compile KerfCut into a standalone Windows executable using Nuitka.

## Prerequisites
- Windows 10/11
- Python 3.12 (recommended stable)
- Microsoft Visual C++ (MSVC) compiler installed
- Virtual environment active with `Nuitka` and `zstandard` installed:
  ```bash
  .venv\Scripts\pip install Nuitka zstandard
  ```

## How to Compile
We have a pre-configured `build.py` script in the root directory that handles all the flags (PyQt6 plugin, asset bundling, etc.).

To start the build, run:
```bash
.venv\Scripts\python.exe build.py
```

## Build Artifacts
- The standalone distribution will be generated in `build/main.dist/`.
- The primary executable will be `main.exe` within that folder.

## Troubleshooting
- If Nuitka fails to find PyQt6, ensure you are running the script with the virtual environment's Python.
- If assets are missing, verify the `--include-data-dir=assets=assets` flag in `build.py`.
