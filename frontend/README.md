# DreamHack Local UI

This frontend is a localhost-only React dashboard for the DreamHack Local backend.

It is not a cloud app. It does not write challenge files directly from the browser. All crawl and download actions go through the local backend API, and the backend writes into the configured workspace path on the same machine.

## Stack

- React
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query
- React Router
- lucide-react

## Local-only contract

- The backend is the authority for filesystem writes.
- Clicking `Download` tells the local backend to save content into the configured workspace folder.
- The browser does not trigger a normal `Save As` download for challenge files.
- The UI reads challenge data, settings, session state, stats, and background jobs from the backend API.
- Backend warnings and errors such as `parse_warnings`, `last_error`, and job `error` are shown in the UI instead of being hidden.

## Setup

From the repo root:

```bash
cd frontend
cp .env.example .env
NPM_CONFIG_CACHE=/tmp/dreamhack-local-npm-cache npm install
```

The `.env.example` file exposes one frontend setting:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Leave it unset if you are using the default local backend address.

## Run

Start the backend first:

```bash
python3 dreamhack_crawler.py serve --host 127.0.0.1 --port 8000
```

Then run the frontend:

```bash
cd frontend
npm run dev
```

Vite serves the UI locally, typically at `http://127.0.0.1:5173`.

## Useful commands

```bash
cd frontend
npm run typecheck
npm run test
npm run build
```

Or from the repo root:

```bash
make ui-dev
make ui-test
make ui-build
```

## Main pages

- `Dashboard`: session state, totals, category and difficulty breakdowns, recent jobs, and quick actions.
- `Challenges`: searchable/filterable inventory with bulk download actions.
- `Jobs`: background crawl/download tracking with progress and error details.
- `Session`: import, test, and clear the locally stored DreamHack session.
- `Settings`: workspace/config controls, backend connection test, doctor report, and manifest export.

## Current backend endpoints used by the UI

- `GET /api/health`
- `GET /api/session`
- `POST /api/session/test`
- `POST /api/session/import`
- `POST /api/session/clear`
- `POST /api/crawl/sync`
- `POST /api/crawl/challenge`
- `GET /api/challenges`
- `GET /api/challenges/{id}`
- `POST /api/challenges/{id}/download`
- `POST /api/downloads/bulk`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/stats`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/export/manifest`
- `POST /api/sync/files`
- `POST /api/doctor`
- `POST /api/open-folder`

## Notes

- If the backend is unavailable, the UI stays usable and shows a clear banner with the command needed to start the API.
- `Open folder` is optional backend behavior and stays local to the machine.
- If a challenge has no downloadable attachment, the UI still shows locally saved metadata and description when the backend has persisted them.
- The UI now reflects backend download outcomes explicitly: `Not downloaded`, `Metadata only`, `Description saved`, `Files downloaded`, `Partial download`, and `Failed`.
