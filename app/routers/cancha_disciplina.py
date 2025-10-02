from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.cancha_disciplina import CanchaDisciplina, CanchaDisciplinaCreate
from app.models.cancha_disciplina import CanchaDisciplina as CanchaDisciplinaModel
from app.database import get_db

router = APIRouter(
    prefix="/canchas-disciplinas",
    tags=["Canchas y Disciplinas"]
)

@router.post("/", response_model=CanchaDisciplina, status_code=status.HTTP_201_CREATED,summary="Crear una nueva asignación de disciplina a cancha")
def create_cancha_disciplina(cancha_disciplina: CanchaDisciplinaCreate, db: Session = Depends(get_db)):
    db_cancha_disciplina = CanchaDisciplinaModel(**cancha_disciplina.dict())
    db.add(db_cancha_disciplina)
    db.commit()
    db.refresh(db_cancha_disciplina)
    return db_cancha_disciplina

@router.get("/", response_model=list[CanchaDisciplina],summary="Obtener todas las asignaciones de disciplinas a canchas")
def get_canchas_disciplinas(db: Session = Depends(get_db)):
    return db.query(CanchaDisciplinaModel).all()

@router.get("/{id_cancha}/{id_disciplina}", response_model=CanchaDisciplina,summary="Obtener una asignación de disciplina a cancha por IDs")
def get_cancha_disciplina_by_ids(id_cancha: int, id_disciplina: int, db: Session = Depends(get_db)):
    cancha_disciplina = db.query(CanchaDisciplinaModel).filter(
        CanchaDisciplinaModel.id_cancha == id_cancha,
        CanchaDisciplinaModel.id_disciplina == id_disciplina
    ).first()
    if not cancha_disciplina:
        raise HTTPException(status_code=404, detail="Asignación de disciplina a cancha no encontrada")
    return cancha_disciplina

@router.delete("/{id_cancha}/{id_disciplina}", status_code=status.HTTP_204_NO_CONTENT,summary="Eliminar una asignación de disciplina a cancha por IDs")
def delete_cancha_disciplina(id_cancha: int, id_disciplina: int, db: Session = Depends(get_db)):
    cancha_disciplina = db.query(CanchaDisciplinaModel).filter(
        CanchaDisciplinaModel.id_cancha == id_cancha,
        CanchaDisciplinaModel.id_disciplina == id_disciplina
    )
    if not cancha_disciplina.first():
        raise HTTPException(status_code=404, detail="Asignación de disciplina a cancha no encontrada")
    
    cancha_disciplina.delete(synchronize_session=False)
    db.commit()
    return {"detail": "Asignación de disciplina a cancha eliminada exitosamente"}