from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UsuarioBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    telefono: Optional[str] = Field(None, max_length=15)
    rol: str = Field(..., pattern="^(admin|gestor|control_acceso|cliente)$")
    estado: Optional[str] = Field("activo", pattern="^(activo|inactivo)$")

class UsuarioCreate(UsuarioBase):
    contrasenia: str = Field(..., min_length=6)

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = Field(None, max_length=15)
    rol: Optional[str] = Field(None, pattern="^(admin|gestor|control_acceso|cliente)$")
    estado: Optional[str] = Field(None, pattern="^(activo|inactivo)$")

class UsuarioResponse(UsuarioBase):
    id_usuario: int
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True