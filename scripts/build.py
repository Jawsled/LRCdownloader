"""Cross-platform release build: `python scripts/build.py [--onefile] [--debug]`.

- Default: onedir + windowed (recommended for Qt: faster startup, easier to debug).
- --onefile: single executable (slower startup, simpler to distribute).
- --debug: keep console window open for logs (troubleshooting).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--onefile", action="store_true", help="single-file exe instead of onedir")
    ap.add_argument("--debug", action="store_true", help="console build for troubleshooting")
    ap.add_argument("--spec", action="store_true", help="build from LRCdownloader.spec instead of flags")
    args = ap.parse_args()

    py = sys.executable
    run([py, "-m", "pip", "install", "-r", "requirements.txt"])
    run([py, "-m", "pytest", "tests", "-q"])

    if args.spec:
        run([py, "-m", "PyInstaller", "--noconfirm", "--clean", "LRCdownloader.spec"])
    else:
        cmd = [
            py, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--name", "LRCdownloader",
            "--hidden-import", "mutagen",
            "--hidden-import", "httpx",
            "--hidden-import", "syncedlyrics",
            "--hidden-import", "rapidfuzz",
            "--hidden-import", "platformdirs",
            "--hidden-import", "keyring.backends",
        ]
        cmd.append("--onefile" if args.onefile else "--onedir")
        cmd.append("--console" if args.debug else "--windowed")
        cmd.append("lrcdownloader/__main__.py")
        run(cmd)

    dist = ROOT / "dist"
    print(f"\nBuild output in: {dist}")
    for p in sorted(dist.rglob("LRCdownloader*")):
        print("  ", p.relative_to(dist))


if __name__ == "__main__":
    main()
