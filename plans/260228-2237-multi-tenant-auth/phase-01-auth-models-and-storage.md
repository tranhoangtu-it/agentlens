# Phase 1 — Auth Models & Storage

## Context Links
- [models.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/models.py) — existing table patterns
- [alert_models.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/alert_models.py) — reference for separate model files
- [alert_storage.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/alert_storage.py) — reference for storage CRUD patterns
- [storage.py](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/server/storage.py) — `_get_engine()` reuse

## Overview
- **Priority**: P1 (blocks all other phases)
- **Status**: pending
- **Description**: Define User and ApiKey SQLModel tables + CRUD functions + Pydantic request schemas

## Key Insights
- Existing pattern: separate `*_models.py` for tables/schemas + `*_storage.py` for CRUD
- All storage functions reuse `storage._get_engine()` singleton
- Models use `SQLModel` with `Field(primary_key=True)` (string IDs via uuid4)
- Tables use `__table_args__` for composite indexes
- `datetime.now(timezone.utc)` for timestamps
- Must work with both SQLite and PostgreSQL (no dialect-specific SQL)

## Architecture

### User Table

```python
class User(SQLModel, table=True):
    id: str = Field(primary_key=True)          # uuid4
    email: str = Field(unique=True, index=True)
    password_hash: str                          # bcrypt
    display_name: Optional[str] = None
    is_admin: bool = Field(default=False)
    created_at: datetime                        # utc
    updated_at: datetime                        # utc
```

### ApiKey Table

```python
class ApiKey(SQLModel, table=True):
    __tablename__ = "api_key"
    id: str = Field(primary_key=True)          # uuid4
    user_id: str = Field(index=True)           # FK to User.id
    key_hash: str                               # sha256(key)
    key_prefix: str                             # first 8 chars for display: "al_xxxx..."
    name: str = Field(default="default")        # user-facing label
    created_at: datetime
    last_used_at: Optional[datetime] = None

    __table_args__ = (
        Index("ix_api_key_hash", "key_hash"),
    )
```

### Key Format

- Generated: `al_` + 32 hex chars (e.g., `al_a1b2c3d4e5f6...`)
- Stored: SHA-256 hash of full key (never store plaintext)
- Prefix: first 8 chars stored for display (`al_a1b2...`)
- Lookup: hash incoming key, query by `key_hash`

## Related Code Files

### Files to Create
1. `server/auth_models.py` — User, ApiKey tables + RegisterIn, LoginIn schemas (~60 lines)
2. `server/auth_storage.py` — CRUD: create_user, get_user_by_email, create_api_key, validate_api_key, list_user_api_keys, delete_api_key (~120 lines)

### Files to Modify
- `server/requirements.txt` — add `PyJWT>=2.9.0` and `bcrypt>=4.2.0`

## Implementation Steps

1. **Add dependencies to requirements.txt**
   ```
   PyJWT>=2.9.0
   bcrypt>=4.2.0
   ```

2. **Create `server/auth_models.py`**
   - `User(SQLModel, table=True)` — fields as above
   - `ApiKey(SQLModel, table=True)` — fields as above
   - `RegisterIn(BaseModel)` — email, password, display_name
   - `LoginIn(BaseModel)` — email, password

3. **Create `server/auth_storage.py`**
   - Import `_get_engine` from `storage`
   - `create_user(email, password, display_name, is_admin) -> User`
     - Hash password with `bcrypt.hashpw(password.encode(), bcrypt.gensalt())`
     - Return User with uuid4 id
   - `get_user_by_email(email) -> Optional[User]`
   - `get_user_by_id(user_id) -> Optional[User]`
   - `verify_password(plain, hashed) -> bool`
     - `bcrypt.checkpw(plain.encode(), hashed.encode())`
   - `create_api_key(user_id, name) -> tuple[ApiKey, str]`
     - Generate `al_` + `secrets.token_hex(16)` = full key
     - Store SHA-256 hash, return (ApiKey, full_key) — full_key shown once
   - `validate_api_key(raw_key) -> Optional[User]`
     - SHA-256 hash raw_key, look up ApiKey by hash, return owning User
     - Update `last_used_at` on match
   - `list_user_api_keys(user_id) -> list[ApiKey]`
   - `delete_api_key(key_id, user_id) -> bool`

4. **Update `server/storage.py` init_db()**
   - Import `auth_models` so `User` and `ApiKey` tables are registered with SQLModel.metadata before `create_all()`
   - Add: `from auth_models import User, ApiKey  # noqa: F401 — register tables`

## Todo List
- [ ] Add PyJWT and bcrypt to requirements.txt
- [ ] Create auth_models.py with User + ApiKey tables + request schemas
- [ ] Create auth_storage.py with all CRUD functions
- [ ] Update storage.py init_db to import auth_models
- [ ] Verify tables created on startup (manual test)

## Success Criteria
- `User` and `ApiKey` tables auto-created on `init_db()`
- `create_user` stores bcrypt-hashed password
- `verify_password` correctly validates credentials
- `create_api_key` returns `al_`-prefixed key
- `validate_api_key` finds user by SHA-256 hash lookup
- Works on both SQLite and PostgreSQL

## Risk Assessment
- **bcrypt on Alpine**: Docker image may need `build-base` for bcrypt compilation → mitigate by using `bcrypt[binary]` or prebuilt wheels
- **Migration order**: `init_db()` must import auth_models before `create_all()` → verified by test

## Security Considerations
- Passwords: bcrypt with default 12 rounds
- API keys: SHA-256 hashed, never stored in plaintext
- Full API key shown only once at creation time
- No timing attack surface — bcrypt.checkpw is constant-time
