from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from auth.auth import decode_jwt
from websocket_manager import get_manager
from typing import Optional
import json

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
            await websocket.close(code=4001)
            return

        # Manager'ı al
        manager = get_manager()
        if not manager:
            await websocket.close(code=4001)
            return

        # Bağlantıyı kabul et
        await manager.connect(websocket, user_id)
        print(f"Yeni WebSocket bağlantısı: {user_id}")

        try:
            while True:
                # Mesajı al
                data = await websocket.receive_json()
                print(f"Alınan mesaj: {data}")

                # Mesaj tipine göre işle
                if data["type"] == "chat_message":
                    print(f"Chat mesajı işleniyor: {data}")
                    await manager.handle_chat_message(websocket, data)
                elif data["type"] == "typing":
                    print(f"Yazıyor bildirimi işleniyor: {data}")
                    await manager.handle_typing(user_id, data)
                elif data["type"] == "read_receipt":
                    print(f"Okundu bildirimi işleniyor: {data}")
                    await manager.handle_read_receipt(user_id, data)
                elif data["type"] == "friend_request":
                    print(f"Arkadaşlık isteği işleniyor: {data}")
                    await manager.handle_friend_request(user_id, data)
                elif data["type"] == "friend_request_response":
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