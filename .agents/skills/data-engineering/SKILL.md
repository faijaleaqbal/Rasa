---
name: data-engineering
description: Data pipelines, ETL extraction, JSON/CSV parsing, cleaning, transformations with Pandas, and data validation schemas.
---

# Data Engineering Skill

Procedures for ingesting, transforming, cleaning, and validating datasets for AI training and analytics.

## Data Processing Pipelines
1. **Extraction**: Ingest data from CSV, JSONL, SQLite databases, or external REST webhooks.
2. **Transformation**:
   * Handle missing values and null fields cleanly.
   * Strip trailing whitespaces, normalize casing, and remove unicode artifacts.
   * Deduplicate records to avoid biasing training sets.
3. **Loading**: Persist transformed records into structured storage formats (`storage/data.db`, Parquet, or JSONL).

## Validation with Pydantic / Pandera
* Define strict schemas before pipeline execution:
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ConversationTurn(BaseModel):
    sender_id: str
    user_message: str = Field(..., min_length=1)
    intent: Optional[str] = None
    entities: List[dict] = []
    timestamp: float
```
