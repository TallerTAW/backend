from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import Token, Login, Register
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import AuthException

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
    try:
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
            rol=usuario_data.rol,
            estado="activo"  # Asegurar que el estado esté establecido
        )
        
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        
        return {"message": "Usuario registrado exitosamente", "id": nuevo_usuario.id_usuario}
    
    except Exception as e:
        db.rollback()
        print(f"Error en registro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )