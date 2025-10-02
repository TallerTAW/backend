from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CanchaDisciplinaBase(BaseModel):
    id_cancha: int
    id_disciplina: int

class CanchaDisciplinaCreate(CanchaDisciplinaBase):
    pass

class CanchaDisciplina(CanchaDisciplinaBase):
    class Config:
        from_attributes = True