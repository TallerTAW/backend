from pydantic import BaseModel
from typing import Optional

class DisciplinaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class DisciplinaCreate(DisciplinaBase):
    pass

class DisciplinaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None

class DisciplinaResponse(DisciplinaBase):
    id_disciplina: int
    
    class Config:
        from_attributes = True