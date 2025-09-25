from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.reserva import Reserva
from app.schemas.reserva import ReservaResponse, ReservaCreate

router = APIRouter()

@router.get("/", response_model=list[ReservaResponse])
def get_reservas(db: Session = Depends(get_db)):
    return db.query(Reserva).all()

@router.get("/{reserva_id}", response_model=ReservaResponse)
def get_reserva(reserva_id: int, db: Session = Depends(get_db)):
    return db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()

@router.post("/", response_model=ReservaResponse)
def create_reserva(reserva_data: ReservaCreate, db: Session = Depends(get_db)):
    # Aquí agregar lógica de validación de horarios, cálculo de costo, etc.
    nueva_reserva = Reserva(**reserva_data.dict())
    db.add(nueva_reserva)
    db.commit()
    db.refresh(nueva_reserva)
    return nueva_reserva