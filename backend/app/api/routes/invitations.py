"""Redeeming an event invitation.

Kept off ``/events/{id}`` on purpose: the holder of a token should not need to
know — or be able to guess — the event id before accepting, and a private
event must stay 404 to them until the token proves they were invited.
"""

from fastapi import APIRouter, BackgroundTasks

from app.api.deps import CurrentUser, DBDep
from app.core.errors import raise_problem
from app.crud.event import event as crud_event
from app.crud.event_invitation import event_invitation as crud_invitation
from app.crud.event_invitation import invitation_invalid_reason
from app.crud.event_membership import event_membership as crud_membership
from app.crud.user import user as crud_user
from app.schemas.event import EventRead
from app.schemas.event_invitation import EventInvitationPreview

router = APIRouter(prefix="/invitations", tags=["invitations"])


def _email_matches(invitation_email: str | None, user_email: str | None) -> bool:
    """Whether a targeted invitation was addressed to this user.

    A link invitation (no address) matches everyone.
    """
    if invitation_email is None:
        return True
    if not user_email:
        return False
    return invitation_email.lower() == user_email.lower()


@router.get("/{token}", response_model=EventInvitationPreview)
async def preview_invitation(
    token: str,
    session: DBDep,
    current_user: CurrentUser,
) -> EventInvitationPreview:
    """What this token grants, so the invitee can decide before accepting.

    Returns 404 for an unknown token, but a *known* token that is expired or
    revoked still resolves — the invitee deserves to be told which it was
    rather than staring at a dead link.
    """
    invitation = await crud_invitation.get_by_token(session, token=token)
    if not invitation:
        raise_problem(
            404,
            code="invitation.not_found",
            detail="This invitation link is not valid",
        )

    db_event = await crud_event.get(session, invitation.event_id)
    if not db_event:
        raise_problem(
            404,
            code="invitation.event_gone",
            detail="The event this invitation points to no longer exists",
        )

    reason = invitation_invalid_reason(invitation)
    if reason is None and not _email_matches(invitation.email, current_user.email):
        reason = "email_mismatch"

    inviter_name: str | None = None
    if invitation.invited_by_id:
        inviter = await crud_user.get(session, id=invitation.invited_by_id)
        inviter_name = inviter.name if inviter else None

    already_member = (
        await crud_membership.get(
            session, user_id=current_user.id, event_id=db_event.id
        )
        is not None
    )

    return EventInvitationPreview(
        event_id=db_event.id,
        event_name=db_event.name,
        event_description=db_event.description,
        start_date=db_event.start_date,
        end_date=db_event.end_date,
        role=invitation.role,  # type: ignore[arg-type]
        invited_by_name=inviter_name,
        is_valid=reason is None,
        invalid_reason=reason,
        already_member=already_member,
    )


@router.post("/{token}/accept", response_model=EventRead)
async def accept_invitation(
    token: str,
    session: DBDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> EventRead:
    """Redeem an invitation and join the event."""
    invitation = await crud_invitation.get_by_token(session, token=token)
    if not invitation:
        raise_problem(
            404,
            code="invitation.not_found",
            detail="This invitation link is not valid",
        )

    reason = invitation_invalid_reason(invitation)
    if reason is not None:
        raise_problem(
            410,
            code=f"invitation.{reason}",
            detail="This invitation can no longer be used",
        )
    if not _email_matches(invitation.email, current_user.email):
        raise_problem(
            403,
            code="invitation.email_mismatch",
            detail="This invitation was sent to a different email address",
        )

    db_event = await crud_event.get(session, invitation.event_id)
    if not db_event:
        raise_problem(
            404,
            code="invitation.event_gone",
            detail="The event this invitation points to no longer exists",
        )

    existing = await crud_membership.get(
        session, user_id=current_user.id, event_id=db_event.id
    )
    if existing is None:
        await crud_membership.upsert(
            session,
            user_id=current_user.id,
            event_id=db_event.id,
            role=invitation.role,  # type: ignore[arg-type]
        )
        await crud_invitation.mark_redeemed(
            session, invitation=invitation, user_id=current_user.id
        )

        from app.logic.notifications.triggers import dispatch_event_invitation_accepted

        background_tasks.add_task(
            dispatch_event_invitation_accepted,
            event_id=db_event.id,
            user_id=current_user.id,
        )

    # An accepted invitation supersedes any request the user had pending.
    from app.crud.event_join_request import event_join_request as crud_join_request

    await crud_join_request.delete_for_user(
        session, user_id=current_user.id, event_id=db_event.id
    )

    from app.api.routes.events import decorate_event

    return await decorate_event(session, current_user, db_event)
