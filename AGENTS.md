# ILLIP AI - Agent Framework Documentation

## Overview

ILLIP AI uses a specialized agent framework with five complementary agents that work together to support autonomous development workflows.

## Agents

### 1. Planner Agent
**Role:** Task decomposition and planning

- Analyzes high-level goals
- Breaks them into actionable tasks
- Identifies dependencies
- Estimates effort
- Creates execution plans

**Trigger:** `POST /api/agents/planner/execute`

**Example:**
```
Input: "Build user authentication system"
Output: Plan with tasks for login, signup, password reset, token management
```

### 2. Builder Agent
**Role:** Code generation and implementation

- Receives task descriptions
- Generates code implementations
- Follows project conventions
- Includes documentation
- Writes production-ready code

**Trigger:** `POST /api/agents/builder/execute`

**Example:**
```
Input: "Create user login endpoint"
Output: Python FastAPI route with auth logic, error handling, tests
```

### 3. Reviewer Agent
**Role:** Quality assurance and review

- Reviews code for quality
- Checks for security issues
- Verifies standards compliance
- Provides improvement suggestions
- Creates review reports

**Trigger:** `POST /api/agents/reviewer/execute`

**Example:**
```
Input: "Review the login endpoint code"
Output: Report with quality assessment, security review, recommendations
```

### 4. Tester Agent
**Role:** Testing and validation

- Designs test cases
- Executes tests
- Reports results
- Identifies bugs
- Verifies requirements

**Trigger:** `POST /api/agents/tester/execute`

**Example:**
```
Input: "Test the login endpoint"
Output: Test results, coverage report, identified issues
```

### 5. Memory Agent
**Role:** Knowledge and context management

- Stores decisions and learnings
- Retrieves context when needed
- Searches knowledge base
- Manages conversation memory
- Maintains audit trail

**Trigger:** `POST /api/agents/memory/execute`

**Example:**
```
Input: "store:user_auth_patterns"
Output: Knowledge stored for future reference
```

## Agent Lifecycle

### Initialization
All agents are initialized when the application starts.

```python
from app.agents import get_agent_registry

registry = get_agent_registry()
agents = registry.list_agents()  # Get all agents
```

### Execution
Execute an agent task:

```python
from app.services import get_agent_service

service = get_agent_service()
result = await service.execute_agent_task(
    agent_type="planner",
    task_input="Your task here",
    context={"key": "value"}  # Optional context
)
```

### Task Processing

Each agent follows this pattern:

```
Input → Validate → Process → Output → Log
   │                              │
   └──────────────────────────────┘
           With Error Handling
```

## Agent Coordination

### The Standard Workflow

```
┌─────────────────────────────┐
│    User Request/Goal        │
└──────────────┬──────────────┘
               │
               ▼
        ┌─────────────┐
        │   PLANNER   │ ← Break down goal
        └────┬────────┘
             │ (Task list)
             ▼
        ┌─────────────┐
        │   BUILDER   │ ← Generate code
        └────┬────────┘
             │ (Implementation)
             ▼
        ┌─────────────┐
        │   REVIEWER  │ ← Check quality
        └────┬────────┘
             │ (Review report)
             ▼
        ┌─────────────┐
        │   TESTER    │ ← Validate
        └────┬────────┘
             │ (Test report)
             ▼
        ┌─────────────┐
        │   MEMORY    │ ← Store learnings
        └────┬────────┘
             │
             ▼
      ┌─────────────┐
      │ ✓ Complete  │
      └─────────────┘
```

## Agent API Endpoints

### List All Agents
```http
GET /api/agents/
```

Response:
```json
{
  "agents": [
    {
      "agent_type": "planner",
      "name": "Planner Agent",
      "is_available": true,
      "task_count": 5,
      "last_activity": "2024-01-01T12:00:00Z"
    }
  ],
  "total_available": 5
}
```

### Get Agent Status
```http
GET /api/agents/{agent_type}
```

### Execute Agent Task
```http
POST /api/agents/{agent_type}/execute?task_input=Your+task+here
```

## Extensibility

### Adding a New Agent

1. Create agent class:
```python
# app/agents/new_agent.py
from app.agents.base_agent import BaseAgent

class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__("new_agent", "New Agent")
    
    async def process(self, task_input, context=None):
        # Implementation
        return "Result"
```

2. Register in registry:
```python
# app/agents/__init__.py
from app.agents.new_agent import NewAgent

# Add to _initialize_agents()
new_agent = NewAgent()
self.agents[new_agent.agent_type] = new_agent
```

3. Update service if needed:
```python
# app/services/model_service.py or new service
```

### Custom Prompts

Each agent has a corresponding prompt in `app/prompts/`:

- `system_prompt.md` - Global system prompt
- `planner_prompt.md` - Planner instructions
- `builder_prompt.md` - Builder instructions
- `reviewer_prompt.md` - Reviewer instructions
- `tester_prompt.md` - Tester instructions

Update prompts to modify agent behavior without changing code.

## Safety & Audit

All agent executions are:
- Logged with timestamp
- Tracked with task counts
- Marked with last activity
- Subject to error handling

## Performance

Agents are lightweight and fast:
- Initialization: < 100ms
- Task execution: 1-5s (depending on complexity)
- Memory usage: < 50MB total

## Future Enhancements

Planned agent improvements:
- Parallel agent execution
- Agent-to-agent communication
- Custom agent types per project
- Agent performance metrics
- Specialized domain agents
