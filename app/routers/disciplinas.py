from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.disciplina import Disciplina
from app.schemas.disciplina import DisciplinaResponse, DisciplinaCreate, DisciplinaUpdate

router = APIRouter()

@router.get("/", response_model=list[DisciplinaResponse])
def get_disciplinas(db: Session = Depends(get_db)):
    return db.query(Disciplina).all()

@router.get("/{disciplina_id}", response_model=DisciplinaResponse)
def get_disciplina(disciplina_id: int, db: Session = Depends(get_db)):
    disciplina = db.query(Disciplina).filter(Disciplina.id_disciplina == disciplina_id).first()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina no encontrada")
    return disciplina

@router.post("/", response_model=DisciplinaResponse)
def create_disciplina(disciplina_data: DisciplinaCreate, db: Session = Depends(get_db)):
    # Verificar si ya existe una disciplina con el mismo nombre
    existing_disciplina = db.query(Disciplina).filter(Disciplina.nombre == disciplina_data.nombre).first()
    if existing_disciplina:
        raise HTTPException(status_code=400, detail="Ya existe una disciplina con ese nombre")
    
    nueva_disciplina = Disciplina(**disciplina_data.dict())
    db.add(nueva_disciplina)
    db.commit()
    db.refresh(nueva_disciplina)
    return nueva_disciplina

@router.put("/{disciplina_id}", response_model=DisciplinaResponse)
def update_disciplina(disciplina_id: int, disciplina_data: DisciplinaUpdate, db: Session = Depends(get_db)):
    disciplina = db.query(Disciplina).filter(Disciplina.id_disciplina == disciplina_id).first()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina no encontrada")
    
    # Verificar nombre único si se está actualizando
    if disciplina_data.nombre and disciplina_data.nombre != disciplina.nombre:
        existing_disciplina = db.query(Disciplina).filter(
            Disciplina.nombre == disciplina_data.nombre,
            Disciplina.id_disciplina != disciplina_id
        ).first()
        if existing_disciplina:
            raise HTTPException(status_code=400, detail="Ya existe una disciplina con ese nombre")
    
    for field, value in disciplina_data.dict(exclude_unset=True).items():
        setattr(disciplina, field, value)
    
    db.commit()
    db.refresh(disciplina)
    return disciplina

@router.delete("/{disciplina_id}")
def delete_disciplina(disciplina_id: int, db: Session = Depends(get_db)):
    disciplina = db.query(Disciplina).filter(Disciplina.id_disciplina == disciplina_id).first()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina no encontrada")
    
    db.delete(disciplina)
    db.commit()
    return {"message": "Disciplina eliminada correctamente"}