from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date
from app.database import get_db
from app.models.cancha import Cancha
from app.models.espacio_deportivo import EspacioDeportivo
from app.models.administra import Administra
from app.schemas.cancha import CanchaResponse, CanchaCreate, CanchaUpdate, DisponibilidadResponse, HorarioDisponible
from app.core.security import get_current_user
from app.models.usuario import Usuario
import os
import shutil
from typing import Optional
import uuid

UPLOAD_DIR_CANCHAS = "static/uploads/espacios/canchas"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024

os.makedirs(UPLOAD_DIR_CANCHAS, exist_ok=True)

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file_cancha(file: UploadFile) -> str:
    """Guarda un archivo subido para canchas y retorna la ruta relativa"""
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")
    
    # Generar nombre único
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR_CANCHAS, unique_filename)
    
    # Guardar archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return f"/{UPLOAD_DIR_CANCHAS}/{unique_filename}"

router = APIRouter()

@router.get("/{cancha_id}/disponibilidad", response_model=DisponibilidadResponse)
def get_disponibilidad_cancha(
    cancha_id: int,
    fecha: str = Query(..., description="Fecha en formato YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """Obtener horarios disponibles de una cancha usando la función PostgreSQL"""
    try:
        # Convertir string a date
        fecha_date = date.fromisoformat(fecha)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Formato de fecha inválido. Use YYYY-MM-DD"
        )
    
    # Verificar que la cancha existe
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    try:
        # Ejecutar la función PostgreSQL
        result = db.execute(
            text("SELECT * FROM listar_horarios_disponibles(:cancha_id, :fecha)"),
            {"cancha_id": cancha_id, "fecha": fecha_date}
        )
        
        horarios = []
        for row in result:
            horarios.append(HorarioDisponible(
                hora_inicio=row.hora_inicio,
                hora_fin=row.hora_fin,
                disponible=row.disponible,
                precio_hora=row.precio_hora,
                mensaje=row.mensaje
            ))
        
        return DisponibilidadResponse(
            cancha_id=cancha_id,
            fecha=fecha,
            horarios=horarios
        )
        
    except Exception as e:
        # Debug: imprime el error real
        print(f"Error en disponibilidad: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener disponibilidad: {str(e)}"
        )

@router.get("/public/{cancha_id}/disponibilidad", response_model=DisponibilidadResponse)
def get_disponibilidad_cancha_public(
    cancha_id: int,
    fecha: str = Query(..., description="Fecha en formato YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """Obtener horarios disponibles de una cancha (público)"""
    return get_disponibilidad_cancha(cancha_id, fecha, db)

def obtener_canchas_por_rol(current_user: Usuario, db: Session):
    """Obtener canchas según el rol del usuario"""
    if current_user.rol == "admin":
        return db.query(Cancha).all()
    else:
        return db.query(Cancha).join(
            EspacioDeportivo,
            Cancha.id_espacio_deportivo == EspacioDeportivo.id_espacio_deportivo
        ).join(
            Administra,
            EspacioDeportivo.id_espacio_deportivo == Administra.id_espacio_deportivo
        ).filter(
            Administra.id_usuario == current_user.id_usuario
        ).all()

def verificar_permiso_cancha(current_user: Usuario, cancha_id: int, db: Session):
    """Verificar si el usuario tiene permisos sobre la cancha"""
    if current_user.rol == "admin":
        return True
    
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        return False
    
    administra_espacio = db.query(Administra).filter(
        Administra.id_usuario == current_user.id_usuario,
        Administra.id_espacio_deportivo == cancha.id_espacio_deportivo
    ).first()
    
    return administra_espacio is not None

def verificar_permiso_espacio(current_user: Usuario, espacio_id: int, db: Session):
    """Verificar si el usuario tiene permisos sobre el espacio deportivo"""
    if current_user.rol == "admin":
        return True
    
    administra_espacio = db.query(Administra).filter(
        Administra.id_usuario == current_user.id_usuario,
        Administra.id_espacio_deportivo == espacio_id
    ).first()
    
    return administra_espacio is not None

@router.get("/", response_model=list[CanchaResponse])
def get_canchas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener canchas según permisos del usuario"""
    if current_user.rol == "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para gestionar canchas"
        )
    
    return obtener_canchas_por_rol(current_user, db)

@router.get("/{cancha_id}", response_model=CanchaResponse)
def get_cancha(
    cancha_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener una cancha específica por ID con control de permisos"""
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    if not verificar_permiso_cancha(current_user, cancha_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a esta cancha"
        )
    
    return cancha

@router.get("/espacio/{espacio_id}", response_model=list[CanchaResponse])
def get_canchas_por_espacio(
    espacio_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener canchas por espacio deportivo con control de permisos"""
    if not verificar_permiso_espacio(current_user, espacio_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este espacio deportivo"
        )
    
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espacio deportivo no encontrado"
        )
    
    return db.query(Cancha).filter(Cancha.id_espacio_deportivo == espacio_id).all()

@router.post("/", response_model=CanchaResponse)
async def create_cancha(
    nombre: str = Form(...),
    tipo: Optional[str] = Form(None),
    hora_apertura: str = Form(...),
    hora_cierre: str = Form(...),
    precio_por_hora: float = Form(...),
    id_espacio_deportivo: int = Form(...),
    estado: str = Form("disponible"),
    imagen: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Crear una nueva cancha con imagen"""
    if not verificar_permiso_espacio(current_user, id_espacio_deportivo, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para crear canchas en este espacio deportivo"
        )
    
    espacio = db.query(EspacioDeportivo).filter(
        EspacioDeportivo.id_espacio_deportivo == id_espacio_deportivo
    ).first()
    
    if not espacio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espacio deportivo no encontrado"
        )
    
    existing_cancha = db.query(Cancha).filter(
        Cancha.nombre == nombre,
        Cancha.id_espacio_deportivo == id_espacio_deportivo
    ).first()
    
    if existing_cancha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cancha con ese nombre en este espacio deportivo"
        )
    
    # Procesar imagen si se proporciona
    imagen_path = None
    if imagen and imagen.size > 0:
        if imagen.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="La imagen es demasiado grande (máximo 5MB)")
        imagen_path = save_uploaded_file_cancha(imagen)
    
    # Convertir horas de string a time
    from datetime import time
    hora_apertura_time = time.fromisoformat(hora_apertura)
    hora_cierre_time = time.fromisoformat(hora_cierre)
    
    nueva_cancha = Cancha(
        nombre=nombre,
        tipo=tipo,
        hora_apertura=hora_apertura_time,
        hora_cierre=hora_cierre_time,
        precio_por_hora=precio_por_hora,
        id_espacio_deportivo=id_espacio_deportivo,
        estado=estado,
        imagen=imagen_path
    )
    
    db.add(nueva_cancha)
    db.commit()
    db.refresh(nueva_cancha)
    return nueva_cancha


@router.put("/{cancha_id}", response_model=CanchaResponse)
async def update_cancha(
    cancha_id: int,
    nombre: Optional[str] = Form(None),
    tipo: Optional[str] = Form(None),
    hora_apertura: Optional[str] = Form(None),
    hora_cierre: Optional[str] = Form(None),
    precio_por_hora: Optional[float] = Form(None),
    id_espacio_deportivo: Optional[int] = Form(None),
    estado: Optional[str] = Form(None),
    imagen: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Actualizar una cancha existente con imagen"""
    if not verificar_permiso_cancha(current_user, cancha_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para editar esta cancha"
        )
    
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    # Verificar permisos si se cambia el espacio deportivo
    if id_espacio_deportivo is not None:
        if not verificar_permiso_espacio(current_user, id_espacio_deportivo, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para mover la cancha a este espacio deportivo"
            )
        
        espacio = db.query(EspacioDeportivo).filter(
            EspacioDeportivo.id_espacio_deportivo == id_espacio_deportivo
        ).first()
        if not espacio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Espacio deportivo no encontrado"
            )
    
    # Verificar nombre único si se está cambiando
    if nombre is not None and nombre != cancha.nombre:
        espacio_id_verificar = id_espacio_deportivo if id_espacio_deportivo is not None else cancha.id_espacio_deportivo
        
        existing_cancha = db.query(Cancha).filter(
            Cancha.nombre == nombre,
            Cancha.id_espacio_deportivo == espacio_id_verificar,
            Cancha.id_cancha != cancha_id
        ).first()
        
        if existing_cancha:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una cancha con ese nombre en este espacio deportivo"
            )
    
    # Actualizar campos
    if nombre is not None:
        cancha.nombre = nombre
    if tipo is not None:
        cancha.tipo = tipo
    if hora_apertura is not None:
        from datetime import time
        cancha.hora_apertura = time.fromisoformat(hora_apertura)
    if hora_cierre is not None:
        from datetime import time
        cancha.hora_cierre = time.fromisoformat(hora_cierre)
    if precio_por_hora is not None:
        cancha.precio_por_hora = precio_por_hora
    if id_espacio_deportivo is not None:
        cancha.id_espacio_deportivo = id_espacio_deportivo
    if estado is not None:
        cancha.estado = estado
    
    # Procesar nueva imagen si se proporciona
    if imagen and imagen.size > 0:
        if imagen.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="La imagen es demasiado grande (máximo 5MB)")
        
        # Eliminar imagen anterior si existe
        if cancha.imagen:
            old_image_path = cancha.imagen.lstrip('/')
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
        
        # Guardar nueva imagen
        cancha.imagen = save_uploaded_file_cancha(imagen)
    
    db.commit()
    db.refresh(cancha)
    return cancha

@router.delete("/{cancha_id}")
def delete_cancha(
    cancha_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Eliminar una cancha (borrado físico) con control de permisos"""
    if not verificar_permiso_cancha(current_user, cancha_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para eliminar esta cancha"
        )
    
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    from app.models.reserva import Reserva
    reservas_activas = db.query(Reserva).filter(
        Reserva.id_cancha == cancha_id,
        Reserva.estado.in_(["pendiente", "confirmada", "en_curso"])
    ).first()
    
    if reservas_activas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar la cancha porque tiene reservas activas"
        )
    
    db.delete(cancha)
    db.commit()
    
    return {"detail": "Cancha eliminada correctamente"}

@router.put("/{cancha_id}/desactivar")
def desactivar_cancha(
    cancha_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Desactivar una cancha (borrado lógico) con control de permisos"""
    if not verificar_permiso_cancha(current_user, cancha_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para desactivar esta cancha"
        )
    
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    if cancha.estado == "inactiva":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cancha ya está inactiva"
        )
    
    cancha.estado = "inactiva"
    db.commit()
    db.refresh(cancha)
    
    return {"detail": "Cancha desactivada correctamente"}

@router.put("/{cancha_id}/activar")
def activar_cancha(
    cancha_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Activar una cancha previamente desactivada con control de permisos"""
    if not verificar_permiso_cancha(current_user, cancha_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para activar esta cancha"
        )
    
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    if cancha.estado == "disponible":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cancha ya está activa"
        )
    
    cancha.estado = "disponible"
    db.commit()
    db.refresh(cancha)
    
    return {"detail": "Cancha activada correctamente"}

@router.get("/gestor/mis-canchas", response_model=list[CanchaResponse])
def get_canchas_gestor(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener canchas según el rol del usuario (endpoint específico)"""
    if current_user.rol == "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a estas canchas"
        )
    
    return obtener_canchas_por_rol(current_user, db)

@router.get("/public/disponibles", response_model=list[CanchaResponse])
def get_canchas_disponibles(db: Session = Depends(get_db)):
    """Obtener todas las canchas disponibles para reservas (público)"""
    return db.query(Cancha).filter(Cancha.estado == "disponible").all()

@router.get("/public/espacio/{espacio_id}", response_model=list[CanchaResponse])
def get_canchas_por_espacio_public(espacio_id: int, db: Session = Depends(get_db)):
    """Obtener canchas por espacio deportivo (público para reservas)"""
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espacio deportivo no encontrado"
        )
    
    return db.query(Cancha).filter(
        Cancha.id_espacio_deportivo == espacio_id,
        Cancha.estado == "disponible"
    ).all()

@router.get("/public/{cancha_id}", response_model=CanchaResponse)
def get_cancha_public(cancha_id: int, db: Session = Depends(get_db)):
    """Obtener una cancha específica por ID (público para reservas)"""
    cancha = db.query(Cancha).filter(
        Cancha.id_cancha == cancha_id,
        Cancha.estado == "disponible"
    ).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada o no disponible"
        )
    return cancha