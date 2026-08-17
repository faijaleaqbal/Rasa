---
name: rasa-workflow
description: Procedures and best practices for developing, validating, training, and testing Rasa chatbot models, stories, rules, and custom actions.
---

# Rasa Workflow Skill

This skill provides step-by-step procedures for managing the Rasa conversational AI stack in this project.

## Environment & Path
* **Rasa Python Virtual Environment**: `/home/ubuntu/rasa-env/bin/python`
* **Rasa Executable**: `/home/ubuntu/rasa-env/bin/rasa`
* **Actions Directory**: `actions/`
* **Training Data**: `data/` (`nlu.yml`, `stories.yml`, `rules.yml`)
* **Domain Configuration**: `domain.yml`
* **Model Config**: `config.yml`
* **Endpoints**: `endpoints.yml`

## Procedures

### 1. Validate Training Data & Configuration
Before training, always validate that NLU, stories, rules, and domain are strictly consistent:
```bash
/home/ubuntu/rasa-env/bin/rasa data validate --config config.yml --domain domain.yml --data data/
```

### 2. Train a New Model
When intents, entities, stories, or pipelines are updated:
```bash
/home/ubuntu/rasa-env/bin/rasa train --domain domain.yml --data data/ --config config.yml --out models/
```

### 3. Test Custom Actions
To test custom action logic or run actions in isolation:
```bash
/home/ubuntu/rasa-env/bin/rasa run actions --actions actions --port 5055
```

### 4. Interactive Testing / Chat Verification
Use the local test script or curl to test the REST webhook endpoint:
```bash
./test_chat.sh "Hello, what can you do?"
```
Or directly query the REST webhook:
```bash
curl -s -X POST http://localhost:5005/webhooks/rest/webhook \
  -H "Content-Type: application/json" \
  -d '{"sender": "test_user", "message": "hello"}'
```

### 5. Check Story Consistency & Model Evaluation
To evaluate NLU and Core models against test sets:
```bash
/home/ubuntu/rasa-env/bin/rasa test --data tests/
```
