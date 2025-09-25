from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioResponse, UsuarioCreate, UsuarioUpdate
from app.core.security import get_password_hash

router = APIRouter()

@router.get("/", response_model=list[UsuarioResponse])
def get_usuarios(include_inactive: bool = False, db: Session = Depends(get_db)):
    """Obtener usuarios, incluir inactivos solo si se solicita"""
    query = db.query(Usuario)
    if not include_inactive:
        query = query.filter(Usuario.estado == "activo")
    return query.all()

@router.get("/{usuario_id}", response_model=UsuarioResponse)
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.post("/", response_model=UsuarioResponse)
def create_usuario(usuario_data: UsuarioCreate, db: Session = Depends(get_db)):
    # Verificar si el email ya existe
    existing_user = db.query(Usuario).filter(Usuario.email == usuario_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Hashear la contraseña
    hashed_password = get_password_hash(usuario_data.contrasenia)
    
    # Crear el usuario
    db_usuario = Usuario(
        nombre=usuario_data.nombre,
        apellido=usuario_data.apellido,
        email=usuario_data.email,
        contrasenia=hashed_password,
        telefono=usuario_data.telefono,
        rol=usuario_data.rol,
        estado=usuario_data.estado or "activo"
    )
    
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@router.put("/{usuario_id}", response_model=UsuarioResponse)
def update_usuario(usuario_id: int, usuario_data: UsuarioUpdate, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Si se está actualizando el email, verificar que no exista otro usuario con el mismo email
    if usuario_data.email and usuario_data.email != usuario.email:
        existing_user = db.query(Usuario).filter(
            Usuario.email == usuario_data.email,
            Usuario.id_usuario != usuario_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado por otro usuario"
            )
    
    # Actualizar campos
    for field, value in usuario_data.dict(exclude_unset=True).items():
        setattr(usuario, field, value)
    
    db.commit()
    db.refresh(usuario)
    return usuario

@router.delete("/{usuario_id}")
def desactivar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Desactivar usuario (borrado lógico)"""
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if usuario.estado == "inactivo":
        raise HTTPException(status_code=400, detail="El usuario ya está inactivo")
    
    usuario.estado = "inactivo"
    db.commit()
    
    return {"detail": "Usuario desactivado exitosamente"}

@router.put("/{usuario_id}/activar")
def activar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Reactivar un usuario previamente desactivado"""
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if usuario.estado == "activo":
        raise HTTPException(status_code=400, detail="El usuario ya está activo")
    
    usuario.estado = "activo"
    db.commit()
    
    return {"detail": "Usuario activado exitosamente"}

@router.put("/{usuario_id}/cambiar-contrasenia")
def cambiar_contrasenia(
    usuario_id: int, 
    nueva_contrasenia: str, 
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    hashed_password = get_password_hash(nueva_contrasenia)
    usuario.contrasenia = hashed_password
    db.commit()
    
    return {"detail": "Contraseña actualizada exitosamente"}