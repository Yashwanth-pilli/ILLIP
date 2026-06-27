# Folder Structure Reference

## Complete Project Tree

```
ILLIP_AI/
├── app/
│   ├── __init__.py              ← Package initialization
│   ├── main.py                  ← FastAPI application entry point
│   ├── config.py                ← Configuration and settings
│   ├── dependencies.py          ← Dependency injection
│   ├── api/
│   │   ├── __init__.py          ← API router setup
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py        ← Health check endpoint
│   │       ├── chat.py          ← Chat endpoints
│   │       ├── tasks.py         ← Task endpoints
│   │       ├── memory.py        ← Memory endpoints
│   │       ├── agents.py        ← Agent endpoints
│   │       └── system.py        ← System status endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── constants.py         ← Application constants
│   │   ├── exceptions.py        ← Custom exceptions
│   │   ├── models.py            ← Data models
│   │   └── schemas.py           ← Pydantic schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chat_service.py      ← Chat business logic
│   │   ├── task_service.py      ← Task management
│   │   ├── memory_service.py    ← Memory/knowledge storage
│   │   ├── log_service.py       ← Application logging
│   │   ├── model_service.py     ← LLM model management
│   │   ├── workspace_service.py ← Workspace management
│   │   └── self_build_service.py← Safe self-improvement
│   ├── agents/
│   │   ├── __init__.py          ← Agent registry
│   │   ├── base_agent.py        ← Abstract agent class
│   │   ├── planner_agent.py     ← Planning agent
│   │   ├── builder_agent.py     ← Code generation agent
│   │   ├── reviewer_agent.py    ← Code review agent
│   │   ├── tester_agent.py      ← Testing agent
│   │   └── memory_agent.py      ← Memory management agent
│   ├── providers/
│   │   ├── __init__.py          ← Provider factory
│   │   ├── base_provider.py     ← Abstract provider
│   │   ├── mock_provider.py     ← Mock provider (testing)
│   │   └── ollama_provider.py   ← Ollama integration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── sqlite.py            ← SQLite initialization
│   │   └── models.py            ← Database models
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py            ← Logging utility
│   │   ├── path_utils.py        ← Path management
│   │   ├── time_utils.py        ← Time utilities
│   │   └── file_utils.py        ← File operations
│   └── prompts/
│       ├── system_prompt.md     ← System prompt
│       ├── planner_prompt.md    ← Planner instructions
│       ├── builder_prompt.md    ← Builder instructions
│       ├── reviewer_prompt.md   ← Reviewer instructions
│       └── tester_prompt.md     ← Tester instructions
├── frontend/
│   ├── index.html               ← Main UI page
│   ├── styles.css               ← Styling
│   └── app.js                   ← Frontend logic
├── data/
│   ├── .gitkeep
│   ├── illip.db                 ← SQLite database (created on first run)
│   ├── memory/                  ← Memory storage
│   │   └── .gitkeep
│   ├── logs/                    ← Application logs
│   │   └── .gitkeep
│   ├── tasks/                   ← Task files
│   │   └── .gitkeep
│   ├── workspaces/              ← Workspace data
│   │   └── .gitkeep
│   └── snapshots/               ← System snapshots
│       └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── test_health.py           ← Health check tests
│   ├── test_chat.py             ← Chat endpoint tests
│   ├── test_tasks.py            ← Task endpoint tests
│   ├── test_memory.py           ← Memory endpoint tests
│   └── test_agents.py           ← Agent endpoint tests
├── scripts/
│   ├── setup.ps1                ← Setup script
│   ├── run_backend.ps1          ← Start backend
│   ├── run_frontend.ps1         ← Start frontend
│   └── dev_start.ps1            ← Start both
├── docs/
│   ├── architecture.md          ← System architecture
│   ├── api.md                   ← API reference
│   ├── portability.md           ← Migration guide
│   ├── self_building_loop.md    ← Self-improvement docs
│   └── folder_structure.md      ← This file
├── README.md                    ← Project overview
├── START_HERE.md                ← Quick start guide
├── .gitignore                   ← Git ignore rules
├── .env.example                 ← Configuration template
├── requirements.txt             ← Python dependencies
├── AGENTS.md                    ← Agent framework docs
└── PROJECT_ROADMAP.md           ← Development roadmap
```

## Directory Purposes

### app/
Main application code organized by responsibility.

**api/** - HTTP endpoints and request handling
**core/** - Shared models, schemas, exceptions
**services/** - Business logic and operations
**agents/** - Agent framework and implementations
**providers/** - LLM model provider abstraction
**db/** - Database initialization and models
**utils/** - Helper functions and utilities
**prompts/** - Agent instructions and prompts

### frontend/
Web-based user interface (HTML/CSS/JavaScript).

### data/
Local data storage (auto-created).

**illip.db** - SQLite database
**memory/** - Chat/knowledge storage
**logs/** - Application logs
**tasks/** - Task data files
**workspaces/** - Workspace configurations
**snapshots/** - System state snapshots

### tests/
Test suite (pytest).

One file per major component.

### scripts/
Helper scripts for development (PowerShell on Windows).

### docs/
Reference documentation.

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application |
| `app/config.py` | Central configuration |
| `app/core/constants.py` | Application constants |
| `.env.example` | Config template |
| `requirements.txt` | Python dependencies |
| `README.md` | Project overview |
| `START_HERE.md` | Quick start guide |

## Important Notes

- **data/** is not committed to git (see .gitignore)
- **venv/** should not be committed (recreate on new machine)
- **.env** is not committed (copy from .env.example)
- All paths are relative, so structure must stay consistent
- Frontend is served automatically by FastAPI from /frontend

## Creating New Files

When adding new features:

1. **New service:** app/services/new_service.py
2. **New agent:** app/agents/new_agent.py
3. **New endpoint:** app/api/routes/new_route.py
4. **New test:** tests/test_new_feature.py
5. **Documentation:** docs/new_feature.md

## Symlinks & Aliases

On Mac/Linux, create shortcuts:

```bash
ln -s data/logs logs_link    # Easy log access
ln -s venv/bin/activate activate_venv
```

Windows batch shortcut:
```batch
mklink /D logs_link .\data\logs
mklink /D activate_venv .\venv\Scripts\Activate.ps1
```
