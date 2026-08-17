---
name: analytics-logging
description: Structured JSON logging, observability, metrics tracking, conversation analytics, and crash monitoring.
---

# Analytics & Structured Logging Skill

Standards and patterns for application observability, structured logs, error tracking, and performance metrics.

## Structured Logging Pattern (Python)
Always emit logs in structured JSON format in production:
```python
import logging
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "extra": getattr(record, "extra", {})
        }
        return json.dumps(log_obj)
```

## Key Metrics to Track
1. **Latency**: End-to-end response time for Rasa NLU + Action execution.
2. **Intent Confidence Distribution**: Proportion of fallback intents triggered vs high-confidence classifications.
3. **Session Duration & Turns**: Average conversation length per user session.
4. **Error Rates**: HTTP 5xx responses and custom action execution exceptions.
