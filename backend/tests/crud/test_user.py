"""Unit tests for User CRUD operations."""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import user as crud_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


@pytest.mark.asyncio
class TestUserCRUD:
    """Test suite for User CRUD operations."""

    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a new user."""
        user_in = UserCreate(
            subject="local|newuser789",
            email="newuser@example.com",
            name="New User",
            roles=["user"],
            is_active=True,
        )
        user = await crud_user.create(db_session, obj_in=user_in)

        assert user.subject == "local|newuser789"
        assert user.email == "newuser@example.com"
        assert user.name == "New User"
        assert user.roles == ["user"]
        assert user.is_active is True
        assert user.id is not None

    async def test_get_user(self, db_session: AsyncSession, test_user: User):
        """Test getting a user by ID."""
        user = await crud_user.get(db_session, id=test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    async def test_get_user_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent user without raising error."""
        import uuid

        fake_id = uuid.uuid4()
        user = await crud_user.get(db_session, id=fake_id)

        assert user is None

    async def test_get_user_not_found_with_error(self, db_session: AsyncSession):
        """Test getting a non-existent user with raise_404_error=True."""
        import uuid

        fake_id = uuid.uuid4()
        with pytest.raises(HTTPException) as exc_info:
            await crud_user.get(db_session, id=fake_id, raise_404_error=True)

        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    async def test_get_user_by_subject(self, db_session: AsyncSession, test_user: User):
        """Test getting a user by their opaque local identity string."""
        user = await crud_user.get_by_subject(db_session, subject=test_user.subject)

        assert user is not None
        assert user.id == test_user.id
        assert user.subject == test_user.subject

    async def test_get_user_by_subject_not_found(self, db_session: AsyncSession):
        """Test getting a user by a subject nobody holds."""
        user = await crud_user.get_by_subject(db_session, subject="local|nonexistent")

        assert user is None

    async def test_get_user_by_email(self, db_session: AsyncSession, test_user: User):
        """Test getting a user by email."""
        assert test_user.email is not None
        user = await crud_user.get_by_email(db_session, email=test_user.email)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    async def test_get_user_by_email_is_case_insensitive(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that the address is matched however the caller happened to type it.

        Email is the login credential now. Nobody types their own address the
        same way twice, and a case-sensitive lookup would turn
        ``Test@Example.com`` into "no such account" — which the login form can
        only render as "wrong password". The comparison is on ``lower(email)``,
        which is also the expression the partial unique index is built on, so
        this stays an index lookup rather than a sequential scan.
        """
        assert test_user.email is not None
        user = await crud_user.get_by_email(db_session, email=test_user.email.upper())

        assert user is not None
        assert user.id == test_user.id

    async def test_get_user_by_email_ignores_surrounding_whitespace(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that a pasted address with stray spaces still resolves."""
        assert test_user.email is not None
        user = await crud_user.get_by_email(db_session, email=f"  {test_user.email}  ")

        assert user is not None
        assert user.id == test_user.id

    async def test_get_user_by_email_not_found(self, db_session: AsyncSession):
        """Test getting a user by non-existent email."""
        user = await crud_user.get_by_email(db_session, email="nonexistent@example.com")

        assert user is None

    async def test_get_user_by_email_never_matches_a_null_address(
        self, db_session: AsyncSession
    ):
        """Test that rows with no address are invisible to the credential lookup.

        ``email`` is nullable — demo accounts and anything predating local
        authentication may have none — and a NULL address is not a credential.
        The empty string is the value most likely to be posted at this function
        by a form that submitted a blank field.
        """
        no_email = User(subject="demo|no-email", email=None, name="No Email")
        db_session.add(no_email)
        await db_session.flush()

        assert await crud_user.get_by_email(db_session, email="") is None

    async def test_get_multi_users(
        self, db_session: AsyncSession, test_user: User, test_admin_user: User
    ):
        """Test getting multiple users."""
        users = await crud_user.get_multi(db_session, skip=0, limit=10)

        assert len(users) == 2
        user_ids = [user.id for user in users]
        assert test_user.id in user_ids
        assert test_admin_user.id in user_ids

    async def test_get_multi_with_pagination(
        self, db_session: AsyncSession, test_user: User, test_admin_user: User
    ):
        """Test pagination in get_multi."""
        # Get first page
        users_page1 = await crud_user.get_multi(db_session, skip=0, limit=1)
        assert len(users_page1) == 1

        # Get second page
        users_page2 = await crud_user.get_multi(db_session, skip=1, limit=1)
        assert len(users_page2) == 1

        # Ensure different users
        assert users_page1[0].id != users_page2[0].id

    async def test_update_user(self, db_session: AsyncSession, test_user: User):
        """Test updating a user."""
        user_update = UserUpdate(
            name="Updated Name",
            email="updated@example.com",
        )
        updated_user = await crud_user.update(
            db_session, db_obj=test_user, obj_in=user_update
        )

        assert updated_user.id == test_user.id
        assert updated_user.name == "Updated Name"
        assert updated_user.email == "updated@example.com"
        assert updated_user.subject == test_user.subject  # Unchanged

    async def test_update_user_roles(self, db_session: AsyncSession, test_user: User):
        """Test updating user roles."""
        user_update = UserUpdate(roles=["admin", "moderator"])
        updated_user = await crud_user.update(
            db_session, db_obj=test_user, obj_in=user_update
        )

        assert updated_user.roles == ["admin", "moderator"]

    async def test_update_user_is_active(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test deactivating a user."""
        user_update = UserUpdate(is_active=False)
        updated_user = await crud_user.update(
            db_session, db_obj=test_user, obj_in=user_update
        )

        assert updated_user.is_active is False

    async def test_update_user_partial(self, db_session: AsyncSession, test_user: User):
        """Test partial update (only specified fields)."""
        original_email = test_user.email
        user_update = UserUpdate(name="New Name Only")
        updated_user = await crud_user.update(
            db_session, db_obj=test_user, obj_in=user_update
        )

        assert updated_user.name == "New Name Only"
        assert updated_user.email == original_email  # Unchanged

    async def test_remove_user(self, db_session: AsyncSession, test_user: User):
        """Test removing a user."""
        user_id = test_user.id
        removed_user = await crud_user.remove(db_session, id=user_id)

        assert removed_user is not None
        assert removed_user.id == user_id

        # Verify user is deleted
        user = await crud_user.get(db_session, id=user_id)
        assert user is None

    async def test_remove_user_not_found(self, db_session: AsyncSession):
        """Test removing a non-existent user."""
        import uuid

        fake_id = uuid.uuid4()
        removed_user = await crud_user.remove(db_session, id=fake_id)

        assert removed_user is None

    async def test_get_count(
        self, db_session: AsyncSession, test_user: User, test_admin_user: User
    ):
        """Test getting total count of users."""
        count = await crud_user.get_count(db_session)
        assert count == 2

    async def test_user_is_admin_property(
        self, db_session: AsyncSession, test_user: User, test_admin_user: User
    ):
        """Test the is_admin property."""
        assert test_user.is_admin is False
        assert test_admin_user.is_admin is True
