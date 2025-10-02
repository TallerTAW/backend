# app/schemas/cancha.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import time, datetime  # ← Añadir datetime
from decimal import Decimal

class CanchaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre de la cancha")
    tipo: Optional[str] = Field(None, max_length=50, description="Tipo de cancha (Fútbol, Básquetbol, etc.)")
    hora_apertura: time = Field(..., description="Hora de apertura de la cancha")
    hora_cierre: time = Field(..., description="Hora de cierre de la cancha")
    precio_por_hora: Decimal = Field(..., gt=0, description="Precio por hora de uso")
    estado: Optional[str] = Field("disponible", description="Estado de la cancha")
    id_espacio_deportivo: int = Field(..., description="ID del espacio deportivo al que pertenece")

class CanchaCreate(CanchaBase):
    pass

class CanchaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    tipo: Optional[str] = Field(None, max_length=50)
    hora_apertura: Optional[time] = None
    hora_cierre: Optional[time] = None
    precio_por_hora: Optional[Decimal] = Field(None, gt=0)
    estado: Optional[str] = Field(None, pattern="^(disponible|mantenimiento|inactiva)$")
    id_espacio_deportivo: Optional[int] = None

class CanchaResponse(CanchaBase):
    id_cancha: int
    fecha_creacion: datetime  # ← Cambiar de str a datetime
    
    class Config:
        from_attributes = True