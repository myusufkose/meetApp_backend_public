from typing import Dict, Any, Optional
from bson import ObjectId

def get_user_details(user_id: str, db) -> Dict[str, Any]:
    """
    Kullanıcı detaylarını getirir
    """
    try:
        users = db.get_all_users()
        for user in users:
            if user.get("user_id") == user_id and not user.get("is_deleted", False):
                # Hassas bilgileri çıkar
                user_details = {
                    "user_id": user.get("user_id"),
                    "email": user.get("email"),
                    "full_name": user.get("full_name"),
                    "friends": user.get("friends", []),
                    "sent_requests": user.get("sent_requests", []),
                    "received_requests": user.get("received_requests", []),
                    "activities": user.get("activities", []),
                    "created_at": user.get("created_at")
                }
                return user_details
        return None
    except Exception as e:
        raise Exception(f"Kullanıcı detayları getirilirken hata oluştu: {str(e)}")


def _convert_to_json(data):
        """
        MongoDB'den gelen verileri JSON'a dönüştürür.
        ObjectId'leri string'e çevirir.
        """
        if isinstance(data, list):
            return [_convert_to_json(item) for item in data]
        elif isinstance(data, dict):
            return {key: _convert_to_json(value) for key, value in data.items()}
        elif isinstance(data, ObjectId):
            return str(data)
        return data