from pydantic import BaseModel, EmailStr
from typing import Optional

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

class Register(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    contrasenia: str
    telefono: Optional[str] = None
    rol: str = "cliente"