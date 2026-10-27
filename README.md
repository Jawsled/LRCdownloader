# LRC Downloader

A simple Qt6 GUI application to download lyrics for your local library.

- **Scan-first workflow:** existing `.lrc` files are detected at import before any network call and skipped unless force-refresh.
- **Respects your naming scheme:** `01 - Title.flac` → `01 - Title.lrc` next to your tracks. respects your folder structure and file naming scheme.
- **Embed-kind-aware skip:** embedded lyrics are classified as `none / plain / synced / enhanced`; a plain embed does NOT block a synced fetch (configurable).
- **Import:** Drag and drop or pick folders/files to import files for the session. `Clear` removes all imported tracks.
- **Sources chain:** LRCLIB → lrc.red → NetEase → QQ Music → syncedlyrics providers (Musixmatch/Megalobiz/LRCLIB) → Spotify Lyrics API (opt-in, needs `SP_DC`). Provider order and toggles live in **Settings**.

## Run from source

Requires Python 3.11+.

**Windows (PowerShell):**

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\.venv\Scripts\python.exe -m lrcdownloader
```

**macOS / Linux (bash):**

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m lrcdownloader
```

> Linux note: PySide6 needs Qt system libs. On Debian/Ubuntu:
> `sudo apt-get install libegl1 libgl1 libxkbcommon0 libdbus-1-3 libxcb-cursor0 libfontconfig1`

## Build a standalone executable (PyInstaller)

The recommended build is a single command on every OS — it installs deps,
runs the test suite, then produces an `onedir` GUI build via
`LRCdownloader.spec`:

**Windows (PowerShell):**

```
.\.venv\Scripts\python.exe scripts\build.py --spec
# output: dist\LRCdownloader\LRCdownloader.exe
# run it: .\dist\LRCdownloader\LRCdownloader.exe
```

**macOS / Linux (bash):**

```
.venv/bin/python scripts/build.py --spec
# output: dist/LRCdownloader/LRCdownloader
# run it: ./dist/LRCdownloader/LRCdownloader
```

**Build variants:**

| Command | Result |
|---|---|
| `python scripts/build.py --spec` | Recommended: onedir GUI build from the checked-in spec |
| `python scripts/build.py` | Same, but generated from CLI flags instead of the spec |
| `python scripts/build.py --onefile` | Single-file executable (simpler to share, slower to start) |
| `python scripts/build.py --debug` | Console build that keeps log output visible (troubleshooting) |

**Direct PyInstaller (without the wrapper):**

```
pip install -r requirements.txt
pyinstaller --noconfirm --clean LRCdownloader.spec
```

### OS-specific notes

- **Windows:** output is `dist\LRCdownloader\` (folder). Zip that folder to distribute. SmartScreen may warn on first run of an unsigned build — click *More info → Run anyway*, or sign the exe.
- **macOS:** output is `dist/LRCdownloader/`. Ad-hoc distribute with `tar -czf LRCdownloader-macos.tar.gz -C dist LRCdownloader`. Unsigned apps trigger Gatekeeper — right-click → *Open* on first launch, or `xattr -cr` / codesign your build. For a proper `.dmg`/`.app`, build on a Mac (you can't cross-compile macOS from Windows/Linux).
- **Linux:** output is `dist/LRCdownloader/`. Ensure the Qt system libs above are installed on the target machine (or bundle for your distro). Build on the oldest distro you want to support for best glibc compatibility.

Automated builds for all three OSes run in `.github/workflows/build.yml`
(on version tags `v*` or manual dispatch) — download the artifacts from the
Actions run.

## Sources & credits

- SongSync: https://github.com/Lambada10/SongSync
- syncedlyrics: https://github.com/moehmeni/syncedlyrics
- spotify-lyrics-api: https://github.com/akashrchandran/spotify-lyrics-api
- LRCLIB: https://lrclib.net/docs
- lrc.red: https://lrc.red/docs
- NetEase Cloud Music (unofficial web API)
- QQ Music (unofficial web API)

### Provider notes

- **lrc.red** requires e-mail address to identify themselves to prevent abuse. The app prompts for that email the first time lrc.red is
  used; cancel the prompt to skip lrc.red for that request. You can also set it
  in **Settings → lrc.red contact email**. Lyrics fetched from lrc.red are
  labelled `lrc.red` in the app. Only line/word-synced entries are used (its
  untimed entries are not readable).
- **NetEase** and **QQ Music** use unofficial web endpoints. They greatly improve
  Chinese/CJK coverage but may be rate-limited, geo-blocked, or changed without
  notice. Untick them in Settings if you do not wish to use them.
