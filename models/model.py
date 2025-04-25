# app/model.py
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
import uuid


class PostSchema(BaseModel):
    id: Optional[int] = None
    title: str
    content: str

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Securing FastAPI applications with JWT.",
                "content": "In this tutorial, you'll learn how to secure your application by enabling authentication using JWT. We'll be using PyJWT to sign, encode and decode JWT tokens...."
            }
        }

class UserSchema(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Abdulazeez Abdulazeez Adeshina",
                "email": "abdulazeez@x.com",
                "password": "weakpassword"
            }
        }


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "abdulazeez@x.com",
                "password": "weakpassword"
            }
        }


class ActivitySchema(BaseModel):
    activity_id: Optional[str] = None  # Optional because it's generated on creation
    title: str
    activity_date: str  # ISO format string olarak saklanacak
    max_participants: int = 10  # Varsayılan değer 10
    participants: List[str] = []  # Katılımcıların ID listesi
    location: Optional[str] = None  # Aktivitenin yapılacağı mekan
    creator_id: Optional[str] = None  # Aktiviteyi oluşturan kullanıcının ID'si
    created_at: Optional[str] = None  # Aktivitenin oluşturulma tarihi

    class Config:
        json_schema_extra = {
            "example": {
                "activity_id": "act_12345678",
                "title": "Proje Toplantısı",
                "activity_date": "2024-03-25T14:00:00+03:00",
                "max_participants": 10,
                "location": "Toplantı Odası 1",
                "creator_id": "usr_12345678",
                "created_at": "2024-03-20T10:00:00+03:00"
            }
        }

class ActivityCreateSchema(BaseModel):
    title: str
    activity_date: str  # ISO format string olarak saklanacak
    max_participants: int = 10  # Varsayılan değer 10
    participants: List[str] = []  # Katılımcıların ID listesi
    location: Optional[str] = None  # Aktivitenin yapılacağı mekan

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Proje Toplantısı",
                "activity_date": "2024-03-25T14:00:00+03:00",
                "max_participants": 10,
                "location": "Toplantı Odası 1"
            }
        }

class ActivityResponseSchema(BaseModel):
    activity_id: str
    title: str
    activity_date: str
    max_participants: int
    participants: List[str]
    location: Optional[str] = None
    creator_id: str
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "activity_id": "act_12345678",
                "title": "Proje Toplantısı",
                "activity_date": "2024-03-25T14:00:00+03:00",
                "max_participants": 10,
                "location": "Toplantı Odası 1",
                "creator_id": "usr_12345678",
                "created_at": "2024-03-20T10:00:00+03:00"
            }
        }

