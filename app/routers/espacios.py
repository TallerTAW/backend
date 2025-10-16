from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.espacio_deportivo import EspacioDeportivo
from app.schemas.espacio_deportivo import EspacioDeportivoResponse, EspacioDeportivoCreate, EspacioDeportivoUpdate
from app.models.usuario import Usuario
from app.models.administra import Administra
from app.core.security import get_current_user

router = APIRouter()

@router.get("/", response_model=list[EspacioDeportivoResponse])
def get_espacios(include_inactive: bool = False, db: Session = Depends(get_db)):
    """Obtener espacios deportivos, incluir inactivos solo si se solicita"""
    query = db.query(EspacioDeportivo)
    if not include_inactive:
        query = query.filter(EspacioDeportivo.estado == "activo")
    return query.all()

@router.get("/{espacio_id}", response_model=EspacioDeportivoResponse)
def get_espacio(espacio_id: int, db: Session = Depends(get_db)):
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    return espacio

@router.post("/", response_model=EspacioDeportivoResponse)
def create_espacio(espacio_data: EspacioDeportivoCreate, db: Session = Depends(get_db)):
    existing_espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.nombre == espacio_data.nombre).first()
    if existing_espacio:
        raise HTTPException(status_code=400, detail="Ya existe un espacio deportivo con ese nombre")
    
    nuevo_espacio = EspacioDeportivo(**espacio_data.dict())
    db.add(nuevo_espacio)
    db.commit()
    db.refresh(nuevo_espacio)
    return nuevo_espacio

@router.put("/{espacio_id}", response_model=EspacioDeportivoResponse)
def update_espacio(espacio_id: int, espacio_data: EspacioDeportivoUpdate, db: Session = Depends(get_db)):
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    if espacio_data.nombre and espacio_data.nombre != espacio.nombre:
        existing_espacio = db.query(EspacioDeportivo).filter(
            EspacioDeportivo.nombre == espacio_data.nombre,
            EspacioDeportivo.id_espacio_deportivo != espacio_id
        ).first()
        if existing_espacio:
            raise HTTPException(status_code=400, detail="Ya existe un espacio deportivo con ese nombre")
    
    for field, value in espacio_data.dict(exclude_unset=True).items():
        setattr(espacio, field, value)
    
    db.commit()
    db.refresh(espacio)
    return espacio

@router.delete("/{espacio_id}")
def desactivar_espacio(espacio_id: int, db: Session = Depends(get_db)):
    """Desactivar espacio deportivo (borrado lógico)"""
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    if espacio.estado == "inactivo":
        raise HTTPException(status_code=400, detail="El espacio deportivo ya está inactivo")
    
    espacio.estado = "inactivo"
    db.commit()
    
    return {"detail": "Espacio deportivo desactivado exitosamente"}

@router.put("/{espacio_id}/activar")
def activar_espacio(espacio_id: int, db: Session = Depends(get_db)):
    """Reactivar un espacio deportivo previamente desactivado"""
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    if espacio.estado == "activo":
        raise HTTPException(status_code=400, detail="El espacio deportivo ya está activo")
    
    espacio.estado = "activo"
    db.commit()
    
    return {"detail": "Espacio deportivo activado exitosamente"}

@router.get("/gestor/mis-espacios", response_model=list[EspacioDeportivoResponse])
def get_espacios_gestor(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener espacios deportivos según el rol del usuario"""
    
    if current_user.rol == "admin":
        query = db.query(EspacioDeportivo)
        if not include_inactive:
            query = query.filter(EspacioDeportivo.estado == "activo")
        espacios = query.all()
        return espacios
    
    elif current_user.rol == "gestor":
        query = db.query(EspacioDeportivo).join(
            Administra, 
            EspacioDeportivo.id_espacio_deportivo == Administra.id_espacio_deportivo
        ).filter(
            Administra.id_usuario == current_user.id_usuario
        )
        
        if not include_inactive:
            query = query.filter(EspacioDeportivo.estado == "activo")
        
        espacios = query.all()
        return espacios
    
    elif current_user.rol == "control_acceso":
        query = db.query(EspacioDeportivo).join(
            Administra, 
            EspacioDeportivo.id_espacio_deportivo == Administra.id_espacio_deportivo
        ).filter(
            Administra.id_usuario == current_user.id_usuario
        )
        
        if not include_inactive:
            query = query.filter(EspacioDeportivo.estado == "activo")
        
        espacios = query.all()
        return espacios
    
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a estos espacios"
        )
    

@router.get("/admin/todos-espacios", response_model=list[EspacioDeportivoResponse])
def get_todos_espacios_admin(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Endpoint exclusivo para admin - todos los espacios sin restricciones"""
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden acceder a este endpoint"
        )
    
    query = db.query(EspacioDeportivo)
    if not include_inactive:
        query = query.filter(EspacioDeportivo.estado == "activo")
    
    return query.all()

@router.post("/{usuario_id}/asignar-espacio/{espacio_id}")
def asignar_espacio_gestor(
    usuario_id: int,
    espacio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Asignar un espacio deportivo a un gestor (solo admin puede hacer esto)"""
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden asignar espacios"
        )
    
    usuario_gestor = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario_gestor or usuario_gestor.rol != "gestor":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario debe ser un gestor"
        )
    
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    existing_asignacion = db.query(Administra).filter(
        Administra.id_usuario == usuario_id,
        Administra.id_espacio_deportivo == espacio_id
    ).first()
    
    if existing_asignacion:
        raise HTTPException(
            status_code=400,
            detail="Este gestor ya administra este espacio"
        )
    
    nueva_asignacion = Administra(
        id_usuario=usuario_id,
        id_espacio_deportivo=espacio_id
    )
    
    db.add(nueva_asignacion)
    db.commit()
    
    return {"detail": "Espacio asignado exitosamente al gestor"}

@router.delete("/{usuario_id}/remover-espacio/{espacio_id}")
def remover_espacio_gestor(
    usuario_id: int,
    espacio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Remover un espacio deportivo de un gestor (solo admin)"""
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden remover espacios"
        )
    
    asignacion = db.query(Administra).filter(
        Administra.id_usuario == usuario_id,
        Administra.id_espacio_deportivo == espacio_id
    ).first()
    
    if not asignacion:
        raise HTTPException(
            status_code=404,
            detail="No se encontró la asignación de este espacio al gestor"
        )
    
    db.delete(asignacion)
    db.commit()
    
    return {"detail": "Espacio removido exitosamente del gestor"}

@router.get("/{usuario_id}/espacios", response_model=list[EspacioDeportivoResponse])
def get_espacios_por_gestor(
    usuario_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener espacios administrados por un gestor específico (para admin)"""
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver espacios de otros gestores"
        )
    
    usuario_gestor = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario_gestor:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if usuario_gestor.rol != "gestor":
        raise HTTPException(
            status_code=400,
            detail="El usuario especificado no es un gestor"
        )
    
    query = db.query(EspacioDeportivo).join(
        Administra, 
        EspacioDeportivo.id_espacio_deportivo == Administra.id_espacio_deportivo
    ).filter(
        Administra.id_usuario == usuario_id
    )
    
    if not include_inactive:
        query = query.filter(EspacioDeportivo.estado == "activo")
    
    espacios = query.all()
    return espacios

@router.get("/public/disponibles", response_model=list[EspacioDeportivoResponse])
def get_espacios_disponibles(db: Session = Depends(get_db)):
    """Obtener espacios deportivos disponibles (público para reservas)"""
    return db.query(EspacioDeportivo).filter(EspacioDeportivo.estado == "activo").all()

@router.get("/public/{espacio_id}", response_model=EspacioDeportivoResponse)
def get_espacio_public(espacio_id: int, db: Session = Depends(get_db)):
    """Obtener un espacio específico (público para reservas)"""
    espacio = db.query(EspacioDeportivo).filter(
        EspacioDeportivo.id_espacio_deportivo == espacio_id,
        EspacioDeportivo.estado == "activo"
    ).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    return espacio