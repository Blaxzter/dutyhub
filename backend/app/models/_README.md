# SQLModels

Uses the [SQLModel](https://sqlmodel.tiangolo.com/) library to define the data models for the application.
Based on [Pydantic](https://pydantic-docs.helpmanual.io/) and [SQLAlchemy](https://www.sqlalchemy.org/), it provides a powerful way to define models that can be used for both data validation and database interaction.

## Tech Stack

-   **SQLModel** models with async SQLAlchemy
-   **Pydantic v2** field validation
-   **PostgreSQL** as the primary database

## Base Model

All models should inherit from the `Base` class which provides common fields:

-   `id`: Primary key with auto-increment
-   `created_at`: Timestamp when the record was created (auto-set on insert)
-   `updated_at`: Timestamp when the record was last updated (auto-set on insert/update)

For models that need soft delete functionality, inherit from `SoftDeleteBase` instead.

## Example Model Structure

```python
from app.models.base import Base
from sqlmodel import Field


class User(Base, table=True):
    """Example user model inheriting from Base."""

    __tablename__ = "users"

    email: str = Field(index=True, unique=True, description="User's email address")
    name: str = Field(description="User's full name")
    is_active: bool = Field(
        default=True, description="Whether the user account is active"
    )
```

## Model Patterns

### Standard Model

Inherit from `Base` for models with automatic timestamps:

```python
from app.models.base import Base


class MyModel(Base, table=True):
    __tablename__ = "my_model"

    field_name: str = Field(description="Field description")
```

### Soft Delete Model

Inherit from `SoftDeleteBase` for models that need soft delete functionality:

```python
from app.models.base import SoftDeleteBase


class MyModel(SoftDeleteBase, table=True):
    __tablename__ = "my_model"

    field_name: str = Field(description="Field description")
```
