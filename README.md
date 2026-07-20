# Password Strength & Breach Detection

A local web app that scores a password, estimates entropy and crack time, and checks it
against the HaveIBeenPwned breach corpus. Ships as a single self-contained binary — no
Python install needed on the target machine.

Your password never leaves the machine: breach checking uses the HIBP k-anonymity API,
which receives only the first 5 hex characters of the password's SHA-1 hash. Nothing is
logged or stored.

## Run from source

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py            # serves http://127.0.0.1:5000 and opens a browser
```

Environment variables: `HOST`, `PORT`, `NO_BROWSER=1`.

## Tests

```bash
python -m unittest discover -p 'test_*.py'
```

## Build the desktop app

Three layers, built in order: the Python backend is frozen with PyInstaller, then
Electron wraps it, then electron-builder produces installers.

```bash
pip install -r requirements-dev.txt
npm install

npm run backend     # 1. freeze the Flask backend -> dist/password-analyzer
npm start           # 2. run the Electron app against it (dev)
npm run dist        # 3. build installers for this OS -> release/
```

The Electron main process ([electron/main.js](electron/main.js)) asks the OS for a free
port, launches the backend on it, waits for the server to answer before showing a window,
enforces a single instance, opens external links in the real browser, and kills the
backend on quit. The renderer runs sandboxed with `contextIsolation` on and no Node
access.

Neither PyInstaller nor electron-builder can cross-compile, so each OS builds its own
installers. [.github/workflows/build.yml](.github/workflows/build.yml) does all five on
their native runners:

| Artifact | Runner | Formats |
| --- | --- | --- |
| `PasswordAnalyzer-macos-arm64` | macos-14 | `.dmg`, `.zip` |
| `PasswordAnalyzer-macos-x64` | macos-13 | `.dmg`, `.zip` |
| `PasswordAnalyzer-windows-x64` | windows-latest | NSIS `.exe`, portable `.exe` |
| `PasswordAnalyzer-linux-x64` | ubuntu-latest | `.AppImage`, `.deb` |
| `PasswordAnalyzer-linux-arm64` | ubuntu-24.04-arm | `.AppImage`, `.deb` |

Each runner also runs the test suite and smoke-tests the backend before packaging.
Trigger from the Actions tab (`workflow_dispatch`) or push to `main`.

## Headless / CLI use

The backend binary still works standalone — no Electron needed:

```bash
./dist/password-analyzer          # serves http://127.0.0.1:5000
```

## Dev build — unsigned

These are **unsigned dev builds** by design: no Apple Developer ID, no notarization, no
Windows Authenticode certificate. That avoids signing setup entirely, but the OS will
warn on first launch. Clearing it:

- **macOS** — `xattr -dr com.apple.quarantine "/Applications/Password Analyzer.app"`, or
  right-click → Open → Open. (Locally built apps aren't quarantined; downloaded ones are.)
- **Windows** — SmartScreen shows "Windows protected your PC" → More info → Run anyway.
- **Linux** — `chmod +x` the AppImage. No signing involved.

For public distribution you'd set `mac.identity` in [package.json](package.json) to a
Developer ID, enable `hardenedRuntime`, add notarization credentials, and supply an
Authenticode certificate for Windows.

## What changed from the original

- `/analyze` validates input — a missing or malformed body returns 400, not a 500.
- Crack time is computed in log space, so long passwords no longer overflow `2 ** entropy`.
- Scoring penalizes common passwords, repeats, sequences and keyboard runs, so
  `Password1!` no longer rates the same as random noise.
- Breach failures are reported as "unknown (offline)" rather than silently as "safe".
- Served by waitress instead of the Werkzeug dev server; `debug=True` removed (it exposes
  a remote-code-execution console).
- Special-character detection covers all non-alphanumerics, not a fixed list.
- A password found in a breach is now forced to Weak (capped at 20) regardless of its
  character mix — `Summer2024!` previously rated "Strong" despite 3,614 known exposures.
- Crack time pluralizes correctly ("1 day", not "1 days").
- Frontend rebuilt in Bitwarden's visual language: branded header, card layout, segmented
  strength meter, colour-coded breach banner, light/dark themes persisted to
  localStorage, live debounced analysis as you type with stale-response guarding.
- Removed dead files (`check_analyze.py`, `inspect_template.py`, `templates/test.py`,
  `script.jss`); tests expanded from 3 to 15.
