from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from auth.auth import decode_jwt
from websocket_manager import get_manager
from typing import Optional
import json
from Database.User_db import UserDB

router = APIRouter()

@router.websocket("/ws")
@router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        # Token'ı doğrula
        try:
            payload = decode_jwt(token)
        except:
            await websocket.close(code=4001)
            return

        user_id = payload.get("user_id")
        if not user_id:
            # user_id yoksa email'den user_id çöz
            email = payload.get("email")
            if email:
                try:
                    user = UserDB().get_user_by_email(email)
                    user_id = user.get("user_id") if user else None
                except Exception:
                    user_id = None
            if not user_id:
                await websocket.close(code=4001)
                return

        # Manager'ı al
        manager = get_manager()
        if not manager:
            await websocket.close(code=4001)
            return

        # Bağlantıyı kabul et
        await manager.connect(websocket, user_id)

        try:
            while True:
                # Mesajı al (metin olarak al ve JSON'a çevir)
                text = await websocket.receive_text()
                if not text:
                    # Boş frame gelirse atla
                    continue
                try:
                    data = json.loads(text)
                except Exception:
                    # JSON değilse atla
                    continue
                print(f"Alınan mesaj: {data}")

                # Mesaj tipine göre işle
                if data.get("type") == "chat_message":
                    print(f"Chat mesajı işleniyor: {data}")
                    await manager.handle_chat_message(websocket, data)
                elif data.get("type") == "typing":
                    print(f"Yazıyor bildirimi işleniyor: {data}")
                    await manager.handle_typing(user_id, data)
                elif data.get("type") == "read_receipt":
                    print(f"Okundu bildirimi işleniyor: {data}")
                    await manager.handle_read_receipt(data.get("chat_id"), data.get("message_id"), user_id)
                elif data.get("type") == "friend_request":
                    print(f"Arkadaşlık isteği işleniyor: {data}")
                    await manager.handle_friend_request(user_id, data)
                elif data.get("type") == "friend_request_response":
                    print(f"Arkadaşlık isteği yanıtı işleniyor: {data}")
                    await manager.handle_friend_request_response(user_id, data)

        except WebSocketDisconnect:
            print(f"WebSocket bağlantısı kapandı: {user_id}")
            manager.disconnect(user_id)
        except Exception as e:
            print(f"WebSocket hatası: {str(e)}")
            print(f"Hata tipi: {type(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            await websocket.close(code=1011)

    except Exception as e:
        print(f"Token doğrulama hatası: {str(e)}")
        await websocket.close(code=4001) 