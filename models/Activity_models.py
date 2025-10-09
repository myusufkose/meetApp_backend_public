from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

#Genel aktivite modeli
class ActivitySchema(BaseModel):
    activity_id: str
    title: str
    activity_date: str 
    max_participants: int
    participants: List[str]
    location: str
    creator_id: str
    created_at:str

#Aktivite oluşturma isteği modeli
class ActivityCreateRequestSchema(BaseModel):
    title: str
    description: Optional[str] = None
    activity_date: str
    max_participants: int = 10 
    location: str

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Proje Toplantısı",
                "description": "Proje Toplantısı hakkında detaylı bilgi",
                "activity_date": "2024-03-25T14:00:00+03:00",
                "max_participants": 10,
                "location": "Toplantı Odası 1"
            }
        }
