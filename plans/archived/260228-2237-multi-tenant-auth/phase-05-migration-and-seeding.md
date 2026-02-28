# Phase 5 — Migration & Admin Seeding

## Context Links
- [storage.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/storage.py) — `init_db()` runs on startup
- [main.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/main.py) — lifespan calls `init_db()`
- [Dockerfile](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/Dockerfile) — Docker env vars
- [Phase 1](phase-01-auth-models-and-storage.md) — User model + create_user
- [Phase 3](phase-03-tenant-isolation.md) — user_id columns on Trace, AlertRule, AlertEvent

## Overview
- **Priority**: P2
- **Status**: pending
- **Description**: Migrate existing data to a "default" admin tenant, seed admin user on first startup, handle upgrade from pre-auth installations

## Key Insights
- `init_db()` already runs `SQLModel.metadata.create_all(engine)` — new columns with `default=None` are added automatically for SQLite (ALTER TABLE ADD COLUMN). PostgreSQL same via SQLModel.
- Existing traces have `user_id=NULL` — assign them to the seeded admin user
- Admin seeding must be idempotent (safe to call on every startup)
- `AGENTLENS_ADMIN_EMAIL` and `AGENTLENS_ADMIN_PASSWORD` env vars control admin credentials

## Architecture

### Startup Flow
```
init_db()
  → create_all() — adds new tables + columns
  → seed_admin_user() — create admin if not exists
  → migrate_orphan_data() — assign user_id=NULL rows to admin
```

### Migration Strategy
```sql
-- Conceptual (executed via SQLModel/SQLAlchemy):
-- 1. Find or create admin user
-- 2. UPDATE trace SET user_id = :admin_id WHERE user_id IS NULL
-- 3. UPDATE alert_rule SET user_id = :admin_id WHERE user_id IS NULL
-- 4. UPDATE alert_event SET user_id = :admin_id WHERE user_id IS NULL
```

## Related Code Files

### Files to Create
1. `server/auth_seed.py` — `seed_admin_user()` and `migrate_orphan_data()` (~70 lines)

### Files to Modify
1. `server/storage.py` — call `seed_admin_user()` and `migrate_orphan_data()` after `create_all()` in `init_db()`
2. `server/Dockerfile` (optional) — document env vars

## Implementation Steps

1. **Create `server/auth_seed.py`**
   ```python
   import os
   import logging
   from sqlalchemy import text
   from sqlmodel import Session, select
   from auth_models import User
   from auth_storage import create_user, get_user_by_email
   from storage import _get_engine

   logger = logging.getLogger(__name__)

   ADMIN_EMAIL = os.environ.get("AGENTLENS_ADMIN_EMAIL", "admin@agentlens.local")
   ADMIN_PASSWORD = os.environ.get("AGENTLENS_ADMIN_PASSWORD", "changeme")

   def seed_admin_user() -> str:
       """Create admin user if not exists. Returns admin user_id."""
       existing = get_user_by_email(ADMIN_EMAIL)
       if existing:
           return existing.id

       user = create_user(
           email=ADMIN_EMAIL,
           password=ADMIN_PASSWORD,
           display_name="Admin",
           is_admin=True,
       )
       logger.info("Seeded admin user: %s", ADMIN_EMAIL)
       return user.id

   def migrate_orphan_data(admin_user_id: str) -> None:
       """Assign orphan records (user_id=NULL) to admin user."""
       engine = _get_engine()
       with Session(engine) as session:
           for table in ("trace", "alert_rule", "alert_event"):
               result = session.execute(
                   text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
                   {"uid": admin_user_id},
               )
               if result.rowcount > 0:
                   logger.info("Migrated %d orphan rows in %s", result.rowcount, table)
           session.commit()
   ```

2. **Update `server/storage.py` — `init_db()`**
   ```python
   def init_db():
       engine = _get_engine()
       SQLModel.metadata.create_all(engine)
       if engine.dialect.name == "sqlite":
           with engine.connect() as conn:
               conn.execute(text("PRAGMA journal_mode=WAL"))
               conn.commit()

       # Auth: seed admin + migrate orphan data
       from auth_seed import seed_admin_user, migrate_orphan_data
       admin_id = seed_admin_user()
       migrate_orphan_data(admin_id)
   ```

3. **Document env vars in README/Dockerfile**
   ```
   AGENTLENS_ADMIN_EMAIL=admin@agentlens.local
   AGENTLENS_ADMIN_PASSWORD=changeme
   AGENTLENS_JWT_SECRET=your-secret-here
   ```

## Migration Edge Cases

| Scenario | Handling |
|----------|----------|
| Fresh install (no data) | Admin seeded, no orphan rows to migrate |
| Upgrade from pre-auth | Admin seeded, all existing traces/rules/events assigned to admin |
| Restart after migration | `seed_admin_user` is idempotent (returns existing), `migrate_orphan_data` is no-op (no NULL rows) |
| Custom admin email | Set `AGENTLENS_ADMIN_EMAIL` env var |
| Multiple restarts | Safe — both functions are idempotent |

## Todo List
- [ ] Create auth_seed.py with seed_admin_user and migrate_orphan_data
- [ ] Update init_db() to call seeding functions
- [ ] Test: fresh DB → admin user created
- [ ] Test: existing traces → all assigned to admin
- [ ] Test: restart → no duplicate admin, no errors
- [ ] Document env vars in README

## Success Criteria
- First startup creates admin user with configured email/password
- All pre-existing traces, alert rules, and alert events get `user_id` = admin's ID
- Subsequent startups skip seeding (idempotent)
- Admin can log in immediately after upgrade
- Works on both SQLite and PostgreSQL

## Risk Assessment
- **Default password**: `changeme` is insecure. Log a warning on startup if default password is used. Document: "Change admin password via env var in production."
- **Large migration**: If thousands of existing traces, the UPDATE is a single statement — fast even on SQLite.
- **Column addition**: SQLModel `create_all()` with `Optional` + `default=None` handles ALTER TABLE transparently for both dialects.

## Security Considerations
- Log warning if admin password is the default `changeme`
- Never log the actual password value
- Admin user has `is_admin=True` — future phases can use this for elevated permissions
