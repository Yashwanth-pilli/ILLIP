# Add a Custom Connector — Zero Code Change Needed

Drop a `.py` file here. ILLIP auto-discovers and starts it on next run.

## Template

```python
import os
from app.connectors.base_connector import BaseConnector
from app.utils import logger

class MyConnector(BaseConnector):
    name = "my_service"
    description = "Connects ILLIP to My Service"
    required_env_vars = ["MY_SERVICE_API_KEY"]       # must be set to start
    optional_env_vars = ["MY_SERVICE_BASE_URL"]       # shown in /api/integrations/status

    async def start(self) -> bool:
        # Set up connection, start background task, etc.
        logger.info("MyConnector started")
        return True

    async def stop(self) -> None:
        # Clean up
        pass

    def is_active(self) -> bool:
        return bool(os.getenv("MY_SERVICE_API_KEY", ""))
```

## Then set the env var in .env

```
MY_SERVICE_API_KEY=your_key_here
```

Restart ILLIP. Connector appears in `GET /api/integrations/status`.

## HTTP-only integrations (Zapier, Make, any webhook tool)

No Python file needed. Register via API:

```
POST /api/webhooks/register
{
  "name": "zapier_trigger",
  "secret": "your_shared_secret",
  "target_agent": "planner"
}
```

ILLIP gives you a URL: `POST /api/webhooks/receive/zapier_trigger`
Use it as the webhook URL in Zapier/Make/anything.
