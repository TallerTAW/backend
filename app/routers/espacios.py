from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.espacio_deportivo import EspacioDeportivo
from app.schemas.espacio_deportivo import EspacioDeportivoResponse, EspacioDeportivoCreate

router = APIRouter()

@router.get("/", response_model=list[EspacioDeportivoResponse])
def get_espacios(db: Session = Depends(get_db)):
    return db.query(EspacioDeportivo).all()

@router.get("/{espacio_id}", response_model=EspacioDeportivoResponse)
def get_espacio(espacio_id: int, db: Session = Depends(get_db)):
    return db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()

@router.post("/", response_model=EspacioDeportivoResponse)
def create_espacio(espacio_data: EspacioDeportivoCreate, db: Session = Depends(get_db)):
    nuevo_espacio = EspacioDeportivo(**espacio_data.dict())
    db.add(nuevo_espacio)
    db.commit()
    db.refresh(nuevo_espacio)
    return nuevo_espacio