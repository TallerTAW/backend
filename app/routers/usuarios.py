from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioResponse, UsuarioUpdate
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

@router.put("/{usuario_id}", response_model=UsuarioResponse)
def update_usuario(usuario_id: int, usuario_data: UsuarioUpdate, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    for field, value in usuario_data.dict(exclude_unset=True).items():
        setattr(usuario, field, value)
    
    db.commit()
    db.refresh(usuario)
    return usuario