# API Routes

This directory is where you should create your FastAPI route modules to organize your application's REST API endpoints.

## Tech Stack

-   **FastAPI** routers and dependency injection
-   **Auth0** auth via `app.api.deps.auth0`
-   **SQLModel + AsyncSession** via `DBDep`
-   **Pydantic** schemas for request/response models

## Route Structure Guidelines

Each route file should follow this structure:

```python
from fastapi import APIRouter, Depends
from app.api.deps import DBDep, auth0

router = APIRouter(prefix="/your-prefix", tags=["your-tag"])


@router.get("/")
async def your_endpoint(session: DBDep, claims: dict = Depends(auth0.require_auth())):
    """Your endpoint description"""
    # Your logic here - user info available in claims dict
    user_id = claims.get("sub")  # Auth0 user ID
    user_email = claims.get("email")  # User email
    pass
```

## Essential Route Files to Create

### `login.py` (Required)

Authentication endpoints for user login and token management.

**Recommended Endpoints:**

### `users.py` (Recommended)

User management endpoints.

**Typical Endpoints:**

- `GET /users/me` - Get current user profile
- `PATCH /users/me` - Update profile
- `PATCH /users/me/password` - Change password
- `POST /users/signup` - User registration
- Admin endpoints for user management (if needed)

### Your Domain-Specific Routes

Create additional route files based on your application's needs:

- `products.py` for e-commerce
- `posts.py` for blog/social features
- `orders.py` for order management
- `analytics.py` for reporting endpoints
- etc.

## Best Practices

### Route Organization

- One route file per logical domain/resource
- Use descriptive prefixes and tags
- Group related endpoints together
- Keep authentication logic in `login.py`

### Authentication Patterns

- Use `claims: dict = Depends(auth0.require_auth())` for authenticated endpoints
- Access user information through the `claims` dict containing Auth0 user data
- Implement proper error handling with HTTPException

### Common Dependencies

- `DBDep` for database operations
- `claims: dict = Depends(auth0.require_auth())` for authenticated routes
- Custom dependencies for specific validation logic

### Response Models

- Define Pydantic models for request/response validation
- Use appropriate HTTP status codes
- Include proper error responses

## Registration

Remember to register your routes in `api/main.py`:

```python
from app.api.routes import login, users, your_routes

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(your_routes.router)
```

This ensures your routes are included in the main application with the API version prefix.
