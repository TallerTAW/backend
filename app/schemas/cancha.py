from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, time
import re

class CanchaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    tipo: Optional[str] = Field(None, max_length=50)
    hora_apertura: time
    hora_cierre: time
    precio_por_hora: float = Field(..., gt=0)
    estado: Optional[str] = Field("disponible", pattern="^(disponible|mantenimiento|ocupada)$")
    id_espacio_deportivo: int = Field(..., gt=0)

    @validator('hora_cierre')
    def validar_horarios(cls, v, values):
        if 'hora_apertura' in values and v <= values['hora_apertura']:
            raise ValueError('La hora de cierre debe ser posterior a la hora de apertura')
        return v

    @validator('nombre')
    def validar_nombre(cls, v):
        if not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-]+$', v):
            raise ValueError('El nombre solo puede contener letras, números, espacios y guiones')
        return v

class CanchaCreate(CanchaBase):
    pass

class CanchaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    tipo: Optional[str] = Field(None, max_length=50)
    hora_apertura: Optional[time] = None
    hora_cierre: Optional[time] = None
    precio_por_hora: Optional[float] = Field(None, gt=0)
    estado: Optional[str] = Field(None, pattern="^(disponible|mantenimiento|ocupada)$")

    @validator('hora_cierre')
    def validar_horarios(cls, v, values):
        if v and 'hora_apertura' in values and values['hora_apertura']:
            if v <= values['hora_apertura']:
                raise ValueError('La hora de cierre debe ser posterior a la hora de apertura')
        return v

class CanchaResponse(CanchaBase):
    id_cancha: int
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True