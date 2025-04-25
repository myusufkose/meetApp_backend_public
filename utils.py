from fastapi import HTTPException
from Database.database import Database

def get_user_details(user_id: str, db: Database) -> dict:
    """
    Kullanıcının detaylı bilgilerini getirir.
    
    Args:
        user_id (str): Kullanıcı ID'si
        db: Veritabanı nesnesi
        
    Returns:
        dict: Kullanıcı detayları
        
    Raises:
        HTTPException: Kullanıcı bulunamazsa veya başka bir hata oluşursa
    """
    try:
        # Kullanıcıyı bul
        user_data = None
        users = db.get_all_users()
        for user in users:
            if user["user_id"] == user_id:
                user_data = user
                break
        
        if not user_data:
            raise HTTPException(
                status_code=404,
                detail="Kullanıcı bulunamadı"
            )
            
        # Arkadaş listesini al
        friends_list = user_data.get("friends", [])
        
        # Arkadaşların detaylı bilgilerini topla
        friends_details = []
        for friend_id in friends_list:
            for user in users:
                if user["user_id"] == friend_id:
                    friends_details.append({
                        "user_id": user["user_id"],
                        "full_name": user.get("full_name", ""),
                        "email": user["email"]
                    })
                    break
        
        # Gönderilen isteklerin detaylarını topla
        sent_requests_details = []
        for request_id in user_data.get("sent_requests", []):
            for user in users:
                if user["user_id"] == request_id:
                    sent_requests_details.append({
                        "user_id": user["user_id"],
                        "full_name": user.get("full_name", ""),
                        "email": user["email"]
                    })
                    break
        
        # Alınan isteklerin detaylarını topla
        received_requests_details = []
        for request_id in user_data.get("received_requests", []):
            for user in users:
                if user["user_id"] == request_id:
                    received_requests_details.append({
                        "user_id": user["user_id"],
                        "full_name": user.get("full_name", ""),
                        "email": user["email"]
                    })
                    break
        
        # Kullanıcı aktivitelerini getir
        user_activities = db.get_user_activities(user_id)
        
        return {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "full_name": user_data.get("full_name", ""),
            "friends": friends_details,
            "sent_requests": sent_requests_details,
            "received_requests": received_requests_details,
            "activities": user_activities
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Kullanıcı bilgileri getirilirken hata oluştu: {str(e)}"
        ) 