# app/schemas/libelula.py

from pydantic import BaseModel, Field
from typing import Optional

# ----------------------------------------------------
# ESQUEMAS PARA INICIAR EL PAGO (Llamado por el router de reservas)
# ----------------------------------------------------

class PaymentInitiation(BaseModel):
    """Datos enviados por tu API a Libélula para iniciar el pago."""
    reserva_id: int = Field(..., description="ID de la reserva que se está pagando (usado como orderId)")
    amount: float = Field(..., gt=0, description="Monto total del pago")
    currency: str = Field("GTQ", description="Moneda (ej: GTQ, USD)")

class PaymentInitiationResponse(BaseModel):
    """Respuesta que tu API devuelve al frontend para la redirección."""
    transaction_id: str = Field(..., description="ID de la transacción devuelto por Libélula")
    payment_url: str = Field(..., description="URL a la que el usuario debe ser redirigido")
    status: str = Field(..., description="Estado inicial de la transacción (ej: PENDING)")


# ----------------------------------------------------
# ESQUEMA CRÍTICO PARA EL WEBHOOK (Donde ocurre el error 422)
# ----------------------------------------------------

class WebhookData(BaseModel):
    """
    Datos recibidos desde el servidor de Libélula para notificar un cambio de estado.
    IMPORTANTE: Verifica si Libélula usa snake_case (transaction_id) o camelCase (transactionId)
    """
    # Si Libélula usa snake_case (lo más fácil):
    transaction_id: str = Field(..., description="ID de la transacción")
    status: str = Field(..., description="Estado final (COMPLETED, FAILED, etc.)")
    amount: float = Field(..., description="Monto final pagado")
    
    # Opcional: Si Libélula envía el orderId
    order_id: Optional[str] = Field(None, description="El ID de la reserva original") 
    
    # Si Libélula usa camelCase, DEBES USAR alias:
    # transaction_id: str = Field(..., alias="transactionId")
    # status: str = Field(..., alias="status")
    
    # Si necesitas validar la firma del webhook:
    # signature: Optional[str] = Field(None, description="Firma para verificación de seguridad")
    
    class Config:
        # Permite recibir campos adicionales en la data del webhook que no están definidos aquí
        extra = 'ignore'