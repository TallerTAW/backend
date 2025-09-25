from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Importaciones corregidas
from app.schemas.administra import Administra, AdministraCreate
from app.models.administra import Administra as AdministraModel
from app.database import get_db

router = APIRouter(
    prefix="/administracion",
    tags=["Administración"]
)

@router.post("/", response_model=Administra, status_code=status.HTTP_201_CREATED,summary="Crear una nueva asignación de administración")
def create_administracion(administra: AdministraCreate, db: Session = Depends(get_db)):
    db_administra = AdministraModel(**administra.dict())
    db.add(db_administra)
    db.commit()
    db.refresh(db_administra)
    return db_administra

@router.get("/", response_model=list[Administra])
def get_administracion(db: Session = Depends(get_db)):
    return db.query(AdministraModel).all()

@router.get("/{id_usuario}/{id_espacio_deportivo}", response_model=Administra,summary="Obtener una asignación de administración por IDs")
def get_administracion_by_ids(id_usuario: int, id_espacio_deportivo: int, db: Session = Depends(get_db)):
    administra = db.query(AdministraModel).filter(
        AdministraModel.id_usuario == id_usuario,
        AdministraModel.id_espacio_deportivo == id_espacio_deportivo
    ).first()
    if not administra:
        raise HTTPException(status_code=404, detail="Asignación de administración no encontrada")
    return administra

@router.delete("/{id_usuario}/{id_espacio_deportivo}", status_code=status.HTTP_204_NO_CONTENT,summary="Eliminar una asignación de administración por IDs")
def delete_administracion(id_usuario: int, id_espacio_deportivo: int, db: Session = Depends(get_db)):
    administra = db.query(AdministraModel).filter(
        AdministraModel.id_usuario == id_usuario,
        AdministraModel.id_espacio_deportivo == id_espacio_deportivo
    )
    if not administra.first():
        raise HTTPException(status_code=404, detail="Asignación de administración no encontrada")
    
    administra.delete(synchronize_session=False)
    db.commit()
    return {"detail": "Asignación de administración eliminada exitosamente"}