from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EspacioDeportivoBase(BaseModel):
   nombre: str = Field(..., min_length=1, max_length=100)
   ubicacion: Optional[str] = Field(None, max_length=150)
   capacidad: Optional[int] = Field(None, ge=1)
   estado: Optional[str] = Field("activo", pattern="^(activo|inactivo)$")
   descripcion: Optional[str] = None

class EspacioDeportivoCreate(EspacioDeportivoBase):
    pass

class EspacioDeportivoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    ubicacion: Optional[str] = Field(None, max_length=150)
    capacidad: Optional[int] = Field(None, ge=1)
    estado: Optional[str] = Field(None, pattern="^(activo|inactivo)$")
    descripcion: Optional[str] = None

class EspacioDeportivoResponse(EspacioDeportivoBase):
    id_espacio_deportivo: int
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True