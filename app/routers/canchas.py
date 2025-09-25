from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.cancha import Cancha
from app.schemas.cancha import CanchaResponse, CanchaCreate

router = APIRouter()

@router.get("/", response_model=list[CanchaResponse])
def get_canchas(db: Session = Depends(get_db)):
    return db.query(Cancha).all()

@router.get("/{cancha_id}", response_model=CanchaResponse)
def get_cancha(cancha_id: int, db: Session = Depends(get_db)):
    return db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()

@router.post("/", response_model=CanchaResponse)
def create_cancha(cancha_data: CanchaCreate, db: Session = Depends(get_db)):
    nueva_cancha = Cancha(**cancha_data.dict())
    db.add(nueva_cancha)
    db.commit()
    db.refresh(nueva_cancha)
    return nueva_cancha