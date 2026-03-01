"""
SQLModel imports and base classes for the application.

This module provides the base SQLModel class and imports for database models.
"""

from sqlmodel import SQLModel

from .base import Base  # Import the Base model for common fields and functionality
from .user import User

# Import all your models here so they are registered with SQLModel
# Example:
# from .user import User

# from .item import Item

__all__ = [
    "SQLModel",
    "Base",
    "User",
]  # Add all your models to this list for easier imports
