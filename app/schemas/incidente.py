from pydantic import BaseModel, condecimal, Field
from typing import Optional
from datetime import datetime

class IncidenteBase(BaseModel):
    tipo: str = Field(..., max_length=50)
    descripcion: str
    multa: Optional[condecimal(max_digits=10, decimal_places=2)] = 0
    id_reserva: Optional[int] = None
    id_usuario: int

class IncidenteCreate(IncidenteBase):
    pass

class IncidenteUpdate(BaseModel):
    tipo: Optional[str] = None
    descripcion: Optional[str] = None
    multa: Optional[condecimal(max_digits=10, decimal_places=2)] = None

class IncidenteResponse(IncidenteBase):
    id_incidente: int
    fecha_incidente: datetime

    class Config:
        from_attributes = True