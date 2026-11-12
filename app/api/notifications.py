from fastapi import APIRouter, Query, status

from app.api.responses import NOT_FOUND
from app.schemas.notification import NotificationResponse, NotificationUpdate
from app.services import notification_service

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse], summary="List notifications")
def list_notifications(
    is_read: bool | None = Query(default=None, description="false = only unread"),
):
    return notification_service.list_notifications(is_read)


@router.patch(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Mark a notification as read or unread",
    responses=NOT_FOUND,
)
def update_notification(notification_id: int, data: NotificationUpdate):
    return notification_service.set_read(notification_id, data.is_read)


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notification",
    responses=NOT_FOUND,
)
def delete_notification(notification_id: int):
    notification_service.delete_notification(notification_id)
