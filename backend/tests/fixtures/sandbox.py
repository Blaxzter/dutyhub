"""Fixtures for the throwaway demo behind the "try a test event" button.

A sandbox is not a shape a test can sensibly hand-roll. It is an event, five
teammate accounts, four tasks each with a batch and a stored generation config,
a few dozen shifts spread either side of today, bookings on most of them,
availabilities, an auth session — and, for the manager variant, a pending
invitation and a pending join request. Rebuilding a plausible subset of that by
hand would test the subset rather than the feature, and the failure this whole
area exists to prevent is precisely a row *shape* nobody remembered to
recreate: an orphaned task, a booking with no shift, a guest account left
behind.

So the factory below mints a real one through ``logic.sandbox.service`` — the
same call ``POST /auth/sandbox`` makes, with the same seeder behind it. Tests
then assert against what production actually produced.

Nothing here commits. ``db_session`` is savepoint-wrapped like everywhere else
in the suite, so a seeded demo disappears with the test that asked for it.
"""

from dataclasses import dataclass
from typing import Protocol

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.logic.auth.service import SignedInSession
from app.logic.sandbox.service import create_sandbox
from app.models.event import Event
from app.models.user import User
from app.schemas.sandbox import SandboxRole


@dataclass(frozen=True, slots=True)
class SandboxSetup:
    """One seeded demo, as the route would have handed it out.

    ``guest`` is the account that owns the event — the only account allowed to
    see it. ``session`` carries the credential pair, so a test can present the
    demo's own access token instead of overriding an identity dependency.
    """

    event: Event
    guest: User
    session: SignedInSession


class SandboxFactory(Protocol):
    """Mints a demo of the requested role and language."""

    async def __call__(
        self, *, role: SandboxRole = "helper", language: str = "en"
    ) -> SandboxSetup: ...


@pytest_asyncio.fixture
async def make_sandbox(db_session: AsyncSession) -> SandboxFactory:
    """Return a factory for seeded demos.

    A factory rather than a plain fixture because several tests need *two* —
    the ceiling, the sweep and "one guest cannot see another's demo" are all
    statements about a second sandbox existing alongside the first.
    """

    async def _make(
        *, role: SandboxRole = "helper", language: str = "en"
    ) -> SandboxSetup:
        signed_in, event = await create_sandbox(
            db_session, role=role, language=language
        )
        return SandboxSetup(event=event, guest=signed_in.user, session=signed_in)

    return _make


@pytest_asyncio.fixture
async def test_sandbox(make_sandbox: SandboxFactory) -> SandboxSetup:
    """A helper-role demo: the guest is a plain ``member`` of their event.

    There is deliberately no ``test_manager_sandbox`` counterpart. Seeding the
    manager variant currently raises (see the xfails in
    ``tests/logic/test_sandbox_seed.py``), and a fixture that raises produces a
    setup *error*, which no ``xfail`` marker can absorb — the tests that need
    that variant call ``make_sandbox(role="manager")`` in their own body so the
    marker applies.
    """
    return await make_sandbox(role="helper")
