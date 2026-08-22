# CRUD Operations

This directory contains CRUD (Create, Read, Update, Delete) utilities for database operations in the FastAPI application. The CRUD system is built around a base class that provides common database operations using SQLModel and AsyncSession.

## Tech Stack

-   **SQLModel** + **SQLAlchemy (async)** for ORM/data access
-   **Pydantic** schemas for input/output typing
-   **FastAPI** for HTTP exceptions in CRUD helpers

## Architecture Overview

The CRUD system follows a consistent pattern:

-   **Base Class**: `CRUDBase` - Generic base class with common CRUD operations
-   **Model-Specific Classes**: Extend `CRUDBase` for each SQLModel
-   **Type Safety**: Uses Generic types for models and schemas
-   **Async Operations**: All database operations are asynchronous

## Core Components

### Base CRUD Class

The `CRUDBase` class provides a generic foundation for all CRUD operations:

```python
from app.crud.base import CRUDBase
from app.models import YourModel
from app.schemas import YourModelCreate, YourModelUpdate


class CRUDYourModel(CRUDBase[YourModel, YourModelCreate, YourModelUpdate]):
    pass


your_model = CRUDYourModel(YourModel)
```

### Generic Type Parameters

The base class uses three generic type parameters:

-   `ModelType`: The SQLModel class (must extend `Base`)
-   `CreateSchemaType`: Pydantic schema for creating new records
-   `UpdateSchemaType`: Pydantic schema for updating existing records

## Available Operations

### Read Operations

#### `get()`

Retrieve a single record by ID with optional error handling:

```python
# Returns None if not found
user = await crud.user.get(session, id=user_id)

# Raises 404 HTTPException if not found
user = await crud.user.get(session, id=user_id, raise_404_error=True)

# With relationship loading
user = await crud.user.get(session, id=user_id, select_in_load=["items"])
```

#### `get_multi()`

Retrieve multiple records with pagination and filtering:

```python
# Basic pagination
users = await crud.user.get_multi(session, skip=0, limit=100)

# Filter by specific IDs
users = await crud.user.get_multi(session, ids=["id1", "id2", "id3"])

# With relationship loading
users = await crud.user.get_multi(session, select_in_load=["items"])
```

#### `iterate()`

Iterate through large datasets efficiently:

```python
from app.crud.base import NamedFilterFields

# Basic iteration
async for user in crud.user.iterate(session, n=50):
    process_user(user)

# With filtering
filters = [NamedFilterFields("is_active", True)]
async for user in crud.user.iterate(session, filter_by=filters):
    process_active_user(user)

# Advanced filtering with comparisons
filters = [
    NamedFilterFields("age", 18, greater_then_comp="gt"),
    NamedFilterFields("status", "banned", is_not=True),
]
```

#### `get_count()`

Get the total count of records with optional filtering:

```python
# Total count
total = await crud.user.get_count(session)

# Filtered count
filters = [NamedFilterFields("is_active", True)]
active_count = await crud.user.get_count(session, filter_by=filters)
```

### Write Operations

#### `create()`

Create a new record:

```python
from app.schemas import UserCreate

user_data = UserCreate(email="user@example.com", full_name="John Doe")
new_user = await crud.user.create(session, obj_in=user_data)
```

#### `update()`

Update an existing record:

```python
from app.schemas import UserUpdate

# Using schema
update_data = UserUpdate(full_name="Jane Doe")
updated_user = await crud.user.update(session, db_obj=existing_user, obj_in=update_data)

# Using dictionary
update_dict = {"full_name": "Jane Doe"}
updated_user = await crud.user.update(
    session,
    db_obj=existing_user,
    obj_in=update_dict,
    skip_refresh=True,  # Skip database refresh for performance
)
```

### Delete Operations

#### `remove()`

Delete a single record:

```python
deleted_user = await crud.user.remove(session, id=user_id)
```

#### `remove_multi()`

Delete multiple records by IDs:

```python
await crud.user.remove_multi(session, ids=[1, 2, 3, 4])
```

## Advanced Filtering

The `NamedFilterFields` class supports complex filtering:

```python
from app.crud.base import NamedFilterFields

# Basic equality
NamedFilterFields("status", "active")

# Negation (NOT equal)
NamedFilterFields("status", "banned", is_not=True)

# Greater than comparison
NamedFilterFields("age", 18, greater_then_comp="gt")

# Less than or equal comparison
NamedFilterFields("score", 100, greater_then_comp="le")
```

## Creating Custom CRUD Classes

### Basic Implementation

```python
# models/user.py
from sqlmodel import SQLModel, Field
from app.models import Base


class User(Base, table=True):
    id: int = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str
    is_active: bool = True


# schemas/user.py
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None


# crud/user.py
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, session: AsyncSession, *, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def authenticate(
        self, session: AsyncSession, *, email: str, password: str
    ) -> User | None:
        user = await self.get_by_email(session, email=email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user


user = CRUDUser(User)
```

### Advanced Custom Methods

```python
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_active_users(
        self, session: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[User]:
        result = await session.execute(
            select(User).where(User.is_active == True).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def deactivate_user(self, session: AsyncSession, *, user_id: int) -> User:
        user = await self.get(session, id=user_id, raise_404_error=True)
        return await self.update(session, db_obj=user, obj_in={"is_active": False})
```

## Best Practices

### 1. Schema Design

-   Create separate schemas for Create, Update, and Read operations
-   Use optional fields in Update schemas
-   Include validation rules in schemas

### 2. Relationship Loading

-   Use `select_in_load` for eager loading relationships
-   Be mindful of N+1 query problems
-   Consider using `selectinload` for one-to-many relationships

### 3. Error Handling

-   Use `raise_404_error=True` for API endpoints
-   Handle database exceptions appropriately
-   Validate input data before database operations

### 4. Performance

-   Use pagination for large datasets
-   Use `iterate()` for processing large amounts of data
-   Set `skip_refresh=True` when you don't need the updated object

### 5. Filtering

-   Use `NamedFilterFields` for complex queries
-   Consider creating dedicated methods for common filters
-   Index database columns used in frequent filters

## Integration with FastAPI Routes

```python
from fastapi import APIRouter, Depends
from app.api.deps import DBDep, CurrentUser
from app import crud

router = APIRouter()


@router.get("/{user_id}")
async def get_user(user_id: int, session: DBDep):
    user = await crud.user.get(session, id=user_id, raise_404_error=True)
    return user


@router.post("/")
async def create_user(user_in: UserCreate, session: DBDep):
    user = await crud.user.create(session, obj_in=user_in)
    return user


@router.patch("/{user_id}")
async def update_user(
    user_id: int, user_in: UserUpdate, session: DBDep, current_user: CurrentUser
):
    user = await crud.user.get(session, id=user_id, raise_404_error=True)
    user = await crud.user.update(session, db_obj=user, obj_in=user_in)
    return user
```

## Required Dependencies

The CRUD system requires these core dependencies:

-   **SQLModel**: For database models and operations
-   **SQLAlchemy**: Core database toolkit (async version)
-   **FastAPI**: For HTTP exception handling
-   **Pydantic**: For schema validation

## Notes

-   All operations are asynchronous and require `AsyncSession`
-   The `Base` class must be imported from `app.models`
-   DateTime fields are handled specially in the `create()` method
-   JSON fields use `flag_modified()` for proper change tracking
-   The system automatically excludes certain fields during updates (`id`, `created_on`, `updated_on`)
