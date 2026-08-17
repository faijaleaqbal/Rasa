---
name: form-autofill-automation
description: Repetitive online web form filling, KYC/onboarding auto-population, and smart input validation via browser automation.
---

# Form Autofill & Web Workflow Automation Skill

Automates repetitive manual web data entry, multi-page application forms, registration flows, and survey submissions using Playwright/Puppeteer.

## Form Mapping & Execution
1. **Field Discovery**: Scan DOM for `<input>`, `<select>`, `<textarea>`, and `aria-label` tags.
2. **Schema Binding**: Safely bind user profile data (name, email, address, tax ID) to discovered form elements.
3. **Pre-Submission Review**: Display a filled summary modal and require user confirmation before triggering final submission buttons.
