# TheLook Data Intelligence — Testing Console

A minimal React (Vite) chat console for testing your FastAPI + ADK backend
locally. Not a production frontend — built for fast iteration while you test
SQL/forecast/visualize workflows end to end.

## What it does

- Sends messages to your backend's `POST /chat` endpoint (NDJSON streaming).
- Renders three event types as they stream in:
  - `{"type": "status", ...}` — shown as small "› ..." progress lines while the agent works
  - `{"type": "text", ...}` — the final natural-language answer, appended live
  - `{"type": "chart", ...}` — rendered inline as a live Chart.js chart
- Lets you edit `user_id` and start a new `session_id` (useful for testing
  session-history growth / compaction behavior).

## Setup

```bash
cd thelook-frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. It proxies `/chat` and `/health` to
`http://localhost:8000` (see `vite.config.js`) — so make sure your FastAPI
backend (`uv run uvicorn app.main:app --reload`) is running on port 8000
first, and MongoDB is up.

If your backend runs on a different port, update the `proxy` block in
`vite.config.js`.

## Notes

- This is a dev tool, not hardened for production (no auth, no error
  boundaries beyond the basic try/catch around the stream read).
- Chart rendering assumes the backend's chart event shape from
  `app/tools/chart_tool.py`'s `build_chart_config`: `{type, labels, datasets}`.
- If you change the NDJSON event shape in `runner_service.py`, update
  `applyEvent()` in `src/App.jsx` to match.
