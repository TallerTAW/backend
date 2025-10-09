from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.comentario import Comentario
from app.models.usuario import Usuario
from app.models.cancha import Cancha
from app.schemas.comentario import ComentarioCreate, ComentarioResponse, ComentarioUpdate

router = APIRouter()

@router.get("/", response_model=List[ComentarioResponse])
def listar_comentarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Comentario).offset(skip).limit(limit).all()

@router.get("/{comentario_id}", response_model=ComentarioResponse)
def obtener_comentario(comentario_id: int, db: Session = Depends(get_db)):
    comentario = db.query(Comentario).filter(Comentario.id_comentario == comentario_id).first()
    if not comentario:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    return comentario

@router.post("/", response_model=ComentarioResponse, status_code=status.HTTP_201_CREATED)
def crear_comentario(payload: ComentarioCreate, db: Session = Depends(get_db)):
    # Validar usuario
    usuario = db.query(Usuario).filter(Usuario.id_usuario == payload.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # Validar cancha si se puso id_cancha
    if payload.id_cancha:
        cancha = db.query(Cancha).filter(Cancha.id_cancha == payload.id_cancha).first()
        if not cancha:
            raise HTTPException(status_code=404, detail="Cancha no encontrada")

    nuevo = Comentario(**payload.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/{comentario_id}", response_model=ComentarioResponse)
def actualizar_comentario(comentario_id: int, payload: ComentarioUpdate, db: Session = Depends(get_db)):
    comentario = db.query(Comentario).filter(Comentario.id_comentario == comentario_id).first()
    if not comentario:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(comentario, field, value)

    db.commit()
    db.refresh(comentario)
    return comentario

@router.delete("/{comentario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_comentario(comentario_id: int, db: Session = Depends(get_db)):
    comentario = db.query(Comentario).filter(Comentario.id_comentario == comentario_id).first()
    if not comentario:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    db.delete(comentario)
    db.commit()
    return None

@router.get("/cancha/{cancha_id}", response_model=List[ComentarioResponse])
def comentarios_por_cancha(cancha_id: int, db: Session = Depends(get_db)):
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    return db.query(Comentario).filter(Comentario.id_cancha == cancha_id).order_by(Comentario.fecha_comentario.desc()).all()

@router.get("/usuario/{usuario_id}", response_model=List[ComentarioResponse])
def comentarios_por_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db.query(Comentario).filter(Comentario.id_usuario == usuario_id).order_by(Comentario.fecha_comentario.desc()).all()