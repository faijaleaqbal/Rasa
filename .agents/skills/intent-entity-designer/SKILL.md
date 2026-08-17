---
name: intent-entity-designer
description: Strategy and syntax for designing high-accuracy NLU intents, entity extraction patterns, lookup tables, regex features, and slot mapping.
---

# Intent & Entity Designer Skill

Methodologies for structuring training datasets, eliminating intent overlap, and maximizing entity extraction precision.

## Intent Hierarchy Design
1. **Granularity**: Keep intents distinct. Avoid overlapping intents (e.g. `ask_weather` vs `check_temperature` should be merged or separated with clear slot contexts).
2. **Diversity**: Provide at least 15-30 realistic, varied training examples per intent in `data/nlu.yml`.
3. **Out-of-Scope Handling**: Always maintain an `out_of_scope` or `nlu_fallback` intent to catch off-topic queries safely.

## Entity Extraction
* **Synonyms & Lookup Tables**: Use lookup tables in `data/nlu.yml` for large dictionaries of entities (cities, product names, devices).
* **Regex Features**: Use regex for structured formats like phone numbers, order IDs, email addresses, and timestamps.
* **Slot Mapping Types**:
  * `from_entity`: Automatically extract entity values into slots.
  * `from_text`: Capture whole message content into a slot.
  * `from_intent`: Set slot based on triggered intent.

## Validation
```bash
/home/ubuntu/rasa-env/bin/rasa data validate --data data/
```
