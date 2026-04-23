# DreamHack Local

`DreamHack Local` is a local-only Python application for crawling DreamHack challenge metadata, persisting it in SQLite, writing local challenge folders, downloading authorized attachments with the user’s own authenticated session, exposing a localhost API for a future web UI, and supporting a full terminal workflow through a Typer CLI.

## Safety and Scope

- Local only. No cloud deployment, no telemetry, no remote storage.
- Uses only the authenticated session that the user provides locally.
- Does not bypass auth, CAPTCHA, anti-bot protections, or access controls.
- If content is not accessible with the current session, the app fails clearly and records the reason.
- Uses conservative request throttling and retry/backoff behavior.

## Current Layout

The repository already contains local challenge folders in a style like:

```text
Cryptography/Level_1/AESthetic
Reverse_Engineering/Level_1/ToyPacked
Web3/Level_6/MagicVote
```

The new app preserves that convention by default:

```text
<workspace_root>/<CategoryDisplay>/Level_<difficulty>/<ChallengeName>/
  metadata.json
  description.md
  description.html
  files/
```

When matching existing folders is possible, the app reuses them instead of creating a parallel tree.

## Features

- SQLite is the source of truth.
- `manifest.json` export is preserved for compatibility.
- Clean service split for crawling, parsing, downloads, session handling, workspace sync, and export.
- Session cookies are stored locally in a user config directory.
- CLI with commands for login, crawl, list, show, download, sync, doctor, export, config, and serving the API.
- FastAPI backend with background jobs for long crawl/download operations.
- Parser normalization is strict: category comes from an allowlist and difficulty is constrained to `0..10`, otherwise it is stored as `null` with a parse warning.

## How Downloads Work

Downloads are real backend actions.

- The UI and CLI both call the same local download service.
- The backend fetches the challenge detail page with the user’s stored authenticated session.
- The backend saves `metadata.json` and `description.md` or `description.html` into the deterministic challenge folder.
- If downloadable attachments exist and the session is authorized, the backend saves them into `files/`.
- The browser does not perform a normal file download. The backend writes into the configured workspace path on disk.

Example result:

```text
<workspace_root>/Web/Level_4/Neat_Web_Challenge/
  metadata.json
  description.md
  files/
    challenge.zip
```

## Download Status Meanings

- `Not downloaded`: no local download has completed for that challenge.
- `Metadata only`: local metadata exists, but there is no saved description text and no downloaded file.
- `Description saved`: local metadata and description were saved, but there was no downloadable file.
- `Files downloaded`: one or more attachments were downloaded successfully.
- `Partial download`: some files were saved, but one or more downloads failed.
- `Failed`: the download attempt failed and no attachment was saved.

## Backend/UI Contract

- The app is local-only.
- The backend is the authority for filesystem writes and challenge downloads.
- The frontend never claims to save directly to disk; it asks the backend to save into the configured workspace path.
- The backend exposes challenge list, challenge detail, settings, session state, stats, and background job progress.
- Challenge folders are deterministic and stable once created.
- If a challenge has no downloadable file, the backend still stores its metadata and description locally.
- Backend warnings and errors are part of the contract. The UI should surface `parse_warnings`, `last_error`, and job `error` values instead of hiding them.

## Requirements

- Python 3.11+
- Recommended install:

```bash
python3 -m pip install -e ".[dev]"
```

- Optional browser-based session bootstrap:

```bash
python3 -m pip install -e ".[playwright]"
playwright install chromium
```

## Configuration

The app reads environment variables from `.env` and `.env.example`, and persists user overrides in a local config file.

Important settings:

- `DH_WORKSPACE_ROOT`
- `DH_DATABASE_PATH`
- `DH_MANIFEST_EXPORT_PATH`
- `DH_REQUEST_DELAY_SECONDS`
- `DH_MAX_RETRIES`
- `DH_TIMEOUT_SECONDS`

Example:

```bash
cp .env.example .env
```

## Session / Login

Preferred options:

```bash
dh login --cookie-file cookie.txt
dh login --cookie "sessionid=..."
dh session status
dh session clear
```

Optional local browser bootstrap:

```bash
dh login --browser
```

This opens a local Chromium instance. You log in yourself. The app only stores the resulting cookies locally.

## CLI Usage

Core workflow:

```bash
dh crawl sync
dh list --category web --json
dh show 1234
dh download 1234
dh download --category web --difficulty 4 --not-downloaded
dh sync-files
dh export manifest
dh doctor
```

Real download examples:

```bash
dh download 1234
dh download https://dreamhack.io/wargame/challenges/1234
dh download --category web --not-downloaded
```

Configuration:

```bash
dh config set workspace /absolute/path/to/workspace
```

Run the localhost backend:

```bash
dh serve --host 127.0.0.1 --port 8000
```

## Localhost API

Main routes:

- `GET /api/health`
- `GET /api/session`
- `POST /api/session/test`
- `POST /api/session/import`
- `POST /api/session/clear`
- `POST /api/crawl/sync`
- `POST /api/crawl/challenge`
- `GET /api/challenges`
- `GET /api/challenges/{id}`
- `GET /api/stats`
- `POST /api/challenges/{id}/download`
- `POST /api/downloads/bulk`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/export/manifest`
- `POST /api/sync/files`
- `POST /api/doctor`
- `POST /api/open-folder`

The crawl/download endpoints return background job objects. Poll `/api/jobs/{job_id}` for status and results.
`GET /api/challenges/{id}` returns the challenge record plus file records so the UI can render local state without inferring it from the filesystem.

`GET /api/stats` also exposes category and difficulty distributions for the localhost dashboard.

## Frontend UI

A local-only React UI now lives in `frontend/`.

It is designed around the same contract as the backend:

- The browser does not directly save challenge files.
- Clicking `Download` tells the local backend to save into the configured workspace path.
- The UI reflects real session state, job progress, and local challenge metadata from the backend API.

Setup:

```bash
cd frontend
cp .env.example .env
NPM_CONFIG_CACHE=/tmp/dreamhack-local-npm-cache npm install
```

Run:

```bash
python3 dreamhack_crawler.py serve --host 127.0.0.1 --port 8000
cd frontend
npm run dev
```

Validation:

```bash
cd frontend
npm run typecheck
npm run test
npm run build
```

Convenience targets:

```bash
make ui-dev
make ui-test
make ui-build
```

## Storage

SQLite tables:

- `challenges`
- `challenge_files`
- `crawl_runs`
- `jobs`
- `app_settings`
- `session_state`

`manifest.json` is now an export artifact, not the primary source of truth.

## Testing

```bash
python3 -m pytest
```

## Compatibility Wrapper

The old entry file still exists:

```bash
python3 dreamhack_crawler.py --help
```

It now forwards to the new Typer CLI.

## Known Limitations

- Session validation is heuristic because DreamHack’s authenticated UI markers may change.
- Browser-based login capture is optional and requires Playwright.
- HTML structure can change; parser tests cover the normalization contract, not every live DreamHack template.
- Existing local folders without `metadata.json` are matched best-effort by category, difficulty, and title slug.

## Download Troubleshooting

If a download does not produce a real local file, check these first:

- Session missing or invalid:
  `dh session status`
- Workspace root not configured as expected:
  `dh config set workspace /absolute/path`
- Challenge or file not accessible to the logged-in account:
  the backend now surfaces the exact error in job detail and challenge `last_error`
- Detail page returned a logged-out or HTML error page instead of a file:
  the backend treats this as a real failure and will not mark the challenge as downloaded
- Challenge has no attachments:
  the backend still saves metadata and description locally and marks the challenge as `Description saved` or `Metadata only`

Useful checks:

```bash
dh show 1234 --json
dh doctor --json
```
