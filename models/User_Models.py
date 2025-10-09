from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import uuid
from enum import Enum

class Friend_Request_Status(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class Friend_Request_Model(BaseModel):
    from_user_id: str
    to_user_id: str
    status: Friend_Request_Status = Friend_Request_Status.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    
class User_Model(BaseModel):
    user_id: str = Field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:8]}")
    profile_picture: Optional[str] = ""
    name: str
    email: str
    password_hash: str
    friends: List[str] = []
    friend_requests_sent: List[Friend_Request_Model] = []
    friend_requests_received: List[Friend_Request_Model] = []
    friend_requests_rejected: List[Friend_Request_Model] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_deleted: bool = False
     
class User_Create_Model(BaseModel):
    name: str
    email: str
    password: str
    profile_picture: Optional[str] = ""
    
class User_Login_Model(BaseModel):
    email: str
    password: str
    
class Friend_Request_Data_Model(BaseModel):
    from_user_id: str
    to_user_id: str
    status: Friend_Request_Status = Friend_Request_Status.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    