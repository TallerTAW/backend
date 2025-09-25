from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioResponse, UsuarioCreate, UsuarioUpdate
from app.core.security import get_password_hash

router = APIRouter()

@router.get("/", response_model=list[UsuarioResponse])
def get_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).all()

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
    
    # Crear el usuario (el id se genera automáticamente por SERIAL)
    db_usuario = Usuario(
        nombre=usuario_data.nombre,
        apellido=usuario_data.apellido,
        email=usuario_data.email,
        contrasenia=hashed_password,  # Usar el nombre correcto del campo
        telefono=usuario_data.telefono,
        rol=usuario_data.rol,
        estado=usuario_data.estado or "activo"  # Valor por defecto
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
def delete_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # En lugar de eliminar, podrías cambiar el estado a "inactivo"
    # usuario.estado = "inactivo"
    # db.commit()
    # return {"detail": "Usuario marcado como inactivo"}
    
    # O eliminar físicamente
    db.delete(usuario)
    db.commit()
    return {"detail": "Usuario eliminado exitosamente"}

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