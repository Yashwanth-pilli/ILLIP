# Start Here

This guide gets ILLIP AI running and shows where to look first.

## What You Have

ILLIP AI is a local-first assistant scaffold:

- A FastAPI backend in `app/`
- A plain browser frontend in `frontend/`
- Five starter agents
- Local task, memory, chat, and log storage
- Tests and docs for the main flows

No cloud account is required for the default mock provider.

## First Run

Open PowerShell in the project root:

```powershell
cd C:\Users\ketha\OneDrive\Desktop\ILLIP_AI
.\scripts\setup.ps1
```

Start the backend:

```powershell
.\scripts\run_backend.ps1
```

Open a second PowerShell window and start the frontend:

```powershell
.\scripts\run_frontend.ps1
```

Open the app:

```text
http://localhost:8080
```

## Useful Local URLs

| URL | What it shows |
| --- | --- |
| `http://localhost:8080` | Browser UI |
| `http://127.0.0.1:8000/docs` | Interactive API docs |
| `http://127.0.0.1:8000/redoc` | Alternate API docs |
| `http://127.0.0.1:8000/api/health` | Backend health check |

## Try These First

1. Send a chat message in the browser UI.
2. Open `http://127.0.0.1:8000/docs`.
3. Run `GET /api/agents/` from the API docs.
4. Run the test suite:

```powershell
pytest -v
```

## How The Pieces Connect

The frontend is small enough to trace by hand:

1. `frontend/index.html` loads the page.
2. `frontend/app.js` calls the backend API with `fetch()`.
3. FastAPI receives requests under `/api`.
4. Route modules in `app/api/routes/` call services in `app/services/`.
5. Services use agents, providers, SQLite, or JSON files as needed.
6. The backend returns JSON and the frontend renders it.

Read [docs/integration_flow.md](docs/integration_flow.md) for the full request map.

## Files To Read First

- `frontend/app.js`: browser-to-backend calls
- `app/main.py`: FastAPI application setup
- `app/api/__init__.py`: route registration
- `app/api/routes/chat.py`: chat endpoint example
- `app/services/model_service.py`: model and agent service entry points
- `app/agents/__init__.py`: agent registry
- `tests/test_chat.py`: simple API test pattern

## Safety Notes

- The default `mock` provider is safe for local learning and does not call an external model.
- Keep API route changes synchronized with `frontend/app.js` and the docs.
- The self-building workflow should stay behind review, tests, and approval gates.
- Do not store secrets in committed files. Use `.env` for local overrides.

## Common Issues

Backend will not start:

- Make sure setup completed successfully.
- Check whether port `8000` is already in use:

```powershell
netstat -ano | findstr :8000
```

Frontend cannot reach backend:

- Confirm the backend terminal is still running.
- Confirm `frontend/app.js` points to `http://127.0.0.1:8000/api`.
- Open browser dev tools with `F12` and check the Console tab.

Import errors:

- Re-run setup:

```powershell
.\scripts\setup.ps1
```

- Confirm Python can import the app from the project root:

```powershell
python -c "from app.main import app; print(app.title)"
```

## Development Commands

```powershell
.\scripts\dev_start.ps1       # Start backend and frontend helpers
.\scripts\run_backend.ps1     # Backend only
.\scripts\run_frontend.ps1    # Frontend only
pytest -v                     # Run tests
```

View recent logs:

```powershell
Get-Content .\data\logs\illip.log -Tail 50
```

## Next Reading

1. [docs/integration_flow.md](docs/integration_flow.md)
2. [docs/architecture.md](docs/architecture.md)
3. [AGENTS.md](AGENTS.md)
4. [docs/self_building_loop.md](docs/self_building_loop.md)
