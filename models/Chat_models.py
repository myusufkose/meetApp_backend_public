from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import uuid

class Message(BaseModel):
    message_id: str
    content: str
    sender_id: str
    timestamp: datetime
    read_by: List[str] = []
    reply_to: Optional[str] = None
    forward_from: Optional[str] = None


class Chat(BaseModel):
    chat_id: str
    messages: List[Message]
    participants: List[str]
    participants_info: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    is_group: bool
    group_name: Optional[str] = None
    group_photo_url: Optional[str] = None
    group_description: Optional[str] = None
    group_admin_ids: List[str] = []
    is_active: bool = True
    last_message: Optional[Message] = None

class CreateNewChat(BaseModel):
    participants: Optional[List[str]] = None
    is_group: bool
    group_name: Optional[str] = None
    message_content: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_message_required(self):
        # Eğer grup chat'i değilse, mesaj zorunlu olmalı
        if not self.is_group and (self.message_content is None or self.message_content.strip() == ""):
            raise ValueError("Message is required for non-group chats")
        return self
    


