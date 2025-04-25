import Database.database as database
from fastapi import APIRouter, Body, Depends, HTTPException, status
from auth.auth_bearer import JWTBearer
from models.model import ActivityCreateSchema, ActivityResponseSchema
from exceptions import DatabaseError, NotFoundError, DuplicateError, AuthenticationError
from typing import List, Dict, Any
import uuid
import jwt
from datetime import datetime
import os
from auth.auth import decode_jwt

router = APIRouter()
db = database.Database()

secret = os.getenv("JWT_SECRET")
algorithm = os.getenv("JWT_ALGORITHM")

@router.get("/activities", response_model=List[ActivityResponseSchema])
async def get_all_activities():
    try:
        activities = db.get_all_activities()
        # Tarih alanlarını kontrol et ve dönüştür
        for activity in activities:
            if "created_at" in activity:
                if isinstance(activity["created_at"], datetime):
                    activity["created_at"] = activity["created_at"].isoformat()
            if "activity_date" in activity:
                if isinstance(activity["activity_date"], datetime):
                    activity["activity_date"] = activity["activity_date"].isoformat()
        return activities
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@router.get("/activities/{activity_id}", response_model=ActivityResponseSchema)
async def get_activity(activity_id: str):
    try:
        activity = db.get_activity_by_id(activity_id)
        if not activity:
            raise NotFoundError("Aktivite bulunamadı")
            
        # Tarih alanlarını kontrol et ve dönüştür
        if "created_at" in activity:
            if isinstance(activity["created_at"], datetime):
                activity["created_at"] = activity["created_at"].isoformat()
        if "activity_date" in activity:
            if isinstance(activity["activity_date"], datetime):
                activity["activity_date"] = activity["activity_date"].isoformat()
            
        return activity
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@router.post("/activities", response_model=ActivityResponseSchema)
async def create_activity(
    activity: ActivityCreateSchema = Body(...),
    token: str = Depends(JWTBearer())
):
    try:
        # Token'dan user_id'yi al
        decoded_token = decode_jwt(token)
        if not decoded_token or "user_id" not in decoded_token:
            raise AuthenticationError("Geçersiz token")
        
        user_id = decoded_token["user_id"]
        
        # Aktivite verilerini hazırla 
        activity_data = activity.model_dump()
        
        # Backend tarafından atanacak alanları ekle
        activity_data["activity_id"] = str(uuid.uuid4())
        activity_data["created_at"] = datetime.utcnow().isoformat()
        activity_data["creator_id"] = user_id
        
        # Creator'ı katılımcılar listesine ekle
        if user_id not in activity_data["participants"]:
            activity_data["participants"].append(user_id)
        
        # Aktivite tarihini kontrol et
        activity_date = datetime.fromisoformat(activity_data["activity_date"].replace('Z', '+00:00'))
        current_time = datetime.now(activity_date.tzinfo)  # Aynı timezone'u kullan
        
        if activity_date < current_time:
            raise HTTPException(
                status_code=400,
                detail="Aktivite tarihi geçmiş bir tarih olamaz"
            )
        
        # Maksimum katılımcı sayısını kontrol et
        if activity_data["max_participants"] < 1:
            raise HTTPException(
                status_code=400,
                detail="Maksimum katılımcı sayısı en az 1 olmalıdır"
            )
        
        # Aktiviteyi veritabanına ekle
        db.insert_activity(activity_data)
        
        # Eklenen aktiviteyi getir
        created_activity = db.get_activity_by_id(activity_data["activity_id"])
        if not created_activity:
            raise DatabaseError("Aktivite oluşturuldu ancak getirilemedi")
            
        return created_activity
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@router.put("/activities/{activity_id}", response_model=ActivityResponseSchema)
async def update_activity(
    activity_id: str,
    activity: ActivityResponseSchema = Body(...),
    token: str = Depends(JWTBearer())
):
    try:
        # Token'dan user_id'yi al
        decoded_token = decode_jwt(token)
        if not decoded_token or "user_id" not in decoded_token:
            raise AuthenticationError("Geçersiz token")
        
        user_id = decoded_token["user_id"]
        
        # Mevcut aktiviteyi kontrol et
        existing_activity = db.get_activity_by_id(activity_id)
        if not existing_activity:
            raise NotFoundError("Güncellenecek aktivite bulunamadı")
            
        # Aktivite verilerini hazırla
        activity_data = activity.dict(exclude={'activity_id', 'creator_id', 'created_at'})
        activity_data["activity_id"] = activity_id  # ID'yi koru
        activity_data["creator_id"] = existing_activity["creator_id"]  # Oluşturan kullanıcıyı koru
        
        # Aktivite tarihini kontrol et
        activity_date = datetime.fromisoformat(activity_data["activity_date"].replace('Z', '+00:00'))
        if activity_date < datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail="Aktivite tarihi geçmiş bir tarih olamaz"
            )
        
        # Maksimum katılımcı sayısını kontrol et
        if activity_data["max_participants"] < 1:
            raise HTTPException(
                status_code=400,
                detail="Maksimum katılımcı sayısı en az 1 olmalıdır"
            )
        
        # Mevcut katılımcı sayısını kontrol et
        if len(existing_activity["participants"]) > activity_data["max_participants"]:
            raise HTTPException(
                status_code=400,
                detail="Maksimum katılımcı sayısı mevcut katılımcı sayısından az olamaz"
            )
        
        # Aktiviteyi güncelle
        db.update_activity(activity_id, activity_data)
        
        # Güncellenmiş aktiviteyi getir
        updated_activity = db.get_activity_by_id(activity_id)
        if not updated_activity:
            raise DatabaseError("Aktivite güncellendi ancak getirilemedi")
            
        return updated_activity
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@router.delete("/activities/{activity_id}")
async def delete_activity(
    activity_id: str,
    token: str = Depends(JWTBearer())
):
    try:
        # Token'dan user_id'yi al
        decoded_token = decode_jwt(token)
        if not decoded_token or "user_id" not in decoded_token:
            raise AuthenticationError("Geçersiz token")
        
        user_id = decoded_token["user_id"]
        
        # Aktiviteyi kontrol et
        activity = db.get_activity_by_id(activity_id)
        if not activity:
            raise NotFoundError("Silinecek aktivite bulunamadı")
            
        # Aktiviteyi sil
        db.delete_activity(activity_id)
        
        return {"message": "Aktivite başarıyla silindi"}
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@router.get("/users/{user_id}/activities", response_model=List[ActivityResponseSchema])
async def get_user_activities(user_id: str):
    try:
        activities = db.get_user_activities(user_id)
        return activities
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")
