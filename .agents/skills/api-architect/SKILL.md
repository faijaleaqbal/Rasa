---
name: api-architect
description: RESTful and Webhook API architecture, authentication schemes (JWT/OAuth2/API Keys), rate limiting, and standard response modeling.
---

# API Architect Skill

Architectural principles and patterns for designing resilient, secure, and developer-friendly APIs.

## RESTful Design Standards
* **Resource-Oriented URIs**: Use plural nouns (`/api/v1/conversations`, `/api/v1/users`).
* **HTTP Method Semantics**:
  * `GET`: Retrieve resource representation (idempotent, safe).
  * `POST`: Create resource or trigger action.
  * `PUT` / `PATCH`: Replace or update existing resource.
  * `DELETE`: Remove resource.
* **Standard HTTP Status Codes**:
  * `200 OK`, `201 Created`, `204 No Content`
  * `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `429 Too Many Requests`
  * `500 Internal Server Error`, `503 Service Unavailable`

## Security & Authentication
1. **Token Authentication**: Pass Bearer tokens via `Authorization: Bearer <jwt_token>` headers.
2. **Rate Limiting**: Implement token-bucket or fixed-window rate limiters to prevent API abuse.
3. **CORS Configuration**: Restrict allowed origins in production rather than using wildcard `*`.
4. **Payload Validation**: Use Pydantic models (Python) or Zod schemas (TypeScript) to strictly validate incoming request payloads.
