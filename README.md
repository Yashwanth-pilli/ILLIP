# ILLIP AI

ILLIP AI is a local-first AI assistant scaffold. It gives you a small FastAPI backend, a plain HTML/CSS/JavaScript frontend, five starter agents, local storage, and tests you can run immediately.

The goal of this repository is to be easy to understand before it is clever. It avoids heavy frontend frameworks and cloud-only assumptions so beginners can trace each request from the browser to the backend service that handles it.

## Quick Start

Prerequisites:

- Python 3.9+
- PowerShell on Windows
- About 100 MB of disk space for the virtual environment and local data

```powershell
# 1. Install dependencies and create the virtual environment
.\scripts\setup.ps1

# 2. Start the FastAPI backend
.\scripts\run_backend.ps1

# 3. In another terminal, start the frontend
.\scripts\run_frontend.ps1
```

Then open:

- Frontend UI: `http://localhost:8080`
- Backend API docs: `http://127.0.0.1:8000/docs`
- Backend health check: `http://127.0.0.1:8000/api/health`

## What Is Included

- Five starter agents: Planner, Builder, Reviewer, Tester, and Memory
- FastAPI routes for chat, tasks, memory, agents, health, and system status
- Service layer for business logic
- Provider abstraction with a mock provider ready to use
- SQLite models plus JSON-backed local storage helpers
- Plain JavaScript frontend that calls the backend with `fetch()`
- Pytest suite covering the main API flows
- Documentation for architecture, API usage, portability, and the self-building loop

## Project Structure

```text
ILLIP_AI/
  app/          Backend application, routes, services, agents, providers
  frontend/     Browser UI built with HTML, CSS, and JavaScript
  data/         Local runtime data such as logs, tasks, and memory
  docs/         Architecture and workflow documentation
  scripts/      PowerShell helpers for setup and local development
  tests/        Pytest tests for core API behavior
```

See [docs/folder_structure.md](docs/folder_structure.md) for a fuller map.

## Frontend and Backend Flow

The frontend and backend are intentionally separate but simple:

1. The browser loads `frontend/index.html`.
2. `frontend/app.js` sends requests to `http://127.0.0.1:8000/api`.
3. FastAPI routes in `app/api/routes/` validate and route the request.
4. Services in `app/services/` perform the work.
5. Local data is read from or written to `data/` and SQLite.
6. The backend returns JSON and the frontend updates the page.

The full request map is documented in [docs/integration_flow.md](docs/integration_flow.md).

## Core API Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Check backend health |
| `POST /api/chat/` | Send a chat message |
| `GET /api/tasks/` | List tasks |
| `POST /api/tasks/` | Create a task |
| `GET /api/memory/search` | Search memory |
| `GET /api/agents/` | List agents |
| `POST /api/agents/{agent_type}/execute` | Run an agent task |
| `GET /api/system/status` | Read system status |

Use `http://127.0.0.1:8000/docs` for interactive API testing.

## Agents

ILLIP AI starts with five complementary agents:

- Planner: breaks goals into steps
- Builder: drafts implementation work
- Reviewer: checks quality, risks, and standards
- Tester: proposes or validates tests
- Memory: stores and retrieves project knowledge

Read [AGENTS.md](AGENTS.md) for the agent lifecycle and extension pattern.

## Running Tests

```powershell
pytest -v
```

Useful focused runs:

```powershell
pytest tests/test_chat.py -v
pytest tests/test_agents.py -v
```

The tests use FastAPI's `TestClient`, so they exercise the same route layer the frontend calls.

## Configuration

Copy `.env.example` to `.env` if you want to override defaults:

```env
API_HOST=127.0.0.1
API_PORT=8000
MODEL_PROVIDER=mock
DEBUG=True
```

The mock provider is the safest default while learning the scaffold. It works without external accounts or model downloads.

## Safety Notes

- The project is local-first; data stays in this project folder unless you change the configuration.
- Keep `MODEL_PROVIDER=mock` until you intentionally connect another provider.
- If you rename or move API routes, update `frontend/app.js`, `docs/api.md`, and `docs/integration_flow.md` in the same change.
- Treat the self-building workflow as a guided development loop. It is designed around approval gates, review, testing, and audit logs.

## Documentation

- [START_HERE.md](START_HERE.md): beginner quick start
- [docs/integration_flow.md](docs/integration_flow.md): frontend/backend request flow
- [docs/architecture.md](docs/architecture.md): system design
- [docs/api.md](docs/api.md): API reference
- [docs/self_building_loop.md](docs/self_building_loop.md): safe improvement workflow
- [docs/portability.md](docs/portability.md): moving the project between machines
- [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md): future milestones

## Troubleshooting

Backend will not start:

- Check that port `8000` is free: `netstat -ano | findstr :8000`
- Re-run `.\scripts\setup.ps1`
- Confirm you are using the project virtual environment

Frontend cannot reach backend:

- Confirm the backend is running at `http://127.0.0.1:8000`
- Open browser dev tools and check the Console tab
- Confirm `frontend/app.js` still uses `http://127.0.0.1:8000/api`

Tests fail:

- Run `pytest -v` for the full error
- Make sure dependencies were installed with `.\scripts\setup.ps1`
- Check that local data folders exist under `data/`

## Current Status

Version: `0.1.0`  
Status: stable learning scaffold  
Default provider: `mock`
