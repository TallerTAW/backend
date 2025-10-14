from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt

# Importaciones de tu proyecto
from app.config import settings # 🚨 Importación agregada (asumo que está en app/config.py)
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import Token, Login, Register # Asegúrate de que Register tiene 'captcha_token'
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import AuthException
from app.core.captcha import verificar_captcha # 🚨 Importación para el CAPTCHA

router = APIRouter(tags=["Autenticación"])

# Asegúrate de que tokenUrl coincida con el path que usas en main.py (ej. /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") 

# -----------------------------------------------------------
# RUTAS DE LOGIN Y REGISTRO (con validación de CAPTCHA)
# -----------------------------------------------------------

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    # Captcha_token se recibe como Form data para OAuth2PasswordRequestForm
    captcha_token: str = Form(..., description="Token reCAPTCHA proporcionado por el cliente") 
):
    """Inicia sesión validando credenciales y el token de reCAPTCHA."""
    
    # 1. Verificar CAPTCHA
    captcha_valido = verificar_captcha(captcha_token)
    if not captcha_valido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha inválido. Inténtalo de nuevo."
        )

    # 2. Verificar usuario y contraseña
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    
    if not usuario or not verify_password(form_data.password, usuario.contrasenia):
        raise AuthException("Credenciales incorrectas") # Usamos AuthException para el manejador

    if usuario.estado != "activo":
        raise AuthException("Usuario inactivo")
    
    # 3. Crear token
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
    """Registra un nuevo usuario, validando el token de reCAPTCHA."""
    
    # 1. Verificar CAPTCHA (Asumiendo que Register tiene el campo captcha_token)
    if not hasattr(usuario_data, 'captcha_token') or not usuario_data.captcha_token:
        raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail="Token de captcha no proporcionado en los datos de registro"
        )
        
    captcha_valido = verificar_captcha(usuario_data.captcha_token)
    if not captcha_valido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha inválido. Inténtalo de nuevo."
        )
        
    # 2. Verificar existencia y roles
    existing_user = db.query(Usuario).filter(Usuario.email == usuario_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
        
    roles_permitidos = ["cliente", "gestor", "admin", "control_acceso"]
    if usuario_data.rol not in roles_permitidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol no permitido. Roles válidos: {roles_permitidos}"
        )
        
    # 3. Crear usuario
    hashed_password = get_password_hash(usuario_data.contrasenia)
    
    nuevo_usuario = Usuario(
        nombre=usuario_data.nombre,
        apellido=usuario_data.apellido,
        email=usuario_data.email,
        contrasenia=hashed_password,
        telefono=usuario_data.telefono,
        rol=usuario_data.rol,
        estado="activo"
    )
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return {"message": "Usuario registrado exitosamente", "id": nuevo_usuario.id_usuario}


# -----------------------------------------------------------
# FUNCIÓN DE DEPENDENCIA PARA OBTENER USUARIO ACTUAL (Reincorporada)
# -----------------------------------------------------------

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Decodifica el token, verifica la existencia y estado del usuario."""
    
    try:
        # Asegúrate de que 'settings' esté disponible y tenga SECRET_KEY y ALGORITHM
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        email: str = payload.get("sub")
        rol: str = payload.get("rol")
        id_usuario: int = payload.get("id")
        
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