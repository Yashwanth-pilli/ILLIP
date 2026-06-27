# Architecture Overview

## System Design

ILLIP AI is a local-first, modular AI system with clear separation of concerns.

### Core Architecture

```
┌─────────────────────────────────────────┐
│         Frontend (HTML/CSS/JS)          │
│     - Chat interface                    │
│     - Status dashboard                  │
│     - Task management UI                │
└─────────────┬───────────────────────────┘
              │ HTTP/REST
              ▼
┌─────────────────────────────────────────┐
│     FastAPI Backend Application         │
│  ┌───────────────────────────────────┐  │
│  │   API Routes                      │  │
│  │  - /chat, /tasks, /memory, ...   │  │
│  └───────────────┬───────────────────┘  │
│                  │                       │
│  ┌───────────────▼───────────────────┐  │
│  │   Services Layer                  │  │
│  │  - ChatService                    │  │
│  │  - TaskService                    │  │
│  │  - MemoryService                  │  │
│  │  - AgentService                   │  │
│  │  - ModelService                   │  │
│  └───────────────┬───────────────────┘  │
│                  │                       │
│  ┌───────────────▼───────────────────┐  │
│  │   Core Layer                      │  │
│  │  - Models & Schemas               │  │
│  │  - Exceptions                     │  │
│  │  - Constants                      │  │
│  └─────────────────────────────────────┘  │
│                                           │
│  ┌───────────────────────────────────┐  │
│  │   Agent Framework                 │  │
│  │  - PlannerAgent                   │  │
│  │  - BuilderAgent                   │  │
│  │  - ReviewerAgent                  │  │
│  │  - TesterAgent                    │  │
│  │  - MemoryAgent                    │  │
│  └───────────────────────────────────┘  │
│                                           │
│  ┌───────────────────────────────────┐  │
│  │   Model Providers                 │  │
│  │  - MockProvider (default)         │  │
│  │  - OllamaProvider (stub)          │  │
│  └───────────────────────────────────┘  │
│                                           │
│  ┌───────────────────────────────────┐  │
│  │   Storage Layer                   │  │
│  │  - SQLite Database                │  │
│  │  - JSON File Storage              │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│    Local Storage (Windows/Mac/Linux)    │
│  - data/illip.db (SQLite)              │
│  - data/logs/                          │
│  - data/memory/                        │
│  - data/tasks/                         │
└─────────────────────────────────────────┘
```

## Key Components

### Frontend
- **index.html**: Chat interface and dashboard
- **styles.css**: Responsive, modern styling
- **app.js**: Client-side logic and API integration

### Backend Services
- **ChatService**: Manages conversations and LLM interaction
- **TaskService**: CRUD operations for tasks
- **MemoryService**: Knowledge storage and retrieval
- **AgentService**: Coordinates agent execution
- **ModelService**: Manages LLM providers
- **SelfBuildService**: Safe self-improvement workflow

### Agent Framework
- **BaseAgent**: Abstract interface for all agents
- **PlannerAgent**: Decomposes goals into tasks
- **BuilderAgent**: Generates implementations
- **ReviewerAgent**: Validates code and outputs
- **TesterAgent**: Runs tests and validation
- **MemoryAgent**: Manages knowledge

### Model Providers
- **BaseProvider**: Abstract provider interface
- **MockProvider**: Safe testing provider (default)
- **OllamaProvider**: Local Ollama integration (stub)

### Database
- **SQLite**: Primary database for structured data
- **JSON Files**: Task and memory persistence

## Data Flow

### Chat Flow
```
User Input → Frontend → API → ChatService → ModelProvider → LLM Response → Storage → Frontend Display
```

### Task Execution Flow
```
Create Task → TaskService → AgentService → Agent Selection → Agent Execution → Result Storage → API Response
```

### Self-Build Workflow
```
Goal → Plan (Planner) → Build (Builder) → Review (Reviewer) → Test (Tester) → Approval Gate → Deploy
```

## Configuration

All configuration is centralized in:
- **app/config.py**: Settings and path management
- **.env**: Environment variables (development)

## Safety & Portability

### Safety Features
- Protected critical files list
- Approval gates before changes
- Full audit trail logging
- Sandbox environment

### Portability
- Relative path configuration
- Self-contained data storage
- No external dependencies
- Windows/Mac/Linux compatible

## Scalability Path

Current design supports growth:
- Service layer can be extended with new services
- Agent framework can add new agent types
- Provider interface supports new LLM backends
- Database can migrate to PostgreSQL/MySQL
- Frontend can scale to React/Vue
