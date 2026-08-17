---
name: performance-optimizer
description: Performance optimization, CPU/Memory profiling, async I/O bottlenecks, caching strategies, and asset compression.
---

# Performance Optimizer Skill

Methodologies for auditing, profiling, and maximizing application responsiveness, throughput, and compute efficiency.

## Key Optimization Areas

### 1. Python Async & Non-Blocking I/O
* Replace blocking `requests.get()` with `aiohttp` or `httpx.AsyncClient` in asynchronous action servers and API handlers.
* Avoid heavy compute in the main event loop; delegate CPU-intensive tasks to threadpools or background worker queues (`Celery` / `RQ`).

### 2. Database Query Tuning
* Eliminate `N+1` query antipatterns by batching lookups (`SELECT ... WHERE id IN (...)`).
* Use `EXPLAIN QUERY PLAN` in SQLite to verify index utilization:
  ```sql
  EXPLAIN QUERY PLAN SELECT * FROM conversations WHERE user_id = 'user123';
  ```

### 3. Frontend & Payload Optimization
* Enable Gzip / Brotli compression on reverse proxies.
* Optimize asset delivery with lazy loading and image optimization.
* Minify CSS and JS bundles in production.
