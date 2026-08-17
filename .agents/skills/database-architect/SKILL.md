---
name: database-architect
description: Database design, SQL schema modeling, indexing strategies, migrations, SQLite/PostgreSQL optimization, and ORM patterns.
---

# Database Architect Skill

Best practices for designing scalable database schemas, optimizing queries, and managing local and production databases.

## Schema Modeling Principles
1. **Normalization vs Denormalization**: Normalize transactional data (3NF) to eliminate redundancy; strategically denormalize read-heavy tables for high-throughput queries.
2. **Primary & Foreign Keys**: Always define explicit primary keys (UUID or auto-incrementing integer) and foreign keys with appropriate cascade rules (`ON DELETE CASCADE` or `SET NULL`).
3. **Indexing**:
   * Index frequently queried columns in `WHERE`, `JOIN`, and `ORDER BY` clauses.
   * Avoid excessive indexing on high-write tables.
   * Use composite indexes for multi-column query filters.

## SQLite Local Best Practices (`storage/data.db`)
* Enable WAL mode for concurrent read/write operations:
  ```sql
  PRAGMA journal_mode = WAL;
  PRAGMA synchronous = NORMAL;
  PRAGMA foreign_keys = ON;
  ```
* Perform automated daily backups:
  ```bash
  sqlite3 storage/data.db ".backup 'storage/backup_$(date +%Y%m%d).db'"
  ```

## Safe Migration Checklist
* Test migrations on a staging copy before applying to production.
* Ensure backward compatibility when modifying columns.
