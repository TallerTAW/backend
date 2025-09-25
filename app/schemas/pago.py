from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PagoBase(BaseModel):
    monto: float
    metodo_pago: str
    id_reserva: int

class PagoCreate(PagoBase):
    pass

class PagoUpdate(BaseModel):
    estado: Optional[str] = None
    id_transaccion: Optional[str] = None

class PagoResponse(PagoBase):
    id_pago: int
    estado: str
    id_transaccion: Optional[str] = None
    fecha_pago: datetime
    
    class Config:
        from_attributes = True