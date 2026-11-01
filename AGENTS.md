# PCDeck Autonomous Agent Operating Rules (STRICT)

## 1. Anti-Sycophancy & Honesty Protocol
- NEVER agree with the user just to be polite or supportive.
- Do NOT flip-flop your recommendation when the user pushes back. State the technical facts, trade-offs, and risks directly.
- Before claiming any task is done, verify the result empirically (run tests, check `gh run list`, inspect binary hashes).

## 2. Public Repository Threat Model (`greson719/pcdeck` is PUBLIC)
- **Zero Plaintext Secrets:** NEVER hardcode developer bypass tokens, passwords, customer emails, or real license UUIDs anywhere in `server/`, `tests/`, `docs/`, or `tools/audit_repo.py`.
- **Hash-Only PII Scanning:** `tools/audit_repo.py` must only store one-way SHA-256 hashes of forbidden strings and reject any un-allowlisted RFC-4122 UUID.
- **Sanitized Release Notes:** NEVER disclose exploit mechanics (e.g., "CSWSH", "Sec-Fetch-Site") or internal cryptography (e.g., "HMAC-SHA256 salt") in Microsoft Store or public release notes.

## 3. Ban on "Reward Hacking" & Test Shortcuts
- **Never Cut Test Coverage:** `.github/workflows/verify.yml` MUST always run the full `python -m pytest tests/` suite (90+ tests). NEVER pass a subset of test files in CI to make a build green.
- **Never Weaken Failing Tests:** If an existing test in `tests/` fails after your change, assume your code broke backward compatibility (e.g., existing `license.dat` files on customer PCs). Fix the backward-compatibility bug in the server code; only update a test if the test fixture itself is provably outdated, and explicitly report any test file edits to the user.
- **Hard Failures Only:** Verification scripts (`tools/audit_repo.py`, `tools/verify_website.py`) must exit `1` on failure. Agents ignore `[WARNING]` logs.

## 4. Mandatory Cross-System Pre-Flight Checks
Before editing any file, check these 4 system boundaries:
1. **Android WebView vs. Desktop Browser (`server/main.py` & `MainActivity.java`):**
   - `PCDeck.apk` loads UI via `file:///android_asset/index.html`, which sends `Origin: null` or `Origin: file://` with `"Android"` in `User-Agent`.
   - Desktop browsers can forge `Origin: null` via `<iframe sandbox="allow-scripts">` (which includes `Sec-Fetch-Site: cross-site` and a Desktop `User-Agent`).
   - Any CORS, `/api/ping`, or `/ws` auth change MUST block desktop cross-site/sandboxed origins while preserving Android WebView access.
2. **Offline License Backward Compatibility (`server/license_manager.py`):**
   - Paying customers have existing `%LOCALAPPDATA%\PCDeck\license.dat` files on disk. Any change to signature validation MUST support transparent migration from the previous schema without logging out existing Pro users.
3. **Binary Rebuild & Version Sync Cascade:**
   - Editing `static/app.js` or `index.html` requires syncing `android_app/assets/` and rebuilding BOTH `PCDeck.apk` and `PCDeck.exe`.
   - Editing `server/*.py` requires rebuilding `PCDeck.exe` (`python build_exe.py`) before committing or releasing.
   - NEVER bump `version.json` (e.g., to `2.7.8.1`) unless explicitly instructed to cut a full new release across all binaries.
4. **MSIX Read-Only Container:**
   - Never write logs, temp files, or licenses relative to `__file__`. Always use `%LOCALAPPDATA%\PCDeck` or `~/.pcdeck`.

## 5. Definition of Done (Mandatory Exit Gate)
A code/release task is NOT complete until all 4 commands return Exit Code 0:
1. `python tools/audit_repo.py`
2. `python tools/verify_website.py`
3. `python -m pytest tests/` (must collect >= 90 tests)
4. If pushed to GitHub: `gh run list --limit 1` must show `completed success`.

## 6. Execution & Communication Style
- **Mandatory Caveman Mode:** Minimum words, maximum signal. State exact actions, file diffs, test outputs, exit codes.
- **Customer Support Voice:** First-person only (`"I"`, `"my"`, `"me"`). Never use `"we"` or `"our team"`. Zero emojis in UI, code, or documentation.
