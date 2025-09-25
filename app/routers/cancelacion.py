from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Importaciones corregidas, sin el prefijo 'app'
from app.schemas.cancelacion import Cancelacion, CancelacionCreate, CancelacionUpdate
from app.models.cancelacion import Cancelacion as CancelacionModel
from app.database import get_db

router = APIRouter(
    prefix="/cancelaciones",
    tags=["Cancelaciones"]
)

@router.post("/", response_model=Cancelacion, status_code=status.HTTP_201_CREATED,summary="Crear una nueva cancelación")
def create_cancelacion(cancelacion: CancelacionCreate, db: Session = Depends(get_db)):
    db_cancelacion = CancelacionModel(**cancelacion.dict())
    db.add(db_cancelacion)
    db.commit()
    db.refresh(db_cancelacion)
    return db_cancelacion

@router.get("/{cancelacion_id}", response_model=Cancelacion,summary="Obtener detalles de una cancelación por ID")
def get_cancelacion(cancelacion_id: int, db: Session = Depends(get_db)):
    cancelacion = db.query(CancelacionModel).filter(CancelacionModel.id_cancelacion == cancelacion_id).first()
    if not cancelacion:
        raise HTTPException(status_code=404, detail="Cancelación no encontrada")
    return cancelacion

@router.put("/{cancelacion_id}", response_model=Cancelacion,summary="Actualizar una cancelación existente")
def update_cancelacion(cancelacion_id: int, cancelacion_data: CancelacionUpdate, db: Session = Depends(get_db)):
    cancelacion = db.query(CancelacionModel).filter(CancelacionModel.id_cancelacion == cancelacion_id).first()
    if not cancelacion:
        raise HTTPException(status_code=404, detail="Cancelación no encontrada")
    
    for field, value in cancelacion_data.dict(exclude_unset=True).items():
        setattr(cancelacion, field, value)
    
    db.commit()
    db.refresh(cancelacion)
    return cancelacion

@router.delete("/{cancelacion_id}", status_code=status.HTTP_204_NO_CONTENT,summary="Eliminar una cancelación por ID")
def delete_cancelacion(cancelacion_id: int, db: Session = Depends(get_db)):
    cancelacion = db.query(CancelacionModel).filter(CancelacionModel.id_cancelacion == cancelacion_id)
    if not cancelacion.first():
        raise HTTPException(status_code=404, detail="Cancelación no encontrada")
    
    cancelacion.delete(synchronize_session=False)
    db.commit()
    return {"detail": "Cancelación eliminada exitosamente"}