from pydantic import BaseModel, Field
from typing import Optional
import datetime
import uuid

class NotificationType:
    FRIEND_REQUEST = "friend_request"
    FRIEND_REQUEST_ACCEPTED = "friend_request_accepted"
    ACTIVITY_INVITATION = "activity_invitation"
    ACTIVITY_UPDATE = "activity_update"
    CHAT_MESSAGE = "chat_message"

class Notification(BaseModel):
    notification_id: str = Field(default_factory=lambda: f"not_{uuid.uuid4().hex[:8]}")
    user_id: str
    type: str
    title: str
    message: str
    data: Optional[dict] = None
    is_read: bool = False
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    read_at: Optional[str] = None 