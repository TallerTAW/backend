from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import Token, Login, Register
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import AuthException
from app.core.captcha import verificar_captcha

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    
    if not usuario or not verify_password(form_data.password, usuario.contrasenia):
        raise AuthException("Credenciales incorrectas")
    
    if usuario.estado != "activo":
        raise AuthException("Usuario inactivo")
    
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
    """
    Registra un nuevo usuario, validando el token de reCAPTCHA.
    """
    try:
        print(f"Datos recibidos en registro: {usuario_data}")

        # Verificar CAPTCHA
        if not usuario_data.captcha_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de captcha no proporcionado"
            )

        captcha_valido = verificar_captcha(usuario_data.captcha_token)
        if not captcha_valido:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Captcha inválido. Inténtalo de nuevo."
            )
        
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
        
        print("Creando hash de contraseña...")
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
        
        print(f"Usuario registrado exitosamente: {nuevo_usuario.id_usuario}")
        return {"message": "Usuario registrado exitosamente", "id": nuevo_usuario.id_usuario}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error completo en registro: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )
