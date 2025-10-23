from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.notification import Notificacion
from app.models.usuario import Usuario
from app.schemas.notification import NotificationResponse, NotificationCreate
from typing import List

router = APIRouter()

@router.get("/", response_model=List[NotificationResponse])
def get_notificaciones(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return db.query(Notificacion).order_by(Notificacion.fecha_creacion.desc()).offset(skip).limit(limit).all()

@router.get("/usuario/{usuario_id}", response_model=List[NotificationResponse])
def get_notificaciones_usuario(usuario_id: int, db: Session = Depends(get_db)):
    return db.query(Notificacion).filter(Notificacion.usuario_id == usuario_id).order_by(Notificacion.fecha_creacion.desc()).all()

@router.get("/no-leidas/count")
def contar_notificaciones_no_leidas(db: Session = Depends(get_db)):
    count = db.query(Notificacion).filter(Notificacion.leida == False).count()
    return {"count": count}

@router.post("/", response_model=NotificationResponse)
def crear_notificacion(notificacion_data: NotificationCreate, db: Session = Depends(get_db)):
    db_notificacion = Notificacion(**notificacion_data.dict())
    db.add(db_notificacion)
    db.commit()
    db.refresh(db_notificacion)
    return db_notificacion

@router.put("/{notificacion_id}/leer")
def marcar_como_leida(notificacion_id: int, db: Session = Depends(get_db)):
    notificacion = db.query(Notificacion).filter(Notificacion.id_notificacion == notificacion_id).first()
    if not notificacion:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    notificacion.leida = True
    db.commit()
    return {"detail": "Notificación marcada como leída"}

@router.delete("/{notificacion_id}")
def eliminar_notificacion(notificacion_id: int, db: Session = Depends(get_db)):
    notificacion = db.query(Notificacion).filter(Notificacion.id_notificacion == notificacion_id).first()
    if not notificacion:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    db.delete(notificacion)
    db.commit()
    return {"detail": "Notificación eliminada"}