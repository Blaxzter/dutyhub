import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.event_group_manager import event_group_manager as crud_egm
from app.models.user import User


async def require_event_group_access(
    user: User,
    session: AsyncSession,
    event_group_id: uuid.UUID | None,
) -> None:
    """Raise 403 unless the user has access to manage the given task group.

    Access is granted when ANY of these is true:
    - user.is_admin (global admin)
    - user.is_task_manager (global task_manager role)
    - user is an assigned manager of this specific event_group_id

    If event_group_id is None (task not part of any group), only admins and
    global task_managers may manage it — scoped group managers cannot.
    """
    if user.is_admin or user.is_task_manager:
        return

    if event_group_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    is_group_manager = await crud_egm.is_manager(
        session,
        user_id=user.id,
        event_group_id=event_group_id,
    )
    if not is_group_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
