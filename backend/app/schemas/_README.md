# Pydantic schemas

This directory contains Pydantic schemas used for request and response validation in the FastAPI application.
Depending on how big your application is, you might want to organize schemas into subdirectories.

## Tech Stack

-   **Pydantic v2** for schema validation
-   **FastAPI** request/response models

## Schema Structure Guidelines

Each schema file should follow this structure:

```python
from pydantic import BaseModel, Field


class YourSchema(BaseModel):
    """Description of your schema"""

    field_name: str = Field(..., description="Description of the field")
    another_field: int = Field(0, description="Another field with a default value")
```

## CRUD Schemas

When you want to use CRUD base python file you need to create "create, read, update" schemas for each model you want to use with it.
