from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, time

class ReservaBase(BaseModel):
    fecha_reserva: date
    hora_inicio: time
    hora_fin: time
    cantidad_asistentes: Optional[int] = None
    material_prestado: Optional[str] = None
    id_cancha: int
    id_disciplina: int
    id_usuario: int  

class ReservaCreate(ReservaBase):
    pass

class ReservaUpdate(BaseModel):
    estado: Optional[str] = None
    material_prestado: Optional[str] = None
    cantidad_asistentes: Optional[int] = None

class ReservaResponse(ReservaBase):
    id_reserva: int
    estado: str
    costo_total: float
    codigo_reserva: str
    qr_code: Optional[str] = None
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True