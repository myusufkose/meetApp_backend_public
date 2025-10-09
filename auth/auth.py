from Database.User_db import UserDB
from fastapi import APIRouter
import time
from typing import Dict
import jwt
from decouple import config
import os
from dotenv import load_dotenv
import datetime
from passlib.context import CryptContext

# .env dosyasını yükle
load_dotenv()

router = APIRouter()

# Şifre hashleme için context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

User_db = UserDB()


def token_response(token: str):
    return {
        "AccessToken": token
    }


def hash_password(password: str) -> str:
    """
    Şifreyi hashle
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Şifreyi doğrula
    """
    return pwd_context.verify(plain_password, hashed_password)


# app/auth/auth_handler.py

def sign_jwt(name: str, email: str, user_id: str) -> Dict[str, str]:
    payload = {
        "name": name,
        "email": email,
        "expires": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
    }
    if user_id:
        payload["user_id"] = user_id
    token = jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm=os.getenv("JWT_ALGORITHM"))
    return token_response(token)


def decode_jwt(token: str) -> dict:
    #start_time = time.perf_counter()
    try:
        # Bearer prefix ayıklama
        #t_strip_start = time.perf_counter()
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        #t_strip_end = time.perf_counter()
        #print(f"[auth] decode_jwt step=strip_bearer duration={(t_strip_end - t_strip_start):.6f}s")

        # Exp kontrolü PyJWT tarafından otomatik yapılmasın; iki farklı alanı kendimiz yöneteceğiz
        #t_decode_start = time.perf_counter()
        decoded_token = jwt.decode(
            token,
            os.getenv("JWT_SECRET"),
            algorithms=[os.getenv("JWT_ALGORITHM")],
            options={"verify_exp": False}
        )
        #t_decode_end = time.perf_counter()
        #print(f"[auth] decode_jwt step=jwt_decode duration={(t_decode_end - t_decode_start):.6f}s")

        # expires parse ve kontrol
        #t_exp_start = time.perf_counter()
        try:
            exp_iso = datetime.datetime.fromisoformat(decoded_token["expires"])
        except Exception:
            return None
        if exp_iso < datetime.datetime.now():
            return None
        #t_exp_end = time.perf_counter()
        #print(f"[auth] decode_jwt step=parse_expires duration={(t_exp_end - t_exp_start):.6f}s")

        # Kullanıcının silinip silinmediğini kontrol et
        #t_db_init_start = time.perf_counter()
        db = User_db
        #t_db_init_end = time.perf_counter()
        #print(f"[auth] decode_jwt step=db_init duration={(t_db_init_end - t_db_init_start):.6f}s")
        user_email = decoded_token.get("email")
        if user_email:
            #t_db_query_start = time.perf_counter()
            is_active = db.is_user_active(user_email)
            #t_db_query_end = time.perf_counter()
            #print(f"[auth] decode_jwt step=db_is_user_active duration={(t_db_query_end - t_db_query_start):.6f}s")
            if not is_active:
                return None
                
        return decoded_token
    except:
        return None
    finally:
        pass
        #end_time = time.perf_counter()
        #duration_seconds = end_time - start_time
        #print(f"[auth] decode_jwt step=total duration={duration_seconds:.6f}s")
