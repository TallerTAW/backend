from pydantic import BaseModel
from typing import Optional
from datetime import datetime, time

class CanchaBase(BaseModel):
    nombre: str
    tipo: Optional[str] = None
    hora_apertura: time
    hora_cierre: time
    precio_por_hora: float
    estado: Optional[str] = "disponible"
    id_espacio_deportivo: int

class CanchaCreate(CanchaBase):
    pass

class CanchaUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    hora_apertura: Optional[time] = None
    hora_cierre: Optional[time] = None
    precio_por_hora: Optional[float] = None
    estado: Optional[str] = None

class CanchaResponse(CanchaBase):
    id_cancha: int
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True