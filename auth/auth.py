import Database.database as database
from fastapi import APIRouter
import time
from typing import Dict
import jwt
from decouple import config
import os
from dotenv import load_dotenv
import datetime

# .env dosyasını yükle
load_dotenv()

router = APIRouter()


def token_response(token: str):
    return {
        "AccessToken": token
    }


# app/auth/auth_handler.py

def sign_jwt(user_id: str, email: str, full_name: str) -> Dict[str, str]:
    payload = {
        "user_id": user_id,
        "email": email,
        "full_name": full_name,
        "expires": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
    }
    token = jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm=os.getenv("JWT_ALGORITHM"))
    return token_response(token)


def decode_jwt(token: str) -> dict:
    try:
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        decoded_token = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=[os.getenv("JWT_ALGORITHM")])
        expires = datetime.datetime.fromisoformat(decoded_token["expires"])
        return decoded_token if expires >= datetime.datetime.now() else None
    except:
        return None
