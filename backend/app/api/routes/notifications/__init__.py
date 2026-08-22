from fastapi import APIRouter

from app.api.routes.notifications.feed import router as feed_router
from app.api.routes.notifications.preferences import router as preferences_router
from app.api.routes.notifications.push import router as push_router
from app.api.routes.notifications.telegram import router as telegram_router
from app.api.routes.notifications.types import router as types_router

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Order matters. `feed_router` owns the catch-all single-segment routes
# `DELETE /{notification_id}` and `PATCH /{notification_id}/read`, and FastAPI
# matches in registration order — so a literal sibling route registered after it
# becomes unreachable. Registering feed LAST keeps every literal path reachable
# and makes future additions safe by default.
#
# This was a live bug: `DELETE /notifications/telegram` (the "Disconnect
# Telegram" button) matched `DELETE /{notification_id}` with
# notification_id="telegram" and returned 500 on an invalid-UUID cast.
router.include_router(types_router)
router.include_router(preferences_router)
router.include_router(push_router)
router.include_router(telegram_router)
router.include_router(feed_router)
