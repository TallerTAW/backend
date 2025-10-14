from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from enum import Enum

class Token(BaseModel):
    access_token: str
    token_type: str
    usuario: dict

class TokenData(BaseModel):
    email: Optional[str] = None
    rol: Optional[str] = None

class Login(BaseModel):
    email: EmailStr
    contrasenia: str

class UserRole(str, Enum):
    cliente = "cliente"
    gestor = "gestor"
    admin = "admin"
    control_acceso = "control_acceso"

class Register(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    contrasenia: str
    telefono: Optional[str] = None
    rol: UserRole = UserRole.cliente
    captcha_token: str 

    @validator('contrasenia')
    def password_length(cls, v):
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        return v

    @validator('telefono')
    def phone_length(cls, v):
        if v and len(v) < 8:
            raise ValueError('El teléfono debe tener al menos 8 dígitos')
        return v
