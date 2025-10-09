# app/auth/auth_bearer.py

from fastapi import Request, HTTPException
import time
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.auth import decode_jwt


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        start_time = time.perf_counter()
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        try:
            if credentials:
                if not credentials.scheme == "Bearer":
                    raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
                # Decode once and attach payload to request for downstream usage
                payload = decode_jwt(credentials.credentials)
                if not payload:
                    raise HTTPException(status_code=403, detail="Invalid token or expired token.")
                request.state.user = payload
                return payload
            else:
                raise HTTPException(status_code=403, detail="Invalid authorization code.")
        finally:
            end_time = time.perf_counter()
            duration_seconds = end_time - start_time
            #print(f"[auth] JWTBearer __call__ süresi: {duration_seconds:.6f} saniye")

    def verify_jwt(self, jwtoken: str) -> bool:
        isTokenValid: bool = False
        try:
            payload = decode_jwt(jwtoken)
        except:
            payload = None
        if payload:
            isTokenValid = True
        return isTokenValid
