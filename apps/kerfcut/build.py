import os
import subprocess
import sys

def build():
    print("Starting Nuitka build for KerfCut...")
    
    if os.path.exists(".env"):
        print("INFO: .env detected locally but will not be bundled into the build.")
    
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--plugin-enable=pyqt6",
        "--include-data-dir=assets=assets",
        "--windows-console-mode=disable",
        "--output-dir=build",
        "--assume-yes-for-downloads",
        "main.py"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("Build completed successfully!")
        print("Executable should be in build/main.dist/main.exe")
    else:
        print(f"Build failed with exit code {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build()
