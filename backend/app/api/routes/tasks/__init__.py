from fastapi import APIRouter

from app.api.routes.tasks.batches import router as batches_router
from app.api.routes.tasks.crud import router as crud_router
from app.api.routes.tasks.feed import router as feed_router
from app.api.routes.tasks.slots import router as slots_router

router = APIRouter(prefix="/tasks", tags=["tasks"])

router.include_router(feed_router)
router.include_router(crud_router)
router.include_router(slots_router)
router.include_router(batches_router)
