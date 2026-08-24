"""Request and response shapes for the throwaway demo session.

The role a caller picks here is the whole of the demo's configuration. It
decides two things at once: the ``EventMembership`` row the guest gets, and
therefore which half of the application they can see at all — ``member`` hides
every management screen behind ``requiresEventManager``, ``owner`` opens them.
"""

import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.auth import TokenResponse

SandboxRole = Literal["helper", "manager"]


class SandboxCreate(BaseModel):
    """Ask for a demo session.

    Deliberately tiny and entirely anonymous: no address, no password, nothing
    to verify. The language is carried so the seeded event reads in the same
    language as the page the visitor clicked from — a German landing page that
    opens an English demo is a jarring first impression.
    """

    role: SandboxRole = Field(
        default="helper",
        description=(
            "'helper' joins the demo event as a member and sees the volunteer "
            "side; 'manager' owns it and sees the organiser side"
        ),
    )
    language: Literal["en", "de"] = Field(
        default="en", description="UI language the visitor is currently reading"
    )


class SandboxSessionResponse(TokenResponse):
    """A real signed-in session, pointed at a demo that will not outlive the day.

    Extends the normal login response rather than inventing a parallel one, so
    the client installs it through exactly the same code path — the demo is not
    a special rendering mode, it is an ordinary session that happens to belong
    to a guest.
    """

    event_id: uuid.UUID = Field(
        ..., description="The seeded event, already set as the guest's selection"
    )
    role: SandboxRole = Field(..., description="Which side of the app was requested")
    expires_at: dt.datetime = Field(
        ...,
        description=(
            "Naive UTC instant at which the sweep may purge this demo. The "
            "banner counts down to it; the server does not enforce it early."
        ),
    )
