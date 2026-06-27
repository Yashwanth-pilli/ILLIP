# Self-Building Loop & Safety

## Overview

ILLIP AI is designed to safely improve itself over time while maintaining human control.

## The Safe Build Cycle

```
┌─────────────────────────────────────────────┐
│         1. DETECT NEED                       │
│  - Identify missing capability              │
│  - Analyze error patterns                   │
│  - Prioritize improvement                   │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│         2. PLAN (Planner Agent)             │
│  - Break down improvement into tasks        │
│  - Identify dependencies                    │
│  - Estimate effort                          │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│         3. BUILD (Builder Agent)            │
│  - Generate implementation draft            │
│  - Follow code standards                    │
│  - Save to staging (not applied)           │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│         4. REVIEW (Reviewer Agent)          │
│  - Check code quality                       │
│  - Verify safety rules                      │
│  - Identify issues                          │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│         5. TEST (Tester Agent)              │
│  - Run unit tests                           │
│  - Test edge cases                          │
│  - Verify no regressions                    │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│         6. APPROVAL GATE ⚠️ CRITICAL        │
│  - Human review required                    │
│  - Change summary displayed                 │
│  - Option: Approve / Reject / Request Info │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
        │ APPROVED    │ REJECTED
        ▼             ▼
┌─────────────────┐  Go back to step 2
│   7. DEPLOY     │  and revise plan
│  - Apply changes│
│  - Backup first │
│  - Verify start │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│         8. LOG & LEARN                       │
│  - Record change in audit log              │
│  - Update memory with learnings            │
│  - Close improvement request               │
└─────────────────────────────────────────────┘
```

## Safety Rules

### Protected Files

These files CANNOT be auto-edited. Manual review required:

```
- app/main.py           (Application entry point)
- app/config.py         (Configuration)
- app/dependencies.py   (Dependency injection)
- .env                  (Environment secrets)
- requirements.txt      (Dependencies)
```

### Safe Changes

These can be auto-deployed after review:

```
- Agent implementations (app/agents/*)
- Service extensions (app/services/*.py for new services)
- Route additions (app/api/routes/*)
- Prompt updates (app/prompts/*.md)
- Frontend updates (frontend/*)
- Tests (tests/*)
```

### Approval Requirements

**Always requires human approval:**
1. Changes to protected files
2. New external dependencies
3. Changes to critical paths
4. Modifications to safety rules

**Faster approval path** (for experienced users):
- Prompt updates
- Agent improvements
- Frontend changes
- Test additions

## Implementation: SelfBuildService

```python
from app.services import get_self_build_service

service = get_self_build_service()

# Start a build session
session_id = service.start_build_session(
    goal="Add email notification feature"
)

# Execute phases
await service.execute_phase(session_id, SafeBuildPhase.PLAN)
await service.execute_phase(session_id, SafeBuildPhase.BUILD)
await service.execute_phase(session_id, SafeBuildPhase.REVIEW)
await service.execute_phase(session_id, SafeBuildPhase.TEST)

# Get approval from human
result = service.approve_build(session_id, reviewer="user@example.com")

# After approval, system would deploy
# await service.execute_phase(session_id, SafeBuildPhase.DEPLOY)
```

## Audit Trail

All improvements are logged:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "improvement_id": "imp_123",
  "goal": "Add feature X",
  "status": "approved",
  "approved_by": "human_reviewer",
  "changes": [
    {
      "file": "app/agents/new_agent.py",
      "status": "created",
      "lines": 150
    }
  ]
}
```

## Backups & Rollback

Before each deployment:

1. **Backup**: Full project backup created
2. **Deploy**: Changes applied
3. **Verify**: System health check
4. **Rollback**: One-click revert if issues

```
./backups/
  └── pre_deployment_2024_01_01_120000.zip
```

## Learning Loop

After successful improvements:

```
Change Applied
     │
     ▼
Monitor for 24-48 hours
     │
     ├─ All systems normal → Record as successful
     │
     └─ Issues detected → Analyze & improve
```

## User Control Points

Users can:

1. **Trigger**: Request specific improvements
2. **Review**: See proposed changes before approval
3. **Approve**: Decide when changes are applied
4. **Rollback**: Revert any change if issues arise
5. **Configure**: Set safety rules and preferences

## Future: Full Autonomy Path

Phase 1 (MVP): Human-in-the-loop (current)
Phase 2: Trusted auto-deploy for low-risk changes
Phase 3: Full autonomy with rollback capability
Phase 4: Self-healing and proactive improvements

## Example Workflow

### Scenario: System detects it's slow

```
1. DETECT
   - Response time > 2 seconds
   - Need: Optimize query caching

2. PLAN
   - Add Redis cache layer
   - Update service to use cache
   - Add cache invalidation

3. BUILD (staged)
   - Draft Redis integration
   - Save to draft/redis_integration.py
   - Create tests

4. REVIEW
   - Check security (no secrets exposed)
   - Check performance benefit
   - Verify no breaking changes

5. TEST
   - Run performance benchmarks
   - Verify cache hit rates
   - Check fallback behavior

6. APPROVAL
   ⚠️  USER REVIEWS:
   "Performance improves 40%, code looks good"
   ✓ APPROVED

7. DEPLOY
   - Create backup
   - Apply changes
   - Run health check
   - Verify 2sec goal met

8. LOG
   - Record: "Added Redis cache, 40% faster"
   - Update documentation
   - Suggest next optimization
```

## Conclusion

The self-building loop is designed to balance:

✅ **Improvement**: Continuous learning and growth
✅ **Safety**: Humans in control of critical decisions  
✅ **Auditability**: Full log of all changes
✅ **Reversibility**: Can rollback at any time
