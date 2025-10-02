from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CancelacionBase(BaseModel):
    motivo: str = Field(..., min_length=1)
    id_reserva: int
    id_usuario: int

class CancelacionCreate(CancelacionBase):
    pass

class CancelacionUpdate(BaseModel):
    motivo: Optional[str] = Field(None, min_length=1)

class Cancelacion(CancelacionBase):
    id_cancelacion: int
    fecha_cancelacion: datetime

    class Config:
        from_attributes = True