---
name: prompt-engineering
description: Techniques and best practices for crafting robust LLM prompts, few-shot examples, output schemas, guardrails, and fallback handlers.
---

# Prompt Engineering Skill

Techniques for designing deterministic, reliable, and high-performance LLM prompts and conversational agent instructions.

## Core Prompt Architecture
When constructing system prompts for agents or LLM nodes:

1. **Role & Identity**: Explicitly define the persona, capabilities, boundaries, and communication style.
2. **Context & Domain Constraints**: Provide project-specific knowledge, guidelines, and forbidden patterns.
3. **Few-Shot Examples**: Include positive and negative input/output examples to anchor expected behavior.
4. **Structured Output Format**: Enforce JSON schema or strict formatting when output needs to be programmatically consumed.
5. **Fallbacks & Uncertainty**: Instruct the model to gracefully handle ambiguous queries or missing parameters.

## Best Practices
* **Zero Hallucination Anchoring**: Explicitly specify: "If the requested information is not in the context, state that you do not know rather than fabricating facts."
* **Chain-of-Thought (CoT)**: For complex multi-step reasoning, instruct the model to think step-by-step before producing final answers.
* **Guardrails**: Implement validation hooks to sanitize user input and prevent prompt injection or jailbreaking.
