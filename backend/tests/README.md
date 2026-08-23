# Backend Unit Tests

This directory contains comprehensive unit tests for the backend application, focusing on CRUD operations and authentication dependencies.

## Test Structure

Tests are organized into subdirectories that mirror the backend application structure:

- **conftest.py** - Shared fixtures including database setup, test users, projects, and tasks
- **crud/** - CRUD operation tests
  - `test_user.py` - Tests for User CRUD operations
  - `test_project.py` - Tests for Project CRUD operations
  - `test_task.py` - Tests for Task CRUD operations
- **api/** - API and dependency tests
  - `test_deps.py` - Tests for authentication dependencies and role-based access control

## Running Tests

### Run all tests

```bash
cd backend
bash ./scripts/test.sh
```

Or with uv directly:

```bash
cd backend
uv run pytest
```

### Run specific test file

```bash
uv run pytest tests/crud/test_user.py
```

### Run specific test class or function

```bash
uv run pytest tests/crud/test_user.py::TestUserCRUD::test_create_user
```

### Run with verbose output

```bash
uv run pytest -v
```

### Run with coverage report

```bash
uv run coverage run --source=app -m pytest
uv run coverage report --show-missing
uv run coverage html
```

## Test Database

Tests use a separate PostgreSQL database (`app_test`) with the same Docker PostgreSQL instance as development. Each test session:

- Creates the test database
- Runs Alembic migrations to set up the schema
- Each test function gets a fresh transaction that is rolled back after the test
- Drops the test database after all tests complete

This ensures tests use the exact same database engine and schema as production.

## Fixtures

### Database Fixtures

- `test_engine` - Creates a test database engine
- `db_session` - Provides an async database session with automatic rollback

### User Fixtures

- `test_user` - Regular active user
- `test_admin_user` - Platform superadmin (`roles=["admin"]`)
- `test_event_admin_user` - Runs the fixture events, holds no global role
- `test_outsider_user` - Belongs to no event at all
- `test_inactive_user` - Suspended user for testing access control
- `test_passwordless_user` - Account whose `password_hash` is NULL

All of them carry a real bcrypt hash of `tests.fixtures.users.TEST_USER_PASSWORD`
except the last, which exists to cover the legacy/demo shape.

### Task Fixtures

- `test_task` - Single task in `test_event`
- `test_draft_task` - Unpublished task

### Auth Fixtures

Factories that mint **real** HS256 tokens through `app.core.security`:

- `make_access_token(user, *, session_id=None)` - a valid access token
- `auth_headers(user, *, session_id=None)` - `{"Authorization": "Bearer …"}`
- `make_expired_access_token(user)` - correctly signed, `exp` in the past
- `make_tampered_access_token(user)` - correct claims, wrong signing key

### Client Fixtures

- `async_client` - always signed in as `test_user` (identity is overridden)
- `unauthenticated_client` - no identity override; `deps.py` runs for real.
  Required for anything under `/auth`, where being already signed in would
  make the test meaningless.

## Test Coverage

The test suite covers:

### CRUD Operations

- Creating records
- Reading single and multiple records
- Updating records (full and partial updates)
- Deleting records
- Pagination and filtering
- Search functionality
- Sorting (ascending/descending)
- Counting filtered results
- 404 error handling

### Authentication & Authorization

- Password hashing and verification (bcrypt, including its raising edge cases)
- Access-token minting and validation (HS256, expiry, forged signatures)
- Refresh-token rotation, revocation and reuse detection
- Role-based access control
- Active/inactive user handling
- Tokens naming an account that no longer exists
- CurrentUser, CurrentSuperuser and AnyUser dependencies
- The `X-Test-User-Email` E2E bypass, and that it is inert outside TESTING

## Adding New Tests

When adding new tests:

1. Place tests in the appropriate subdirectory:
   - `tests/crud/` for CRUD operation tests
   - `tests/api/` for API endpoint and dependency tests
   - Create new subdirectories as needed (e.g., `tests/logic/` for business logic tests)
2. Use the provided fixtures from conftest.py
3. Mark async tests with `@pytest.mark.asyncio`
4. Organize tests into classes for better grouping
5. Use descriptive test names that explain what is being tested
6. Test both success and failure cases
7. Test edge cases (empty lists, None values, etc.)

Example:

```python
@pytest.mark.asyncio
class TestMyFeature:
    """Test suite for my feature."""

    async def test_feature_success(self, db_session: AsyncSession):
        """Test successful feature execution."""
        # Arrange
        # Act
        # Assert
        pass

    async def test_feature_failure(self, db_session: AsyncSession):
        """Test feature handles errors correctly."""
        # Arrange
        # Act & Assert
        with pytest.raises(HTTPException):
            # Code that should raise
            pass
```

## Dependencies

Required test dependencies (in pyproject.toml):

- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `coverage` - Test coverage reporting

Tests use the same database driver as production:

- `asyncpg` - PostgreSQL async driver
- `psycopg[binary]` - PostgreSQL driver

## CI/CD Integration

Requires PostgreSQL instance (use Docker in CI)

- Fast execution (typically < 1 minute for full suite)
- Requires standard environment variables (POSTGRES_SERVER, etc.)
- Deterministic results (no flaky tests)
- Automatic database cleanupry database)
- Fast execution (typically < 1 minute for full suite)
- No environment variables needed for basic tests
- Deterministic results (no flaky tests)
