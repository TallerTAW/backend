from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EspacioDeportivoBase(BaseModel):
   nombre: str = Field(..., min_length=1, max_length=100)
   ubicacion: Optional[str] = Field(None, max_length=150)
   capacidad: Optional[int] = Field(None, ge=1)
   estado: Optional[str] = Field("activo", pattern="^(activo|inactivo)$")
   descripcion: Optional[str] = None
   imagen: Optional[str] = Field(None, max_length=255)
   latitud: Optional[float] = Field(None, ge=-90, le=90)
   longitud: Optional[float] = Field(None, ge=-180, le=180)

class EspacioDeportivoCreate(EspacioDeportivoBase):
    pass

class EspacioDeportivoCreate(EspacioDeportivoBase):
    nombre: str  # obligatorio para creación

class EspacioDeportivoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    ubicacion: Optional[str] = Field(None, max_length=150)
    capacidad: Optional[int] = Field(None, ge=1)
    estado: Optional[str] = Field(None, pattern="^(activo|inactivo)$")
    descripcion: Optional[str] = None
    latitud: Optional[float] = Field(None, ge=-90, le=90, description="Latitud geográfica")
    longitud: Optional[float] = Field(None, ge=-180, le=180, description="Longitud geográfica")
    imagen: Optional[str] = Field(None, max_length=255)

class EspacioDeportivoResponse(EspacioDeportivoBase):
    id_espacio_deportivo: int
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True