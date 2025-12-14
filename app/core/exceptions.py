# app/core/exceptions.py

from fastapi import HTTPException, status

class AuthException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "No tiene permisos para realizar esta acción"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

# =======================================================
# 💳 AGREGADA: EXCEPCIÓN PARA LA PASARELA DE PAGOS
# =======================================================
class PaymentGatewayError(Exception):
    """
    Excepción personalizada para manejar errores al comunicarse 
    con pasarelas de pago externas (ej. Libélula).
    """
    def __init__(self, message: str = "Error al comunicarse con la pasarela de pago"):
        self.message = message
        super().__init__(self.message)