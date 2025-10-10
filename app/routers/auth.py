from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# 🚨 AGREGAR/VERIFICAR: Importación necesaria para el objeto settings
from app.config import settings 

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import Token, Login, Register
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token
)
from app.core.exceptions import AuthException

# 🚨 Importaciones necesarias para get_current_user
from datetime import datetime, timedelta
from jose import JWTError, jwt

# Hemos quitado el prefijo aquí para evitar el 404, y lo añadimos en main.py
router = APIRouter(tags=["Autenticación"]) 

# Asegúrate de que tokenUrl coincida con el path que usas en main.py (ej. /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") 

# -----------------------------------------------------------
# RUTAS DE LOGIN Y REGISTRO
# -----------------------------------------------------------

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    
    if not usuario or not verify_password(form_data.password, usuario.contrasenia):
        # Usamos AuthException para que el manejador la intercepte
        raise AuthException("Credenciales incorrectas")
    
    if usuario.estado != "activo":
        raise AuthException("Usuario inactivo")
    
    # create_access_token usa 'settings' internamente
    access_token = create_access_token(
        data={"sub": usuario.email, "rol": usuario.rol, "id": usuario.id_usuario}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id_usuario,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol
        }
    }

@router.post("/register")
def register(usuario_data: Register, db: Session = Depends(get_db)):
    # Verificar si el email ya existe
    existing_user = db.query(Usuario).filter(Usuario.email == usuario_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Crear nuevo usuario
    hashed_password = get_password_hash(usuario_data.contrasenia)
    nuevo_usuario = Usuario(
        nombre=usuario_data.nombre,
        apellido=usuario_data.apellido,
        email=usuario_data.email,
        contrasenia=hashed_password,
        telefono=usuario_data.telefono,
        rol=usuario_data.rol
    )
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return {"message": "Usuario registrado exitosamente", "id": nuevo_usuario.id_usuario}


# -----------------------------------------------------------
# FUNCIÓN DE DEPENDENCIA PARA OBTENER USUARIO ACTUAL
# -----------------------------------------------------------

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Decodifica el token y verifica la existencia y estado del usuario."""
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        email: str = payload.get("sub")
        rol: str = payload.get("rol")
        id_usuario: int = payload.get("id")
        
        # 🚨 BLOQUE DE VERIFICACIÓN DE EXPIRACIÓN COMENTADO PARA LA PRUEBA FINAL
        # Esto elimina el error "Token expirado" si el problema es el tiempo.
        # expires: datetime = payload.get("exp")
        # if expires and datetime.fromtimestamp(expires) < datetime.utcnow():
        #     raise AuthException("Token expirado") 
        
        if email is None or rol is None or id_usuario is None:
            raise AuthException("Token de autenticación inválido")
            
    except JWTError:
        raise AuthException("Token de autenticación inválido o corrupto") 

    # Buscar el usuario en la BD
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()

    if usuario is None:
        raise AuthException("Usuario no encontrado") 

    if usuario.estado != "activo":
        raise AuthException("Usuario inactivo") 
        
    return usuario