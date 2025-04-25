from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid

class MessageStatus(BaseModel):
    """
    Mesaj durumu modeli
    """
    read_by: List[str] = []
    delivered_to: List[str] = []

    @property
    def is_delivered(self) -> bool:
        return len(self.delivered_to) > 0

    @property
    def is_read(self) -> bool:
        return len(self.read_by) > 0

    def dict(self, **kwargs) -> Dict[str, Any]:
        return {
            "read_by": self.read_by,
            "delivered_to": self.delivered_to
        }

class MessageContent(BaseModel):
    """
    Mesaj içeriği modeli
    """
    type: str = "text"
    text: Optional[str] = None
    content: Optional[str] = None

    @validator('text')
    def validate_text(cls, v, values):
        if values.get('type') == 'text' and not v:
            raise ValueError('Text message must have text content')
        return v

    @validator('content')
    def validate_content(cls, v, values):
        if values.get('type') != 'text' and not v:
            raise ValueError('Non-text message must have content')
        return v

    def __init__(self, **data):
        # Eğer text verilmişse content'i de aynı değere ayarla
        if 'text' in data and 'content' not in data:
            data['content'] = data['text']
        super().__init__(**data)

    def dict(self, **kwargs) -> Dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text,
            "content": self.content
        }

class Message(BaseModel):
    """
    Chat mesajı modeli
    """
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    chat_id: str
    sender_id: str
    content: MessageContent
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: MessageStatus = Field(default_factory=MessageStatus)
    is_deleted: bool = False
    edited: bool = False
    reply_to: Optional[str] = None  # Yanıtlanan mesajın ID'si

    def __init__(self, **data):
        print(f"\n=== Message modeli oluşturuluyor ===")
        print(f"Gelen veri: {data}")
        try:
            # Eğer data boşsa veya content yoksa, varsayılan değerler kullan
            if not data or not data.get('content'):
                data['content'] = MessageContent(type="text", text="", content="")
            super().__init__(**data)
            print(f"Message modeli başarıyla oluşturuldu: {self.dict()}")
        except Exception as e:
            print(f"Message modeli oluşturma hatası: {str(e)}")
            print(f"Hata tipi: {type(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            raise

    def dict(self, **kwargs) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "sender_id": self.sender_id,
            "content": self.content.dict(),
            "timestamp": self.timestamp,
            "status": self.status.dict(),
            "is_deleted": self.is_deleted,
            "edited": self.edited,
            "reply_to": self.reply_to
        }

class Chat(BaseModel):
    """
    Chat modeli
    """
    chat_id: str = Field(default_factory=lambda: f"chat_{uuid.uuid4().hex[:8]}")
    participants: List[str]
    participants_info: Optional[List[Dict[str, str]]] = None
    is_group: bool = False
    group_name: Optional[str] = None
    group_picture: Optional[str] = None
    group_admin: Optional[str] = None
    messages: List[Message] = []
    last_message: Optional[Dict[str, Any]] = None
    unread_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True

    def __init__(self, **data):
        print(f"\n=== Chat modeli oluşturuluyor ===")
        print(f"Gelen veri: {data}")
        try:
            # Eğer last_message boşsa, None olarak ayarla
            if data.get('last_message') == {}:
                data['last_message'] = None
            super().__init__(**data)
            print(f"Chat modeli başarıyla oluşturuldu: {self.dict()}")
        except Exception as e:
            print(f"Chat modeli oluşturma hatası: {str(e)}")
            print(f"Hata tipi: {type(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            raise

    def dict(self, **kwargs) -> Dict[str, Any]:
        return {
            "chat_id": self.chat_id,
            "participants": self.participants,
            "participants_info": self.participants_info,
            "is_group": self.is_group,
            "group_name": self.group_name,
            "group_picture": self.group_picture,
            "group_admin": self.group_admin,
            "messages": [msg.dict() for msg in self.messages],
            "last_message": self.last_message,
            "unread_count": self.unread_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active
        }

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CreateNewChat(BaseModel):
    """
    Yeni sohbet oluşturma modeli
    """
    participants: List[str]
    is_group: bool = False
    group_name: Optional[str] = None
    group_admin: Optional[str] = None
