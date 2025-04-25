from fastapi import HTTPException, status

class DatabaseError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Kimlik doğrulama başarısız"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )

class ValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )

class NotFoundError(HTTPException):
    def __init__(self, detail: str = "Kayıt bulunamadı"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

class DuplicateError(HTTPException):
    def __init__(self, detail: str = "Bu kayıt zaten mevcut"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        ) 